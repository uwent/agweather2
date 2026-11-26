"""What the crop stages job asks `agdata.seasonmaps.refresh` to compute (D108, D109): the archive's season, its last
days once the rest is stored, and the current forecast run's once per run. The computing is `update`'s, checked
against maps computed on request in test_modelgrid; here it's recorded rather than run."""

from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import croptiers, modelmaps, seasonmaps, series
from agdata.testing import WINDOW

LAST = date(2025, 7, 10)  # the archive's last rolled-up day


@pytest.fixture
def calls(tmp_path, monkeypatch):
    """`update`'s calls, each (year, last, since, run, run_first); the archive rolled up through LAST, no run."""
    made: list[tuple] = []

    def update(data_dir, window, year, last, run=None, run_first=None, lock=None, since=None, **kwargs):
        made.append((year, last, since, run, run_first))
        return ["written"]

    monkeypatch.setattr(seasonmaps, "update", update)
    monkeypatch.setattr(modelmaps, "_rolled_days", lambda data_dir, year: np.arange((LAST - date(2025, 1, 1)).days + 1))
    monkeypatch.setattr(series, "current_forecast", lambda data_dir: series.Forecast(path=None, reason="none"))
    return made


def test_out_of_season_nothing_is_computed(tmp_path, calls):
    assert seasonmaps.refresh(tmp_path, WINDOW, date(2025, 12, 20)) == {}
    assert calls == []


def test_the_archives_season_is_computed_whole_until_stored_then_only_its_last_days(tmp_path, calls, monkeypatch):
    assert seasonmaps.refresh(tmp_path, WINDOW, LAST + timedelta(days=1)) == {"archive": ["written"]}
    assert calls == [(2025, LAST, None, None, None)]  # nothing stored yet: the whole season
    stored = dict.fromkeys(modelmaps.SEASON_MODELS, LAST)
    monkeypatch.setattr(seasonmaps, "stored_through", lambda root, model_id, year: stored[model_id])
    calls.clear()
    seasonmaps.refresh(tmp_path, WINDOW, LAST + timedelta(days=1))
    assert calls == [(2025, LAST, LAST - timedelta(days=croptiers.REWRITE_DAYS), None, None)]
    stored["fire-blight"] = LAST - timedelta(days=30)  # one model behind: the whole season again
    calls.clear()
    seasonmaps.refresh(tmp_path, WINDOW, LAST + timedelta(days=1))
    assert calls[0][2] is None


def test_a_forecast_run_is_computed_once(tmp_path, calls, monkeypatch):
    run = tmp_path / "forecast" / "runs" / "a"
    run.mkdir(parents=True)
    last_hour = datetime(2025, 7, 21, 12, tzinfo=UTC)
    current = series.Forecast(path=run, last_hour=last_hour)
    monkeypatch.setattr(series, "current_forecast", lambda data_dir: current)
    monkeypatch.setattr(croptiers, "forecast_first_day", lambda path: "2025-07-09")
    found = seasonmaps.refresh(tmp_path, WINDOW, LAST + timedelta(days=1))
    assert found == {"archive": ["written"], "run": ["written"]}
    assert calls[-1] == (2025, last_hour.date(), None, run, date(2025, 7, 9))
    assert (run / seasonmaps.RUN_STAMP).read_text() == "2025-07-09"
    calls.clear()
    assert "run" not in seasonmaps.refresh(tmp_path, WINDOW, LAST + timedelta(days=1))  # the same run: not again
    assert [c[3] for c in calls] == [None]
