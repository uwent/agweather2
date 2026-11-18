"""Fixtures shared across the app's tests."""

import shutil

import pytest

from agdata.testing import built_once
from api.tests import fixture_archive


@pytest.fixture(autouse=True)
def _own_data_dir(settings, tmp_path_factory):
    """Every test gets an empty DATA_DIR unless it sets one (`archive`, or its own tmp_path), so a command's run
    record (`ops.runs`) or a lock never lands in the real archive."""
    settings.DATA_DIR = tmp_path_factory.mktemp("data")


@pytest.fixture(autouse=True)
def _public_text_quotes_identifiers():
    """Fails a test whose API answer named a parameter, value or column without quotes (`api.errors.check_style`)."""
    from api import errors

    errors.STYLE_SLIPS.clear()
    yield
    slips, errors.STYLE_SLIPS[:] = list(errors.STYLE_SLIPS), []
    assert not slips, "Quote what a reader could type ('start', 'thresholds=32,28'):\n" + "\n".join(slips)


@pytest.fixture(scope="session")
def _built_archive(tmp_path_factory):
    """The fixture archive (`api.tests.fixture_archive`), built once for every worker (~13 s; `built_once`) and never
    handed to a test: `archive_dir` and the others are each worker's copies, so maps and run records one test leaves
    don't reach another."""
    return built_once(tmp_path_factory, "archive", fixture_archive.build)


def _with(built, add):
    """A build step for `built_once`: the fixture archive copied into the folder, then `add` run on it."""

    def build(folder):
        shutil.copytree(built, folder, dirs_exist_ok=True)
        add(folder)

    return build


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
    """The fixture archive with two earlier years (`fixture_archive.add_past_years`, ~35 s), built once for every
    worker and copied for each."""
    built = built_once(tmp_path_factory, "projection", _with(_built_archive, fixture_archive.add_past_years))
    return shutil.copytree(built, tmp_path_factory.mktemp("projection") / "archive")


@pytest.fixture
def projection_archive(projection_archive_dir, settings, monkeypatch):
    settings.DATA_DIR = projection_archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return projection_archive_dir


@pytest.fixture(scope="session")
def climate_archive_dir(_built_archive, tmp_path_factory):
    """The fixture archive with five gridMET years for `last5` (`fixture_archive.add_climate_years`), built once for
    every worker and copied for each."""
    built = built_once(tmp_path_factory, "climate", _with(_built_archive, fixture_archive.add_climate_years))
    return shutil.copytree(built, tmp_path_factory.mktemp("climate") / "archive")


@pytest.fixture
def climate_archive(climate_archive_dir, settings, monkeypatch):
    settings.DATA_DIR = climate_archive_dir
    settings.SERVICE_BOX = fixture_archive.BOX
    monkeypatch.setattr("api.clock.now", lambda: fixture_archive.NOW)
    return climate_archive_dir
