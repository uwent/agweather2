"""Normal maps (`agdata.normals`, D85): what each period stores, the statistics of a block against known answers, a
store built and read back as maps, and when it goes stale. The years are written straight into the past-years
layout (`agdata.pastyears`), as `pastyears.build` leaves them."""

from datetime import date
from pathlib import Path

import numpy as np
import pytest
import zarr
from zarr.codecs.numcodecs import PCodec

from agdata import climatology, normals, pastyears
from agdata.catalog import DAILY_VARIABLES, FILL
from agdata.grid import Window
from agmodels.degree_days import degree_days_sine

WINDOW = Window(j0=1000, j1=1020, i0=1400, i1=1418)  # 20 × 18: blocks of 16 and the ragged rest
YEARS = [2016, 2017, 2018, 2019, 2020]
NAMES = list(normals.DAILY_NAMES)


def _days(year: int) -> int:
    return (date(year + 1, 1, 1) - date(year, 1, 1)).days


def fields(year: int, shape=WINDOW.shape) -> dict[str, np.ndarray]:
    """A year with known answers: a maximum of 20 °C and minimum of 10 °C everywhere (50 and 68 °F: sine 50 is
    9 °F·d a day), 1 mm of rain a day, a minimum of −5 °C (a freeze) on January 1–10 and from December 20, and
    the minimum one degree warmer each year (so the years differ)."""
    n = _days(year)
    tmin = np.full((n, *shape), 10.0 + (year - 2016))
    tmin[:10] = -5.0
    tmin[n - 12 :] = -5.0
    return {
        "air_temperature_max": np.full((n, *shape), 20.0),
        "air_temperature_min": tmin,
        "air_temperature_mean": np.full((n, *shape), 15.0),
        "precipitation_sum": np.full((n, *shape), 1.0),
        "relative_humidity_max": np.full((n, *shape), 95.0),
        "relative_humidity_min": np.full((n, *shape), 50.0),
        "shortwave_radiation_sum": np.full((n, *shape), 15.0),
        "wind_speed_mean": np.full((n, *shape), 3.0),
        "et0_sum": np.full((n, *shape), 2.0),
    }


def write_copy(data_dir: Path, year: int, values: dict[str, np.ndarray], written: float = 1.0) -> None:
    group = zarr.open_group(pastyears.PAST.path(data_dir, year), mode="w")
    names = list(values)
    n = next(iter(values.values())).shape[0]
    array = group.create_array(
        "values",
        shape=(len(names), n, *WINDOW.shape),
        chunks=(len(names), n, 16, 16),
        dtype="int16",
        fill_value=int(FILL),
        serializer=PCodec(level=1),
    )
    array[:] = np.stack([DAILY_VARIABLES[name].encode(values[name]) for name in names])
    window = {"j0": WINDOW.j0, "j1": WINDOW.j1, "i0": WINDOW.i0, "i1": WINDOW.i1}
    group.attrs.update({"window": window, "names": names, "daily_written": written, "complete": True})


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("normals")
    for year in YEARS:
        write_copy(data_dir, year, fields(year))
    names = normals.build(data_dir, "last5", YEARS, set(YEARS), WINDOW, days_per_chunk=366)
    return data_dir, names


def test_what_each_period_stores():
    last30 = {s.name for s in normals.stats("last30")}
    last5 = {s.name for s in normals.stats("last5")}
    assert "air_temperature_mean/mean" not in last30 and "air_temperature_mean/mean" in last5
    assert "dd_modified_50_86/p50" in last30 and "dd_sine_41_86/p90" in last30 and "precipitation/p10" in last30
    assert not any(n.startswith("dd_sine_41_86") for n in last5)  # no deciles from five years
    assert "dd_sine_41/mean" in last5 and "dd_sine_86/mean" in last5  # a pair is their difference
    assert {"freeze_28/chance", "freeze_28/spring_p50", "freeze_28/season_p50"} <= last5


def test_daily_statistics_and_running_totals(built):
    data_dir, _ = built
    july = date(2025, 7, 15)
    np.testing.assert_allclose(normals.read_map(data_dir, "last5", "air_temperature_max/mean", july), 20.0)
    tmin = normals.read_map(data_dir, "last5", "air_temperature_min/mean", july)
    np.testing.assert_allclose(tmin, 12.0, atol=0.05)  # 10 to 14 °C over the years
    p10 = normals.read_map(data_dir, "last5", "air_temperature_min/p10", july)
    p90 = normals.read_map(data_dir, "last5", "air_temperature_min/p90", july)
    assert (p10 < tmin).all() and (tmin < p90).all()
    # Sine 50 °F from January 1 through March 1: each year's own total, averaged
    totals = []
    for year in YEARS:
        f = fields(year, shape=(1, 1))
        n = (date(year, 3, 1) - date(year, 1, 1)).days + 1
        lo, hi = f["air_temperature_min"][:n, 0, 0] * 1.8 + 32, f["air_temperature_max"][:n, 0, 0] * 1.8 + 32
        totals.append(degree_days_sine(lo, hi, 50.0).sum())
    total = normals.read_map(data_dir, "last5", "dd_sine_50/mean", date(2025, 3, 1))
    assert total.shape == WINDOW.shape
    np.testing.assert_allclose(total, np.mean(totals), atol=0.5)  # packed to 0.5 °F·d
    rain = normals.read_map(data_dir, "last5", "precipitation/mean", date(2025, 1, 31))
    np.testing.assert_allclose(rain, 31.0, atol=0.2)


def test_counts_are_running_counts_from_january_1(built):
    """D88: the minimum is −5 °C on January 1–10 and December 20–31, so 10 freeze days by January 31 and 22 in the
    year; the maximum (20 °C) never reaches 86 °F."""
    data_dir, names = built
    assert "count_air_temperature_min_below_32degF/mean" in names
    assert normals.COUNTS[0].name == "count_air_temperature_max_above_86degF"
    assert normals.COUNTS[7].name == "count_precipitation_sum_below_0p01in"
    freeze = "count_air_temperature_min_below_32degF/mean"
    np.testing.assert_allclose(normals.read_map(data_dir, "last5", freeze, date(2025, 1, 31)), 10.0)
    np.testing.assert_allclose(normals.read_map(data_dir, "last5", freeze, date(2025, 12, 31)), 22.0)
    window = normals.running_change(
        data_dir, "last5", freeze.split("/")[0], date(2025, 12, 1), date(2025, 12, 31), WINDOW
    )
    np.testing.assert_allclose(window, 12.0)
    hot = normals.read_map(data_dir, "last5", "count_air_temperature_max_above_86degF/mean", date(2025, 12, 31))
    np.testing.assert_allclose(hot, 0.0)


def test_freeze_chances_and_dates(built):
    data_dir, _ = built
    chance = lambda day: normals.read_map(data_dir, "last5", "freeze_32/chance", day)  # noqa: E731
    np.testing.assert_allclose(chance(date(2025, 1, 5)), 100.0)  # every year freezes after January 5
    np.testing.assert_allclose(chance(date(2025, 3, 1)), 0.0)
    np.testing.assert_allclose(chance(date(2025, 11, 1)), 0.0)
    np.testing.assert_allclose(chance(date(2025, 12, 25)), 100.0)
    last_spring = normals.read_map(data_dir, "last5", "freeze_32/spring_p50")
    np.testing.assert_allclose(last_spring, climatology.slot(date(2025, 1, 10)))
    season = normals.read_map(data_dir, "last5", "freeze_32/season_p50")
    assert np.nanmin(season) >= 340 and np.nanmax(season) <= 345


def test_status_follows_the_years_and_their_copies(built):
    data_dir, _ = built
    assert normals.status(data_dir, "last5", YEARS, set(YEARS)) is None
    assert normals.status(data_dir, "last5", YEARS[1:], set(YEARS)) == "out of date: the period's years changed"
    assert normals.status(data_dir, "last10", YEARS, set(YEARS)) == "missing"
    zarr.open_group(pastyears.PAST.path(data_dir, 2017), mode="r+").attrs["daily_written"] = 2.0
    try:
        assert normals.status(data_dir, "last5", YEARS, set(YEARS)) == "out of date: a year's data changed"
    finally:
        zarr.open_group(pastyears.PAST.path(data_dir, 2017), mode="r+").attrs["daily_written"] = 1.0


def test_a_missing_copy_is_refused(tmp_path):
    write_copy(tmp_path, 2016, fields(2016))
    with pytest.raises(ValueError, match="2017 has no copy"):
        normals.build(tmp_path, "last5", [2016, 2017], {2016, 2017}, WINDOW)


def test_a_read_over_part_of_the_window(built):
    data_dir, _ = built
    part = Window(j0=1002, j1=1005, i0=1410, i1=1418)
    got = normals.read_map(data_dir, "last5", "et0/mean", date(2025, 1, 10), window=part)
    assert got.shape == (3, 8)
    np.testing.assert_allclose(got, 20.0, atol=0.1)


def test_a_stopped_build_leaves_the_current_store(built, tmp_path):
    data_dir, _ = built
    for year in YEARS:
        target = pastyears.PAST.path(tmp_path, year)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(pastyears.PAST.path(data_dir, year))
    normals.build(tmp_path, "last5", YEARS, set(YEARS), WINDOW, days_per_chunk=366)
    before = normals.read_map(tmp_path, "last5", "et0/mean", date(2025, 6, 1))
    calls = iter([False, True])  # the first block, then stop
    got = normals.build(
        tmp_path, "last5", YEARS[1:], set(YEARS), WINDOW, days_per_chunk=366, stopping=lambda: next(calls, True)
    )
    assert got is None
    np.testing.assert_array_equal(normals.read_map(tmp_path, "last5", "et0/mean", date(2025, 6, 1)), before)
    assert normals.status(tmp_path, "last5", YEARS, set(YEARS)) is None
    assert sorted(p.name for p in normals.path(tmp_path, "last5").parent.iterdir()) == ["last5.zarr"]
