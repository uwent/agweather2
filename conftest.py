import pytest


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", help="also run tests that read real outside services")


def pytest_configure(config):
    config.addinivalue_line("markers", "network: reads a real outside service; runs only with --network")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs --network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
