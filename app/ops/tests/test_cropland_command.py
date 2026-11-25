"""`manage.py cropland` (D116): checks without fetching, fetches only the missing zips, builds, deletes the unpacked
rasters and keeps the zips. NASS's zips are synthetic (`agdata.testing.cdl_zip`); no network."""

import numpy as np
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from agdata import coverage, cropland
from agdata.grid import service_window
from agdata.testing import cdl_raster, cdl_zip
from ops.management.commands.cropland import parse_years

BOX = "43.05,-89.45,43.08,-89.40"  # a few cells near Madison


def test_years_are_a_range_or_a_list():
    assert parse_years("2021-2025") == (2021, 2022, 2023, 2024, 2025)
    assert parse_years("2025,2023") == (2023, 2025)
    for bad in ("2021-", "recent", "2005-2009"):
        with pytest.raises(CommandError, match="--years"):
            parse_years(bad)


def test_check_fetches_nothing(settings, tmp_path, capsys):
    settings.DATA_DIR = tmp_path
    call_command("cropland", "--check", "--box", BOX)
    out = capsys.readouterr().out
    assert "5 zips, 5 to fetch" in out and "cropland store: missing" in out
    assert not cropland.folder(tmp_path).exists()


def test_a_run_fetches_the_missing_years_builds_and_deletes_the_rasters(settings, tmp_path, monkeypatch, capsys):
    settings.DATA_DIR = tmp_path
    window = coverage.extent(service_window(BOX))
    sources = tmp_path / "nass"
    sources.mkdir()
    rasters = {
        y: cdl_raster(sources / f"{y}.tif", window, np.full(window.shape, 1, dtype=np.uint8)) for y in (2021, 2022)
    }
    cdl_zip(tmp_path, 2021, rasters[2021])
    fetched = []

    def fetch(year, dest, progress=None, **kwargs):
        fetched.append(year)
        made = cdl_zip(tmp_path / "server", year, rasters[year])
        dest.write_bytes(made.read_bytes())
        return dest.stat().st_size

    monkeypatch.setattr(cropland, "fetch", fetch)
    call_command("cropland", "--box", BOX, "--years", "2021-2022")
    assert fetched == [2022]
    assert cropland.status(tmp_path, window, (2021, 2022)) is None
    found = cropland.load(tmp_path)
    assert found is not None and (found.share("corn", "mean", window) == 1.0).all()
    assert not cropland.extracted(tmp_path).exists() and cropland.zip_path(tmp_path, 2022).exists()
    assert "cultivated on average" in capsys.readouterr().out
    call_command("cropland", "--box", BOX)  # the built store's years by default: nothing to do
    assert "nothing to do" in capsys.readouterr().out and fetched == [2022]
