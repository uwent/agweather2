from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from ops.management.base import check_range, parse_day, positive


def test_dates_are_checked():
    assert parse_day("2025-01-31", "--start") == date(2025, 1, 31)
    for bad in ("2025-01-31T06:00", "2025-13-01", "yesterday"):
        with pytest.raises(CommandError, match="--start"):
            parse_day(bad, "--start")
    check_range(date(2025, 1, 1), date(2025, 1, 2))
    with pytest.raises(CommandError, match="after"):
        check_range(date(2025, 1, 2), date(2025, 1, 2))
    check_range(date(2025, 1, 2), date(2025, 1, 2), exclusive=False)
    with pytest.raises(CommandError, match="at least 1"):
        positive(0, "--workers")


def test_commands_refuse_bad_ranges_before_touching_anything(settings, tmp_path):
    settings.DATA_DIR = tmp_path
    with pytest.raises(CommandError, match="--end 2025-01-01 must be after"):
        call_command("backfill", "--start", "2025-01-02", "--end", "2025-01-01")
    with pytest.raises(CommandError, match="on or after"):
        call_command("rollup", "--start", "2025-01-02", "--end", "2025-01-01")
    with pytest.raises(CommandError, match="--box"):
        call_command("rollup", "--start", "2025-01-01", "--end", "2025-01-01", "--box", "nowhere")
    assert not any(tmp_path.iterdir())


def test_rebuild_check_says_when_nothing_is_stale(settings, tmp_path, capsys):
    settings.DATA_DIR = tmp_path
    call_command("rebuild", "--check")
    assert "nothing stale" in capsys.readouterr().out


@pytest.mark.django_db
def test_backfill_fetches_only_what_is_missing_and_rolls_up_lost_days(settings, tmp_path, monkeypatch):
    import shutil

    import numpy as np

    from agdata import ingest
    from agdata.ingest import Hour
    from ops.management.commands import backfill

    settings.DATA_DIR = tmp_path
    calls = []

    def fetch(when, window, session):
        calls.append(when)
        values = {
            name: np.full(window.shape, value)
            for name, value in {
                "air_temperature": 20.0,
                "dew_point": 12.0,
                "wind_speed": 3.0,
                "wind_gust": 6.0,
                "wind_direction": 180.0,
                "surface_pressure": 98.0,
                "cloud_cover": 20.0,
                "precipitation": 0.0,
                "shortwave_radiation_hrrr": 100.0,
            }.items()
        }
        return Hour(values=values, sources=dict.fromkeys(values, "urma"))

    real = ingest.ingest_block
    monkeypatch.setattr(backfill, "ingest_block", lambda *a, **k: real(*a, fetch=fetch, **k))
    args = ("backfill", "--start", "2025-07-01", "--end", "2025-07-04", "--box", "43.05,-89.45,43.1,-89.4", "--quiet")
    call_command(*args)
    assert len(calls) == 72
    shutil.rmtree(tmp_path / "daily")  # as if the run had stopped between ingesting and rolling up
    calls.clear()
    call_command(*args)
    assert calls == []  # nothing refetched
    assert (tmp_path / "daily" / "2025.zarr").exists()  # but the days rolled up again
