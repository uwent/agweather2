"""Fixtures shared across the app's tests."""

import pytest

from api.tests import fixture_archive


@pytest.fixture(scope="session")
def archive_dir(tmp_path_factory):
    """The fixture archive (`api.tests.fixture_archive`), built once per session."""
    return fixture_archive.build(tmp_path_factory.mktemp("api-archive"))


@pytest.fixture
def archive(archive_dir, settings, monkeypatch):
    """DATA_DIR and SERVICE_BOX at the fixture archive, and the API's clock at its NOW."""
    settings.DATA_DIR = archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return archive_dir


@pytest.fixture(scope="session")
def projection_archive_dir(tmp_path_factory):
    """The fixture archive with two earlier years (`fixture_archive.build_with_past_years`), built once."""
    return fixture_archive.build_with_past_years(tmp_path_factory.mktemp("projection-archive"))


@pytest.fixture
def projection_archive(projection_archive_dir, settings, monkeypatch):
    settings.DATA_DIR = projection_archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return projection_archive_dir
