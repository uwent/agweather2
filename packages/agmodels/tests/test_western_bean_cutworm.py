"""Western bean cutworm (docs/models-plan.md part H2): Hanson et al. 2015's simple method and flight model, which NEWA
runs (D95)."""

import numpy as np
import pytest

from agmodels.insects.western_bean_cutworm import INSECT
from agmodels.phenology import DD_STEP, PhenologyModel, curves, dd_grid, generation_densities

MODEL = PhenologyModel(insect=INSECT, summary="")
WINDOW = "window_scout_corn_for_egg_masses"
# Hanson et al. 2015, Table 4: the log-logistic's levels of flight (%) in °F·d; 10 and 90 % as NEWA tabulates them
TABLE_4_F = {5: 2377, 10: 2455, 25: 2577, 50: 2704, 75: 2838, 90: 2977, 95: 3077}
MU_C, S = 7.315, 0.044  # the log-logistic's location and scale, on ln °C·d


def log_logistic(dd_f: np.ndarray) -> np.ndarray:
    dd_c = np.maximum(np.asarray(dd_f, dtype=float), 1e-9) / 1.8
    return 1 / (1 + np.exp(-(np.log(dd_c) - MU_C) / S))


def flown(fraction: float) -> float:
    return float(np.interp(fraction, curves(INSECT)["generations_adult_flight"], dd_grid()))


def test_hansons_simple_method_caps_the_days_mean_at_75f_from_march_1():
    assert (INSECT.dd_method, INSECT.base_f, INSECT.upper_f, INSECT.biofix) == ("average_capped_mean", 38, 75, "03-01")
    lo_f, hi_f = np.array([30.0, 50.0, 60.0, 70.0]), np.array([44.0, 70.0, 100.0, 96.0])
    out = MODEL.outputs({"air_temperature_min": (lo_f - 32) / 1.8, "air_temperature_max": (hi_f - 32) / 1.8})
    # a mean below the base counts nothing; a mean above 75 °F counts 75 − 38, though the maximum alone was above it
    np.testing.assert_allclose(out["dd"], [0.0, 22.0, 37.0, 37.0], atol=1e-9)


def test_the_table_is_the_log_logistic():
    for level, dd in TABLE_4_F.items():
        assert log_logistic(np.array(dd)) * 100 == pytest.approx(level, abs=0.6), level


def test_the_flight_curve_follows_hansons_log_logistic():
    x = dd_grid()
    ours = np.cumsum(generation_densities(insect=INSECT, stage=INSECT.life_stages[0])[0]) * DD_STEP  # type: ignore[arg-type]
    span = (x >= 1800) & (x <= 3800)
    assert np.abs(ours[span] - log_logistic(x[span])).max() * 100 <= 2.3
    assert np.sqrt(np.mean((ours[span] - log_logistic(x[span])) ** 2)) * 100 <= 1.3
    found = {level: flown(level / 100) for level in TABLE_4_F}
    assert round(found[5]) == 2402 and round(found[50]) == 2705 and round(found[95]) == 3043
    for level, dd in TABLE_4_F.items():
        assert found[level] == pytest.approx(dd, abs=40), level


def test_one_generation_egg_masses_carry_the_risk():
    assert INSECT.generation_dd is None and INSECT.max_generations is None
    assert [s.weight for s in INSECT.life_stages] == [0, 1]
    peak = float(dd_grid()[np.argmax(curves(INSECT)["activity_egg_masses"])])
    assert TABLE_4_F[50] < peak < TABLE_4_F[75]  # a little after the flight's middle
    assert MODEL.explore(dd_total=peak)["risk"] == pytest.approx(1.0, abs=1e-3)
    assert MODEL.explore(dd_total=3800)["risk"] < 1e-3 and MODEL.explore(dd_total=2000)["risk"] == 0


def test_the_scouting_window_runs_from_5_to_90_percent_of_the_flight():
    open_dd = dd_grid()[curves(INSECT)[WINDOW] > 0]
    assert open_dd[0] == pytest.approx(flown(0.05), abs=DD_STEP)
    assert open_dd[-1] == pytest.approx(flown(0.9), abs=DD_STEP)
    assert abs(open_dd[-1] - TABLE_4_F[90]) <= 2  # NEWA's 90 %
    assert np.all(np.diff(open_dd) == DD_STEP)


def test_trained_in_nebraska():
    assert INSECT.trained is not None and INSECT.trained.contains(state="NE", fips=None)
    assert not INSECT.trained.contains(state="WI", fips="55025")
