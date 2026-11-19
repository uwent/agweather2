"""Rye biomass 0.3: the fixed-ceiling logistic in GDD since planting with the fall's part capped at 800 °C-days."""

from datetime import date, timedelta

import numpy as np
import pytest

from agmodels import runner
from agmodels.models import rye_biomass as rye


def _season(planting: date, last: date, *, tmin=None, tmax=None) -> tuple[list[date], dict[str, np.ndarray]]:
    """Daily inputs from planting through `last`: a smooth annual cycle (coldest mid-January) unless given."""
    days = [planting + timedelta(days=k) for k in range((last - planting).days + 1)]
    doy = np.array([d.timetuple().tm_yday for d in days], dtype=float)
    mean = 8.0 - 16.0 * np.cos(2 * np.pi * (doy - 15) / 365.25)
    inputs = {
        "air_temperature_min": mean - 6 if tmin is None else tmin,
        "air_temperature_max": mean + 6 if tmax is None else tmax,
        "day_of_year": doy,
        "year": np.array([d.year for d in days], dtype=float),
    }
    return days, inputs


def test_the_formula_on_known_values():
    assert rye.biomass(rye.X0) == pytest.approx(3000)  # a quarter of the ceiling at the midpoint
    assert rye.counted_gdd(2000, 1000) == 1800  # fall 1,000 counts as 800
    assert rye.counted_gdd(1500, 600) == 1500
    expected = 12000 / (1 + np.exp(-0.00327 * (1500 - 1127))) ** 2
    assert rye.biomass(1500) == pytest.approx(expected, rel=1e-12)
    # The levels' degree days, as the page gives them: 2,000 at about 1,010 °C-days, 4,500 at about 1,270
    assert rye.biomass(1010) < 2000 < rye.biomass(1020)
    assert rye.biomass(1265) < 4500 < rye.biomass(1270)
    assert rye.explore(gdd_total=1500, gdd_fall=600) == {"biomass": pytest.approx(expected), "level": 2.0}


def test_the_fall_cap():
    spring = 700.0
    capped = [rye.explore(gdd_total=fall + spring, gdd_fall=fall)["biomass"] for fall in (800, 1000, 1400)]
    assert capped[0] == capped[1] == capped[2]
    assert rye.explore(gdd_total=700 + spring, gdd_fall=700)["biomass"] < capped[0]


def test_biomass_stays_between_0_and_the_ceiling():
    values = rye.biomass(np.array([0.0, 500, 1500, 3000, 10000, 1e6]))
    assert (values > 0).all() and (values <= 12000).all() and (np.diff(values) >= 0).all()
    assert values[-1] == pytest.approx(12000)


def test_a_season_rises_from_march_1_and_is_blank_before():
    days, inputs = _season(date(2025, 10, 1), date(2026, 6, 30))
    out = rye.outputs(inputs)
    shown = np.isfinite(out["biomass"])
    first = days[int(np.flatnonzero(shown)[0])]
    assert first == date(2026, 3, 1) and shown[days.index(first) :].all()
    assert (np.diff(out["biomass"][shown]) >= 0).all()  # never falls through a spring
    assert out["biomass"][days.index(date(2026, 6, 15))] > out["biomass"][days.index(date(2026, 4, 15))] * 3
    assert np.isfinite(out["gdd_total"]).all()  # degree days show from planting
    np.testing.assert_allclose(out["gdd_counted"], rye.counted_gdd(out["gdd_total"], out["gdd_fall"]))
    levels = rye.risk(out)
    assert np.isnan(levels[~shown]).all() and np.isfinite(levels[shown]).all()


def test_march_1_in_a_leap_year():
    days, inputs = _season(date(2027, 10, 1), date(2028, 3, 5))
    shown = np.isfinite(rye.outputs(inputs)["biomass"])
    assert days[int(np.flatnonzero(shown)[0])] == date(2028, 3, 1)  # day 61


def test_fall_degree_days_stop_at_new_year():
    days, inputs = _season(date(2025, 10, 1), date(2026, 3, 31))
    out = rye.outputs(inputs)
    new_year = days.index(date(2026, 1, 1))
    assert out["gdd_fall"][new_year - 1] == out["gdd_fall"][-1] > 0
    assert out["gdd_total"][-1] > out["gdd_fall"][-1]


def test_missing_data_stays_missing():
    _, inputs = _season(date(2025, 10, 1), date(2026, 5, 1))
    lo = inputs["air_temperature_min"].copy()
    lo[10] = np.nan
    assert np.isnan(rye.ingredients(inputs | {"air_temperature_min": lo})["gdd"][10])
    # Before the biofix nothing has accumulated: no biomass, level or flag
    out = rye.outputs(inputs, biofix_index=5)
    assert np.isnan(out["gdd_total"][:5]).all() and np.isnan(out["planting_outside_data"][:5]).all()
    assert np.isnan(rye.risk({"biomass": np.array([np.nan])})).all()
    assert np.isnan(rye.biomass(np.nan))


@pytest.mark.parametrize(
    ("planting", "flagged"),
    [
        (date(2025, 8, 24), 1),
        (date(2025, 8, 25), 0),
        (date(2025, 10, 1), 0),
        (date(2025, 11, 10), 0),
        (date(2025, 11, 11), 1),
        (date(2024, 11, 10), 0),  # day 315 in a leap year
        (date(2024, 8, 24), 1),  # day 237 in a leap year
    ],
)
def test_plantings_outside_the_data_are_flagged(planting, flagged):
    _, inputs = _season(planting, date(planting.year + 1, 4, 1))
    flag = rye.outputs(inputs)["planting_outside_data"]
    assert (flag == flagged).all()


def test_days_after_june_15_are_out_of_season():
    assert runner._in_season(rye.SPEC, date(2026, 6, 15)) and runner._in_season(rye.SPEC, date(2026, 3, 1))
    assert not runner._in_season(rye.SPEC, date(2026, 6, 16))
    assert runner._in_season(rye.SPEC, date(2025, 8, 25)) and not runner._in_season(rye.SPEC, date(2025, 8, 24))
