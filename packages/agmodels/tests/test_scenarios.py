"""Models over scenarios at once (D63's projection; PLAN.md Phase 5 D P2): each scenario as if run alone, and the
spread across them."""

from datetime import date, timedelta

import numpy as np
import pytest

from agmodels import runner, scenarios
from agmodels.registry import all_models, model
from agmodels.testing import DATES, LATITUDE, WEATHER

TEMPERATURES = {"air_temperature_min", "air_temperature_max", "air_temperature_mean", "dew_point_min",
                "temperature_mean_rh_over_90_from_8pm", "soil_temperature_4cm_min", "soil_temperature_10cm_min",
                "soil_temperature_30cm_min"}  # fmt: skip
START = date(2025, 4, 1)
PLANTING = date(2025, 5, 1)


def three_scenarios() -> dict[str, np.ndarray]:
    """The test weather; 2 °C warmer; and with gaps (2 days, bridged, and 10, not)."""
    out = {}
    for name, values in WEATHER.items():
        warmer = values + 2.0 if name in TEMPERATURES else values
        gappy = values.astype(float).copy()
        k = DATES.index(date(2025, 6, 1))
        gappy[k : k + 2] = np.nan
        gappy[k + 30 : k + 40] = np.nan
        out[name] = np.stack([values, warmer, gappy], axis=1).astype(float)
    return out


DAILY = three_scenarios()


def _planting(model_id: str) -> date | None:
    return PLANTING if runner.crop_models(model(model_id).SPEC) else None


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_each_scenario_is_what_running_it_alone_gives(model_id):
    m = model(model_id)
    names = runner.required_inputs(m)
    kwargs = {"dates": DATES, "latitude": LATITUDE, "start": START, "planting": _planting(model_id)}
    together = scenarios.run_scenarios(m, daily={n: DAILY[n] for n in names}, **kwargs)
    assert len(together) == 3
    for j, shared in enumerate(together):
        alone = runner.run(m, daily={n: DAILY[n][:, j] for n in names}, **kwargs)
        assert (shared.biofix, shared.reason, shared.dates) == (alone.biofix, alone.reason, alone.dates), (model_id, j)
        assert shared.outputs.keys() == alone.outputs.keys()
        for name, values in alone.outputs.items():
            np.testing.assert_allclose(shared.outputs[name], values, equal_nan=True, err_msg=f"{model_id} {j} {name}")
        for a, b in ((shared.level, alone.level), (shared.susceptibility, alone.susceptibility)):
            assert (a is None) == (b is None)
            if a is not None:
                np.testing.assert_array_equal(a, b)
        assert shared.windows == alone.windows, (model_id, j)
        assert shared.estimated.keys() == alone.estimated.keys() and shared.missing.keys() == alone.missing.keys()


def test_a_stage_biofix_can_differ_between_scenarios():
    names = runner.required_inputs(model("early-blight-pdays"))
    kwargs = {"dates": DATES, "latitude": LATITUDE, "start": START, "planting": PLANTING}
    runs = scenarios.run_scenarios("early-blight-pdays", daily={n: DAILY[n] for n in names}, **kwargs)
    assert runs[1].biofix is not None and runs[0].biofix is not None and runs[1].biofix < runs[0].biofix  # warmer


def test_the_spread_needs_two_scenarios_for_a_band():
    s = scenarios.spread([np.array([1.0, 2.0, np.nan]), np.array([3.0, np.nan, np.nan]), np.array([5.0, 4.0, np.nan])])
    assert s.p50.tolist()[:2] == [3.0, 3.0] and np.isnan(s.p50[2])
    assert s.p10[0] == pytest.approx(1.4) and s.p90[0] == pytest.approx(4.6)
    assert s.count.tolist() == [3, 2, 0]
    one = scenarios.spread([np.array([1.0])])
    assert one.p50[0] == 1.0 and np.isnan(one.p10[0]) and np.isnan(one.p90[0])


def test_milestones_say_when_stages_and_risk_levels_come_across_scenarios():
    names = runner.required_inputs(model("corn-stages"))
    runs = scenarios.run_scenarios(
        "corn-stages",
        daily={n: DAILY[n] for n in names},
        dates=DATES,
        latitude=LATITUDE,
        start=PLANTING,
        biofix=PLANTING,
    )
    found = {r.name: r for r in scenarios.milestones(model("corn-stages"), runs)}
    ve = found["VE"]
    assert ve.reached == 3 and ve.of == 3 and ve.p10 is not None and ve.p90 is not None and ve.p10 <= ve.p90
    blight_names = runner.required_inputs(model("late-blight-dsv"))
    blight = scenarios.run_scenarios(
        "late-blight-dsv", daily={n: DAILY[n] for n in blight_names}, dates=DATES, latitude=LATITUDE, start=START
    )
    levels = [r for r in scenarios.milestones(model("late-blight-dsv"), blight) if r.what == "risk"]
    assert [r.name for r in levels] == list(model("late-blight-dsv").SPEC.risk.levels[1:])  # type: ignore[union-attr]
    assert all(r.p50 is None or r.p50 >= START for r in levels)
    seedcorn = runner.required_inputs(model("seedcorn-maggot"))
    flies = scenarios.run_scenarios(
        "seedcorn-maggot", daily={n: DAILY[n] for n in seedcorn}, dates=DATES, latitude=LATITUDE, start=date(2025, 1, 1)
    )
    windows = [r for r in scenarios.milestones(model("seedcorn-maggot"), flies) if r.what == "window"]
    first = windows[0]
    assert first.reached == 3 and first.p50 is not None and first.p10 is not None
    assert first.p50 - first.p10 < timedelta(days=60)
