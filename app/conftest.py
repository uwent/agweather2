"""Fixtures shared across the app's tests."""

import shutil

import pytest

from api.tests import fixture_archive


@pytest.fixture(autouse=True)
def _own_data_dir(settings, tmp_path_factory):
    """Every test gets an empty DATA_DIR unless it sets one (`archive`, or its own tmp_path), so a command's run
    record (`ops.runs`) or a lock never lands in the real archive."""
    settings.DATA_DIR = tmp_path_factory.mktemp("data")


@pytest.fixture(scope="session")
def _built_archive(tmp_path_factory):
    """The fixture archive (`api.tests.fixture_archive`), built once per session (~13 s) and never handed to a test:
    `archive_dir` and `projection_archive_dir` are copies, so maps and run records one test leaves don't reach the
    other."""
    return fixture_archive.build(tmp_path_factory.mktemp("built-archive"))


@pytest.fixture(scope="session")
def archive_dir(_built_archive, tmp_path_factory):
    return shutil.copytree(_built_archive, tmp_path_factory.mktemp("api") / "archive")


@pytest.fixture
def archive(archive_dir, settings, monkeypatch):
    """DATA_DIR and SERVICE_BOX at the fixture archive, and the API's clock at its NOW."""
    settings.DATA_DIR = archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return archive_dir


@pytest.fixture(scope="session")
def projection_archive_dir(_built_archive, tmp_path_factory):
    """The fixture archive with two earlier years (`fixture_archive.add_past_years`), built once."""
    path = shutil.copytree(_built_archive, tmp_path_factory.mktemp("projection") / "archive")
    return fixture_archive.add_past_years(path)


@pytest.fixture
def projection_archive(projection_archive_dir, settings, monkeypatch):
    settings.DATA_DIR = projection_archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return projection_archive_dir
