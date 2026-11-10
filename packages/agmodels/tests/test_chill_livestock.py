"""Chill (agmodels.chill, D76) and livestock heat stress (agmodels.livestock, D77) against their sources."""

from pathlib import Path

import numpy as np
import pytest

from agmodels import chill, livestock

REFERENCE = Path(__file__).parent / "fixtures" / "chillr_reference.csv"


def season() -> np.ndarray:
    """120 days of hours from October 1: cooling, a daily cycle, a warm spell (days 40–44), freezing nights later
    (the series `fixtures/make_chillr_reference.R` gives chillR)."""
    hours = np.arange(24 * 120)
    day = hours // 24
    t = 14 - 0.12 * day + 7 * np.sin(2 * np.pi * ((hours % 24) - 9) / 24)
    t[(day >= 40) & (day <= 44)] += 12
    return np.round(t, 1)


def chillr_dynamic(temps: np.ndarray) -> np.ndarray:
    """chillR 0.75's `Dynamic_Model` (R/temp_models.R), ported line for line with R's 1-based indices kept: the
    intermediate at hour l comes from hour l−1's rates, and its portion from hour l−1's ξ."""
    e0, e1, a0, a1, slope, tf = 4153.5, 12888.8, 139500, 2567000000000000000, 1.6, 277
    tk = temps + 273
    aa, ee = a0 / a1, e1 - e0
    sr = np.exp(slope * tf * (tk - tf) / tk)
    xi = sr / (1 + sr)
    xs = aa * np.exp(ee / tk)
    eak1 = np.exp(-a1 * np.exp(-e1 / tk))
    n = len(temps)
    x = np.zeros(n + 1)  # x[1..n], R's indices
    for l in range(2, n + 1):  # noqa: E741 (R's name)
        s = x[l - 1]
        if x[l - 1] >= 1:
            s = s * (1 - xi[l - 2 - 1])  # R: xi[l-2]
        x[l] = xs[l - 1 - 1] - (xs[l - 1 - 1] - s) * eak1[l - 1 - 1]  # R: xs[l-1], eak1[l-1]
    delta = np.zeros(n + 1)
    for i in range(2, n + 1):
        if x[i] >= 1:
            delta[i] = x[i] * xi[i - 1 - 1]  # R: xi[ii-1]
    return np.cumsum(delta[1:])


def test_the_dynamic_model_matches_chillrs_code():
    t = season()
    portions, _, missing = chill.dynamic(t)
    ours = np.cumsum(portions)
    reference = chillr_dynamic(t)
    # chillR's hour l uses hour l−1's temperature: its total through hour l is ours through hour l−1
    np.testing.assert_allclose(ours[:-1], reference[1:], rtol=1e-9, atol=1e-9)
    assert reference[-1] > 30 and (missing == 0)


def test_a_season_split_into_days_carries_its_state():
    t = season()
    whole, end_whole, _ = chill.dynamic(t)
    state, total = 0.0, 0.0
    for day in t.reshape(120, 24):
        portions, state, _ = chill.dynamic(day, state)
        total += portions.sum()
    assert total == pytest.approx(whole.sum()) and state == pytest.approx(end_whole)


def test_warm_hours_undo_chill_and_missing_hours_hold_it():
    t = season()
    cold, _, _ = chill.dynamic(t[: 24 * 40])
    warm_spell, _, _ = chill.dynamic(t[24 * 40 : 24 * 45])
    assert cold.sum() > 0 and warm_spell.sum() < 0.2  # little chill becomes permanent at 20–33 °C
    gappy = t.copy()
    gappy[24 * 70 : 24 * 72] = np.nan  # two cold days, when chill accrues
    portions, _, missing = chill.dynamic(gappy)
    assert missing == 48 and np.isfinite(portions).all() and portions.sum() < chill.dynamic(t)[0].sum()


@pytest.mark.skipif(not REFERENCE.exists(), reason="run fixtures/make_chillr_reference.R to compare with chillR itself")
def test_all_three_match_chillr_itself():
    rows = np.genfromtxt(REFERENCE, delimiter=",", names=True)
    t = rows["temperature_c"]
    np.testing.assert_allclose(np.cumsum(chill.dynamic(t)[0])[:-1], rows["dynamic_cumulative"][1:], atol=1e-6)
    np.testing.assert_allclose(np.cumsum(chill.utah_weights(t)), rows["utah_cumulative"])
    np.testing.assert_allclose(np.cumsum((t >= 0) & (t <= 7.2)), rows["chill_hours_cumulative"])


@pytest.mark.parametrize(
    ("t", "weight"),
    [
        (1.4, 0),
        (1.5, 0.5),
        (2.4, 0.5),
        (2.5, 1),
        (9.1, 1),
        (9.2, 0.5),
        (12.4, 0.5),
        (12.5, 0),
        (15.9, 0),
        (16.0, -0.5),
        (18.0, -0.5),
        (18.1, -1),
        (-5, 0),
        (35, -1),
    ],
)
def test_utah_weights_by_richardsons_ranges(t, weight):
    assert chill.utah_weights(np.array([t]))[0] == weight


def test_chill_hours_and_utah_units_over_a_day():
    day = np.array([-1.0, 0.0, 3.0, 7.2, 7.3, 20.0] * 4)
    assert chill.chill_hours(day) == 12 and chill.utah_units(day) == 4 * (0 + 0 + 1 + 1 + 1 - 1)
    day[5] = np.nan
    assert np.isnan(chill.chill_hours(day)) and np.isnan(chill.utah_units(day))
    grid = np.stack([day, day]).T[:, :, None]  # (hours, 2, 1)
    assert chill.chill_hours(grid).shape == (2, 1)


@pytest.mark.parametrize(
    ("t", "rh", "ws", "rad", "expected"),
    [(30, 50, 1.0, 500, 37.9), (-30, 80, 9.0, 100, -44.1), (45, 80, 1.0, 900, 67.7)],
)
def test_the_cattle_comfort_index_gives_the_papers_values(t, rh, ws, rad, expected):
    """Mader et al. (2010): the worked example (30 °C, 50%, 1 m/s, 500 W/m² → 37.9) and Table 3's ends."""
    assert livestock.cci_from_2m(t, rh, ws, rad) == pytest.approx(expected, abs=0.05)


def test_thi_by_the_nrc_formula():
    assert livestock.thi(25.0, 50.0) == pytest.approx(71.775)  # 77 − (0.55 − 0.275) × (45 − 26)
    assert livestock.thi(20.0, 100.0) == pytest.approx(68.0, abs=0.05)  # saturated air at 20 °C: THI = 1.8T + 32
    assert livestock.cci(30.0, 50.0, 1.0 * np.log(67.8 * 10 - 5.42) / 4.87, 500.0) == pytest.approx(37.9, abs=0.05)
