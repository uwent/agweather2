"""Seasonal products on the grid (`agdata.seasonal`): potato volunteer's winters from the stored ingredients."""

from datetime import UTC, date, datetime

import numpy as np
import pytest

from agdata import modelgrid, seasonal, testing
from agdata.catalog import VARIABLES
from agdata.store import HOURLY, GridStore
from agdata.testing import WINDOW
from agmodels.registry import model
from agmodels.seasons import season_named

POTATO = model("potato-volunteer").SPEC
LAST = testing.WINTER_LAST  # 2025-26 is open; 2023-24 at 1 hour a day below 27 °F, 2024-25 at 2, 2025-26 at 3


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return testing.winters(tmp_path_factory.mktemp("seasons"))


def _at(root, day: date) -> modelgrid.ModelDays:
    return modelgrid.model_days(root, POTATO.id, day, day, WINDOW)


def test_a_winter_counts_november_through_march(built):
    """2024-25's count is its 151 days at two hours, and holds after March 31 (April's cold isn't counted)."""
    found = _at(built, date(2025, 3, 31))
    assert (found.outputs["killing_hours_4cm"] == 2 * 151).all()
    assert (found.level == 0).all()  # Low: 120 hours at every depth
    april = modelgrid.model_days(built, POTATO.id, date(2025, 3, 30), date(2025, 4, 2), WINDOW)
    assert np.isnan(april.outputs["killing_hours_4cm"][2:]).all()  # between seasons: the next hasn't started


def test_the_seasons_held_and_how_far_each_is_counted(built):
    seasons = seasonal.held(POTATO, [2023, 2024, 2025], LAST)
    assert [s.name for s in seasons] == ["2023-24", "2024-25", "2025-26"]  # 2022-23 would start before the archive
    assert seasonal.through(season_named(POTATO, "2025-26"), LAST) == LAST
    assert seasonal.through(season_named(POTATO, "2024-25"), LAST) == date(2025, 3, 31)
    assert seasonal.through(season_named(POTATO, "2026-27"), LAST) is None


def test_the_open_winter_projected_on_the_earlier_ones(built):
    """From December 15: 135 hours so far, then each earlier winter's December 16 to March 31."""
    found = _at(built, LAST)
    assert (found.outputs["killing_hours_4cm"] == 3 * 45).all()  # Nov 1 – Dec 15
    projected = seasonal.project(built, POTATO.id, LAST, WINDOW, found, [2023, 2024, 2025])
    assert projected.years == [2024, 2023]
    # 2024-25: 106 days at 2 h; 2023-24: 107 days (its February had 29) at 1 h
    expected = np.median([3 * 45 + 2 * 106, 3 * 45 + 107])
    np.testing.assert_allclose(projected.medians["projected_killing_hours_4cm"], expected)
    assert (projected.counted == 2).all()
    assert (projected.chances["chance_low"] == 100).all() and (projected.chances["chance_very_high"] == 0).all()
    assert (projected.medians["projected_risk_level"] == 0).all()


def test_a_settled_winter_projects_to_itself(built):
    day = date(2025, 3, 31)
    projected = seasonal.project(built, POTATO.id, day, WINDOW, _at(built, day), [2023, 2024, 2025])
    assert projected.years == []
    assert (projected.medians["projected_killing_hours_4cm"] == 2 * 151).all()


def test_a_season_is_final_once_its_last_day_is_permanent(tmp_path):
    season = season_named(POTATO, "2024-25")
    soil = [VARIABLES[n] for n in ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm")]
    store = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, soil)
    first = datetime(2025, 3, 29, tzinfo=UTC)
    provisional: list[str | None] = [*["era5land"] * 48, *["ifs"] * 72]
    permanent: list[str | None] = ["era5land"] * 120
    for v in soil:
        store.set_sources(v.name, first, provisional)
    assert not seasonal.is_final(tmp_path, POTATO, season, date(2025, 3, 30))  # not observed yet
    assert not seasonal.is_final(tmp_path, POTATO, season, date(2025, 4, 3))  # IFS's provisional soil
    for v in soil:
        store.set_sources(v.name, first, permanent)
    assert seasonal.is_final(tmp_path, POTATO, season, date(2025, 4, 3))


def test_the_test_winters_are_final_through_the_spring(built):
    assert seasonal.is_final(built, POTATO, season_named(POTATO, "2024-25"), LAST)
    assert not seasonal.is_final(built, POTATO, season_named(POTATO, "2025-26"), LAST)


def test_medians_over_the_known_seasons_per_cell():
    values = np.array([[1.0, 5.0, 2.0], [3.0, np.nan, 4.0], [10.0, 7.0, 0.0], [2.0, 1.0, 9.0]])
    known = np.isfinite(values)
    known[3, 2] = False  # a season a cell lacks
    np.testing.assert_allclose(seasonal._median(values, known), [2.5, 5.0, 2.0])
    np.testing.assert_allclose(seasonal._median(values, known, method="higher"), [3.0, 5.0, 2.0])
    assert np.isnan(seasonal._median(values, np.zeros_like(known))).all()


def test_a_season_missing_a_day_isnt_projected_on(built, tmp_path):
    """A day an earlier season lacks would add no cold to its total, so that season is left out."""
    import shutil

    from agdata.catalog import DAILY_VARIABLES
    from agdata.store import DAILY

    root = shutil.copytree(built, tmp_path / "archive")
    name = "hours_soil_4cm_below_27f"
    GridStore.open(root, DAILY, 2025, [DAILY_VARIABLES[name]]).set_sources(name, date(2025, 2, 10), [None])
    found = _at(root, LAST)
    projected = seasonal.project(root, POTATO.id, LAST, WINDOW, found, [2023, 2024, 2025])
    assert projected.years == [2023]
