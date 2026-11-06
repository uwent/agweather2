import pytest


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


@pytest.fixture(scope="session")
def winters_dir(tmp_path_factory):
    """Potato volunteer's winter archive (`agdata.testing.winters`), built once for agdata's and the app's tests
    (~27 s). Read only: a test that changes it works on a copy."""
    from agdata import testing

    return testing.winters(tmp_path_factory.mktemp("winters"))
