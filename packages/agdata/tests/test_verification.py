"""The verification archive (D113): what `keep` copies, `prune` deletes and `score_day` computes."""

import json
import os
import shutil
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import forecast, verification
from agdata.catalog import DAILY_VARIABLES
from agdata.store import DAILY, GridStore
from agdata.testing import WINDOW, fake_run, full, write_days

HOUR = timedelta(hours=1)
CYCLE = datetime(2025, 7, 10, 13, tzinfo=UTC)


def test_a_cycle_belongs_to_its_grid_day_and_leads_count_from_it():
    assert verification.cycle_day(datetime(2025, 7, 10, 1, tzinfo=UTC)) == date(2025, 7, 9)  # 7 p.m. CST the day before
    assert verification.cycle_day(datetime(2025, 7, 10, 7, tzinfo=UTC)) == date(2025, 7, 10)
    assert verification.cycle_day(datetime(2025, 7, 10, 6, tzinfo=UTC)) == date(2025, 7, 9)  # midnight CST ends the 9th
    leads = verification.lead_days(CYCLE, last_observed=None)
    assert leads == {date(2025, 7, 10) + timedelta(days=k): k for k in range(1, 11)}
    # A day is kept only if it starts (after 06Z) after the last observed hour
    observed = datetime(2025, 7, 11, 7, tzinfo=UTC)
    assert min(verification.lead_days(CYCLE, observed)) == date(2025, 7, 12)
    assert date(2025, 7, 11) in verification.lead_days(CYCLE, datetime(2025, 7, 11, 6, tzinfo=UTC))


def read_kept(data_dir, cycle: datetime, name: str, day: date) -> np.ndarray:
    store = GridStore.open(verification.kept_path(data_dir, cycle), DAILY, day.year, verification.kept_variables())
    t = store.index_of(day)
    return store.read_steps(name, t, t + 1)[0]


def test_keep_copies_the_lead_days_exactly_and_leaves_out_lead_0(tmp_path):
    days = [date(2025, 7, 10) + timedelta(days=k) for k in range(12)]
    rng = np.random.default_rng(1)
    tmax = {day: 20 + 10 * rng.random(WINDOW.shape) for day in days}
    dsv = {day: full(k % 5) for k, day in enumerate(days)}
    run = fake_run(tmp_path, CYCLE, {"air_temperature_max": tmax, "late-blight-dsv.dsv": dsv}, CYCLE + 2 * HOUR)
    kept = verification.keep(tmp_path, run)
    assert kept == {date(2025, 7, 10) + timedelta(days=k): k for k in range(1, 11)}
    for day in kept:
        packed = DAILY_VARIABLES["air_temperature_max"].decode(DAILY_VARIABLES["air_temperature_max"].encode(tmax[day]))
        np.testing.assert_array_equal(read_kept(tmp_path, CYCLE, "air_temperature_max", day), packed)
        np.testing.assert_array_equal(read_kept(tmp_path, CYCLE, "late-blight-dsv.dsv", day), dsv[day])
    for day in (date(2025, 7, 10), date(2025, 7, 21)):  # lead 0 and lead 11
        assert np.isnan(read_kept(tmp_path, CYCLE, "air_temperature_max", day)).all()
    (only,) = verification.kept_runs(tmp_path)
    assert only.cycle == CYCLE and only.leads == kept
    assert only.versions == {
        "air_temperature_max": 1,
        "late-blight-dsv.dsv": verification._ingredient("late-blight-dsv.dsv").version,
    }


def test_keep_takes_two_stores_across_new_year_and_replaces_an_earlier_copy(tmp_path):
    cycle = datetime(2025, 12, 28, 13, tzinfo=UTC)
    days = [date(2025, 12, 29) + timedelta(days=k) for k in range(10)]
    run = fake_run(tmp_path, cycle, {"precipitation_sum": {day: full(1.0) for day in days}})
    kept = verification.keep(tmp_path, run)
    assert sorted(kept) == days
    path = verification.kept_path(tmp_path, cycle)
    assert sorted(p.name for p in (path / "daily").iterdir()) == ["2025.zarr", "2026.zarr"]
    assert read_kept(tmp_path, cycle, "precipitation_sum", date(2026, 1, 7)) == pytest.approx(full(1.0))
    assert verification.keep(tmp_path, run) == kept  # again: a fresh copy, not an error


def test_keep_of_a_run_without_days_keeps_nothing(tmp_path):
    path = forecast.run_path(tmp_path, CYCLE)
    path.mkdir(parents=True)
    (path / "run.json").write_text(json.dumps({"cycle": CYCLE.isoformat()}))
    assert verification.keep(tmp_path, path) == {}
    assert verification.kept_runs(tmp_path) == []


def test_prune_deletes_old_runs_and_crashed_keeps(tmp_path):
    now = datetime(2025, 9, 1, 12, tzinfo=UTC)
    root = verification.root(tmp_path)
    for name in ("2025071513", "2025071813", "2025083113", "2025090107", "notes"):
        (root / name).mkdir(parents=True)
    for name in ("2025071513", "2025071813", "2025083113"):
        (root / name / verification.INFO).write_text("{}")
    os.utime(root / "2025083113", (0, 0))  # complete: kept however old its files
    os.utime(root / "2025090107", None)  # incomplete, but maybe being written
    assert verification.prune(tmp_path, now) == 1
    assert sorted(p.name for p in root.iterdir()) == ["2025071813", "2025083113", "2025090107", "notes"]
    os.utime(root / "2025090107", (0, 0))  # an hour later, still incomplete: a crash
    assert verification.prune(tmp_path, now) == 1
    assert not (root / "2025090107").exists()


DAY = date(2025, 7, 12)


@pytest.fixture
def scored(tmp_path):
    """An archive day and two runs (July 10 13Z, lead 2; July 11 07Z, lead 1) holding it, with hand-made values."""
    observed_min, observed_max = full(10.0), full(20.0)
    observed_min[0, 0] = np.nan  # a cell the archive lacks
    write_days(
        tmp_path,
        {
            "air_temperature_min": {DAY: observed_min},
            "air_temperature_max": {DAY: observed_max},
            "precipitation_sum": {DAY: np.array([[0.0, 0.3, 5.0], [0.0, 2.0, 0.1]])},
            "late-blight-dsv.dsv": {DAY: full(2.0)},
        },
    )
    second = datetime(2025, 7, 11, 7, tzinfo=UTC)
    forecast_values = {
        "air_temperature_min": {DAY: full(11.0)},
        "air_temperature_max": {DAY: np.array([[22.0, 18.0, 20.0], [21.0, 19.0, 20.0]])},
        "precipitation_sum": {DAY: np.array([[0.0, 0.0, 4.0], [1.0, 2.0, np.nan]])},
        "late-blight-dsv.dsv": {DAY: full(3.0)},
    }
    for cycle in (CYCLE, second):
        verification.keep(tmp_path, fake_run(tmp_path, cycle, forecast_values))
    return tmp_path


def by(result, cycle=CYCLE) -> dict[str, verification.Score]:
    return {s.variable: s for s in result.scores if s.cycle == cycle}


def test_score_day_compares_where_both_are_known(scored):
    result = verification.score_day(scored, DAY)
    assert result.skipped == [] and result.observed_written is not None
    assert {(s.cycle.hour, s.lead) for s in result.scores} == {(13, 2), (7, 1)}
    scores = by(result)
    assert set(scores) == {
        "air_temperature_min",
        "air_temperature_max",
        "precipitation_sum",
        "late-blight-dsv.dsv",
        "dd_sine_50_86",
    }
    tmin = scores["air_temperature_min"]
    assert (tmin.n, tmin.bias, tmin.mae, tmin.rmse) == (5, pytest.approx(1.0), pytest.approx(1.0), pytest.approx(1.0))
    tmax = scores["air_temperature_max"]  # errors 2, −2, 0, 1, −1, 0
    assert tmax.n == 6 and tmax.bias == pytest.approx(0.0) and tmax.mae == pytest.approx(1.0)
    assert tmax.rmse == pytest.approx(np.sqrt(10 / 6)) and tmax.hits is None
    precip = scores["precipitation_sum"]  # five cells known in both; wet at 0.254 mm
    assert precip.n == 5 and (precip.hits, precip.misses, precip.false_alarms) == (2, 1, 1)
    assert scores["late-blight-dsv.dsv"].bias == pytest.approx(1.0)
    # Degree days from each side's min and max, the same way: where the min is missing, none
    dd = scores["dd_sine_50_86"]
    assert dd.n == 5
    assert verification.UNITS["dd_sine_50_86"] == "degF_day"


def test_a_day_without_kept_runs_or_archive_scores_nothing(scored):
    assert verification.score_day(scored, DAY + timedelta(days=30)).scores == []
    shutil.rmtree(scored / "daily")
    shutil.rmtree(scored / "ingredients")
    result = verification.score_day(scored, DAY)
    assert result.scores == [] and result.observed_written is None


def test_a_variable_kept_from_older_code_is_skipped(scored):
    info_file = verification.kept_path(scored, CYCLE) / verification.INFO
    info = json.loads(info_file.read_text())
    info["versions"]["air_temperature_max"] = 0
    info_file.write_text(json.dumps(info))
    result = verification.score_day(scored, DAY)
    assert "air_temperature_max" not in by(result) and "dd_sine_50_86" not in by(result)
    assert "air_temperature_min" in by(result)
    assert result.skipped == ["air_temperature_max: the 2025-07-10 13Z run's is from older code"]
