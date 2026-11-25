import os
import shutil
from pathlib import Path

import pytest


def _temp_in_memory() -> None:
    """Test archives under /dev/shm (memory) rather than /tmp when there's room: the suite writes thousands of small
    zarr chunk files, and on WSL's disk the file system's system time was most of its run (6.0 min with 13.8 min of
    system time on 8 workers; 3.4 min and 4.6 with the same tests in memory, 2026-11-18). pytest reads the variable
    when it first makes a temp folder, so setting it here, before any, moves them all (numbered per run as under
    /tmp, so runs at the same time don't collide). Set PYTEST_DEBUG_TEMPROOT yourself to put them elsewhere."""
    shm = Path("/dev/shm")
    usable = "PYTEST_DEBUG_TEMPROOT" not in os.environ and shm.is_dir() and os.access(shm, os.W_OK)
    if usable and shutil.disk_usage(shm).free > 6e9:  # a run takes ~2 GB while it runs; failed tests' are kept
        os.environ["PYTEST_DEBUG_TEMPROOT"] = str(shm)


_temp_in_memory()


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", help="also run tests that read real outside services")
    parser.addoption(
        "--update-snapshots", action="store_true", help="rewrite model sweep snapshots (after bumping the version)"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "network: reads a real outside service; runs only with --network")
    # zarr's thread pool (one thread a core by default) spends ~1.7 cores of system time on hand-offs while a test
    # writes a small archive, for no gain in wall time; with a pytest-xdist worker per core it starved the others
    # (the suite: 4.7 min on 8 workers, 2.5 min with one zarr thread each). Results are the same either way.
    import zarr

    zarr.config.set({"threading.max_workers": 1})


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs --network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_network_tries(request, monkeypatch):
    """Fails a test that tried to reach the network. pytest-socket blocks the connection, but code that catches the
    error (a fetch that falls back, an API answer with an error) passed with only a warning. It doesn't block the
    name lookup before it, which went out to DNS: that's refused here for any host but this machine."""
    import socket

    import pytest_socket

    if request.node.get_closest_marker("enable_socket"):  # a `network` test, run with --network
        yield
        return
    tried: list[str] = []
    for error in (pytest_socket.SocketBlockedError, pytest_socket.SocketConnectBlockedError):

        def init(self, *args, _init=error.__init__, **kwargs):
            _init(self, *args, **kwargs)
            tried.append(str(self))

        monkeypatch.setattr(error, "__init__", init)

    def getaddrinfo(host, *args, _lookup=socket.getaddrinfo, **kwargs):
        if host not in (None, "localhost", "127.0.0.1", "::1", b"localhost"):
            tried.append(f"A test tried to look up {host!r}.")
            raise socket.gaierror(socket.EAI_NONAME, "blocked in tests")  # as an unknown name fails
        return _lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    yield
    if tried:
        pytest.fail(f"The test tried to use the network (record a fixture instead): {tried[0]}", pytrace=False)


@pytest.fixture(scope="session")
def winters_dir(tmp_path_factory):
    """Potato volunteer's winter archive (`agdata.testing.winters`), built once for agdata's and the app's tests
    and every worker (~27 s; `built_once`). Read only: a test that changes it works on a copy."""
    import shutil

    from agdata import testing

    built = testing.built_once(tmp_path_factory, "winters", testing.winters)
    return shutil.copytree(built, tmp_path_factory.mktemp("winters") / "archive")  # each worker's own
