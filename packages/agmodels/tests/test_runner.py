from datetime import date, timedelta

import numpy as np
import pytest

from agmodels import runner
from agmodels.crops import SUSCEPTIBLE
from agmodels.gaps import GapFill
from agmodels.registry import all_models, model

FIRST = date(2024, 9, 1)
DAYS = 520  # to early February 2026
DATES = [FIRST + timedelta(days=k) for k in range(DAYS)]
LATITUDE = 43.1


def year_of_weather() -> dict[str, np.ndarray]:
    """A plausible Wisconsin daily series for every input any model reads."""
    rng = np.random.default_rng(3)
    doy = np.array([d.timetuple().tm_yday for d in DATES], dtype=float)
    season = -np.cos(2 * np.pi * (doy - 15) / 365)  # −1 mid-January, +1 mid-July
    mean = 8 + 16 * season + rng.normal(0, 2.5, DAYS)
    rh_mean = 72 + 8 * rng.standard_normal(DAYS)
    hours_humid = np.clip(np.round(6 + 4 * season + 3 * rng.standard_normal(DAYS)), 0, 24)
    soil = 8 + 12 * season
    return {
        "air_temperature_mean": mean,
        "air_temperature_min": mean - 6,
        "air_temperature_max": mean + 6,
        "dew_point_min": mean - 9,
        "dew_point_depression_max": np.full(DAYS, 9.0),
        "dew_point_depression_mean": np.full(DAYS, 4.0),
        "relative_humidity_mean": np.clip(rh_mean, 30, 100),
        "relative_humidity_max": np.clip(rh_mean + 20, 30, 100),
        "precipitation_sum": np.where(rng.random(DAYS) < 0.3, rng.exponential(6, DAYS), 0.0),
        "wind_speed_max": np.full(DAYS, 6.0),
        "hours_rh_over_80": hours_humid + 3,
        "hours_rh_over_90": hours_humid,
        "hours_rh_over_90_from_8pm": hours_humid,
        "hours_rh_over_90_night": np.minimum(hours_humid, 10),
        "hours_rh_over_90_temperature_over_70f": np.where(mean > 21, hours_humid / 2, 0),
        "hours_rh_under_70": 24 - hours_humid - 3,
        "hours_temperature_over_30c": np.where(mean + 6 > 30, 3.0, 0.0),
        "temperature_mean_rh_over_90_from_8pm": mean - 2,
        "hours_soil_4cm_below_27f": np.where(soil - 4 < -3, 12.0, 0.0),
        "hours_soil_10cm_below_27f": np.where(soil - 2 < -3, 8.0, 0.0),
        "hours_soil_8in_below_27f": np.where(soil < -3, 4.0, 0.0),
        "soil_temperature_4cm_min": soil - 4,
        "soil_temperature_10cm_min": soil - 2,
        "soil_temperature_30cm_min": soil,
    }


WEATHER = year_of_weather()


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_every_model_runs_through_the_runner(model_id):
    m = model(model_id)
    for name in runner.required_inputs(m):
        assert name in WEATHER, name
    start = date(2025, 6, 1) if m.SPEC.season is None or m.SPEC.season[0] < m.SPEC.season[1] else date(2025, 11, 1)
    result = runner.run(m, dates=DATES, daily=WEATHER, latitude=LATITUDE, start=start, planting=date(2025, 5, 10))
    assert result.reason is None, result.reason
    assert result.model_id == model_id and result.version == m.SPEC.version
    assert result.dates[0] == start and len(result.dates) == DAYS - (start - FIRST).days
    for name, values in result.outputs.items():
        assert values.shape[0] == len(result.dates), name
    assert (result.risk is None) == (m.SPEC.risk is None)
    if result.level is not None and m.SPEC.risk is not None:
        finite = result.level[np.isfinite(result.level)]
        assert ((finite >= 0) & (finite < len(m.SPEC.risk.levels))).all(), model_id


def test_outputs_match_the_model_called_directly():
    m = model("late-blight-dsv")
    result = runner.run(m, dates=DATES, daily=WEATHER, latitude=LATITUDE, start=date(2025, 5, 1))
    k = (date(2025, 5, 15) - FIRST).days
    direct = m.outputs({q.name: WEATHER[q.name] for q in m.SPEC.inputs}, biofix_index=k)
    shown = (date(2025, 5, 1) - FIRST).days
    for name, values in direct.items():
        np.testing.assert_array_equal(result.outputs[name], values[shown:])
    assert result.biofix == date(2025, 5, 15)
    # Late blight's season is May 1 to September 30
    assert (
        result.in_season is not None
        and result.in_season[0]
        and not result.in_season[(date(2025, 10, 1) - date(2025, 5, 1)).days]
    )


def test_default_biofix_follows_the_season():
    assert runner.default_biofix(model("late-blight-dsv").SPEC, date(2025, 7, 1)) == date(2025, 5, 15)
    potato = model("potato-volunteer").SPEC  # Oct 1 to Sep 30
    assert runner.default_biofix(potato, date(2026, 1, 15)) == date(2025, 10, 1)
    assert runner.default_biofix(potato, date(2025, 10, 2)) == date(2025, 10, 1)
    rye = model("rye-biomass").SPEC  # Sep 1 to Jun 30, biofix Oct 1
    assert runner.default_biofix(rye, date(2026, 3, 1)) == date(2025, 10, 1)
    assert runner.default_biofix(rye, date(2025, 7, 15)) == date(2025, 10, 1)  # between seasons: the next one
    assert runner.default_biofix(rye, date(2025, 9, 10)) == date(2025, 10, 1)
    assert runner.default_biofix(model("tar-spot").SPEC, date(2025, 7, 1)) is None


def test_stage_gating_needs_a_planting_date():
    gated = runner.run("tar-spot", dates=DATES, daily=WEATHER, latitude=LATITUDE, planting=date(2025, 5, 10))
    assert gated.susceptibility is not None and (gated.susceptibility == SUSCEPTIBLE).any()
    assert runner.run("tar-spot", dates=DATES, daily=WEATHER, latitude=LATITUDE).susceptibility is None


def test_a_biofix_at_a_crop_stage():
    result = runner.run(
        "red-crown-rot",
        dates=DATES,
        daily=WEATHER,
        latitude=LATITUDE,
        start=date(2025, 6, 1),
        planting=date(2025, 5, 17),
    )
    soybean = runner.run(
        "soybean-stages",
        dates=DATES,
        daily=WEATHER,
        latitude=LATITUDE,
        biofix=date(2025, 5, 17),
        start=date(2025, 5, 17),
    )
    codes = [s.code for s in model("soybean-stages").stages()]  # type: ignore[attr-defined]
    r1 = int(np.argmax(soybean.outputs["stage"] >= codes.index("R1")))
    assert result.biofix == soybean.dates[r1]
    assert result.biofix is not None and date(2025, 6, 25) < result.biofix < date(2025, 8, 1)


def test_blight_starts_at_the_emergence_a_planting_date_gives():
    planting = date(2025, 5, 1)
    potato = runner.run("potato-stages", dates=DATES, daily=WEATHER, latitude=LATITUDE, biofix=planting, start=planting)
    emerged = potato.dates[int(np.argmax(potato.outputs["stage"] >= 1))]
    assert planting < emerged < date(2025, 6, 15)
    for model_id in ("early-blight-pdays", "late-blight-dsv"):
        result = runner.run(model_id, dates=DATES, daily=WEATHER, latitude=LATITUDE, planting=planting)
        assert result.biofix == emerged, model_id
        k = result.dates.index(emerged)
        total = result.outputs["pdays_total" if model_id == "early-blight-pdays" else "dsv_total"]
        daily = result.outputs["pdays" if model_id == "early-blight-pdays" else "dsv"]
        assert np.isnan(total[:k]).all() and total[k] == daily[k], model_id  # the total starts at emergence
        unplanted = runner.run(model_id, dates=DATES, daily=WEATHER, latitude=LATITUDE, start=planting)
        assert unplanted.biofix == date(2025, 5, 15), model_id  # without a planting date, the spec's default


def test_a_stage_biofix_not_yet_reached_means_not_started():
    last = date(2025, 5, 3)  # two days after planting: not emerged
    days = (last - DATES[0]).days + 1
    daily = {name: values[:days] for name, values in WEATHER.items()}
    result = runner.run(
        "early-blight-pdays", dates=DATES[:days], daily=daily, latitude=LATITUDE, planting=date(2025, 5, 1)
    )
    assert result.reason == "EM isn't reached in the series" and not result.outputs and result.biofix is None


def test_action_windows_become_dates():
    result = runner.run("seedcorn-maggot", dates=DATES, daily=WEATHER, latitude=LATITUDE, start=date(2025, 1, 1))
    periods = result.windows["Avoid planting during adult flight"]
    assert len(periods) >= 2
    first_start, first_end = periods[0]
    assert date(2025, 4, 1) < first_start < first_end < date(2025, 7, 1)


def test_outside_the_region_and_a_biofix_outside_the_series():
    outside = runner.run("pecan-scab", dates=DATES, daily=WEATHER, latitude=LATITUDE, in_region=False)
    assert outside.reason == "outside the model's region" and not outside.outputs
    early = runner.run(
        "late-blight-dsv", dates=DATES, daily=WEATHER, latitude=LATITUDE, start=FIRST, biofix=date(2024, 5, 1)
    )
    assert early.reason == "biofix not in the series"
    winter = DATES[130:220]  # January 9 to April 8, 2025
    late = runner.run(
        "late-blight-dsv", dates=winter, daily={k: v[130:220] for k, v in WEATHER.items()}, latitude=LATITUDE
    )
    assert late.reason == "biofix after the series" and late.biofix == date(2025, 5, 15)


def test_first_day_needed():
    assert runner.first_day_needed(model("tar-spot"), date(2025, 7, 1)) == date(2025, 6, 1)  # 30 days back
    assert runner.first_day_needed(model("late-blight-dsv"), date(2025, 7, 1)) == date(2025, 5, 15)
    assert runner.first_day_needed(model("tar-spot"), date(2025, 7, 1), planting=date(2025, 5, 1)) == date(2025, 5, 1)


def test_continuous_risk_becomes_levels():
    m = model("seedcorn-maggot")
    result = runner.run(m, dates=DATES, daily=WEATHER, latitude=LATITUDE, start=date(2025, 1, 1))
    assert m.SPEC.risk is not None and m.SPEC.risk.thresholds
    assert result.risk is not None and result.level is not None
    expected = np.searchsorted(np.asarray(m.SPEC.risk.thresholds), result.risk, side="right")
    np.testing.assert_array_equal(result.level, expected)
    assert result.level.max() >= 2


def test_gaps_in_the_inputs_are_estimated_and_reported():
    from agmodels.models import red_crown_rot

    daily = {name: values.copy() for name, values in WEATHER.items()}
    r1 = date(2025, 7, 1)
    k = DATES.index(r1)
    daily["air_temperature_mean"][k + 3] = np.nan  # a day from R1
    daily["precipitation_sum"][k - 10 : k - 8] = np.nan  # two days before it
    methods: dict[str, GapFill] = {"air_temperature_mean": "interpolate", "precipitation_sum": "zero"}
    result = runner.run(
        "red-crown-rot", dates=DATES, daily=daily, latitude=LATITUDE, start=r1, biofix=r1, gap_fill=methods
    )
    assert np.isnan(result.inputs["air_temperature_mean"][3])  # the inputs layer keeps the gap
    assert result.estimated["air_temperature_mean"].nonzero()[0].tolist() == [3]
    assert "precipitation_sum" not in result.estimated  # its filled days are before the days shown
    assert result.outputs["precipitation_days_missing"][0] == 2
    assert np.isfinite(result.outputs["incidence"][: red_crown_rot.WINDOW]).all()

    assert result.missing == {}  # every gap was filled

    unfilled = runner.run("red-crown-rot", dates=DATES, daily=daily, latitude=LATITUDE, start=r1, biofix=r1)
    assert unfilled.estimated == {} and unfilled.outputs["precipitation_days_missing"][0] == 2
    assert unfilled.missing["air_temperature_mean"].nonzero()[0].tolist() == [3]

    daily["air_temperature_mean"][k + 5 : k + 15] = np.nan  # ten days: too long to bridge
    long = runner.run(
        "red-crown-rot", dates=DATES, daily=daily, latitude=LATITUDE, start=r1, biofix=r1, gap_fill=methods
    )
    assert long.missing["air_temperature_mean"].nonzero()[0].tolist() == list(range(5, 15))


def _model_inputs(m, *, shape: tuple[int, ...] = ()) -> dict[str, np.ndarray]:
    """The model's inputs from the year of weather; a grid's cells are each warmed or cooled by a few degrees."""
    cells = int(np.prod(shape)) if shape else 1
    shifts = np.linspace(-4, 4, cells).reshape(shape) if shape else np.array(0.0)
    inputs = {}
    for q in m.SPEC.inputs:
        series = WEATHER[q.name]
        temperature = q.unit == "degC"
        cell_series = series[(slice(None),) + (None,) * len(shape)] + (shifts if temperature else 0.0)
        inputs[q.name] = np.broadcast_to(cell_series, (DAYS, *shape)).copy()
    context = runner._context(DATES, LATITUDE)
    inputs |= {name: context[name] for name in m.SPEC.context}
    if "day_of_year" in inputs:
        inputs["day_of_year"] = context["day_of_year"]
    return inputs


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_a_grid_gives_every_cell_what_its_point_series_gives(model_id):
    m = model(model_id)
    shape = (2, 3)
    grid = _model_inputs(m, shape=shape)
    biofix = 120  # a biofix inside the series, which models anchor on
    out = m.outputs(grid, biofix_index=biofix)
    assert out
    for name, values in out.items():
        assert values.shape == (DAYS, *shape), (model_id, name)
    for cell in np.ndindex(shape):
        point_inputs = {
            k: (v if v.ndim == 1 or k in m.SPEC.context else v[:, cell[0], cell[1]]) for k, v in grid.items()
        }
        point = m.outputs(point_inputs, biofix_index=biofix)
        for name, values in out.items():
            np.testing.assert_allclose(
                values[:, cell[0], cell[1]], point[name], equal_nan=True, err_msg=f"{model_id} {name}"
            )
    if m.SPEC.risk is not None:
        level = m.risk(out, biofix_index=biofix)
        assert level.shape == (DAYS, *shape)
        cell = (1, 2)
        point = m.risk({k: v[:, cell[0], cell[1]] for k, v in out.items()}, biofix_index=biofix)
        np.testing.assert_allclose(level[:, cell[0], cell[1]], point, equal_nan=True, err_msg=model_id)


# Models whose risk is a level, not NaN, when every input is missing. Their totals add nothing for a missing day
# (accumulate.py: "a missing day adds nothing"), so nothing seen reads as the lowest level, and the runner reports the
# missing days (ModelRun.missing) for the interface to say so. Potato volunteer reads no killing hours as survival.
NO_DATA_GIVES_A_LEVEL = {
    "alfalfa-weevil", "aphid-pvy-vectors", "black-cutworm", "botrytis-onion-botcast", "cabbage-looper",
    "cabbage-maggot", "carrot-foliar-dsv", "cercospora-beet-div", "colorado-potato-beetle",
    "colorado-potato-beetle-adults", "colorado-potato-beetle-larvae", "common-asparagus-beetle", "corn-earworm",
    "corn-rootworm", "crucifer-flea-beetle", "early-blight-pdays", "european-corn-borer", "imported-cabbageworm",
    "japanese-beetle", "late-blight-dsv", "mint-flea-beetle", "mint-root-borer", "oak-wilt-vectors", "onion-maggot",
    "pecan-scab", "potato-volunteer", "rye-biomass", "seedcorn-maggot", "spotted-wing-drosophila",
    "squash-vine-borer", "stalk-borer", "tarnished-plant-bug", "variegated-cutworm", "western-bean-cutworm",
    "western-flower-thrips",
}  # fmt: skip


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_a_model_without_any_weather_gives_no_risk_but_its_documented_level(model_id):
    m = model(model_id)
    inputs = {k: np.full_like(v, np.nan) for k, v in _model_inputs(m).items() if k not in m.SPEC.context}
    inputs |= {k: v for k, v in _model_inputs(m).items() if k in m.SPEC.context}
    out = m.outputs(inputs)
    if m.SPEC.risk is None:
        # a crop model's stage, with no weather, stays at its "not emerged" value
        assert all(len(np.unique(v[np.isfinite(v)])) <= 1 for v in out.values()), model_id
        return
    level = m.risk(out)
    known = level[np.isfinite(level)]
    assert (known.size > 0) == (model_id in NO_DATA_GIVES_A_LEVEL), model_id
    assert len(np.unique(known)) <= 1, f"{model_id}: a risk that varies with no weather"
    if model_id != "potato-volunteer":  # the rest read "nothing counted" as the lowest level
        assert known.size == 0 or (known == 0).all(), model_id


def test_a_start_outside_the_series_is_an_error():
    with pytest.raises(ValueError, match="isn't in the series"):
        runner.run("late-blight-dsv", dates=DATES, daily=WEATHER, latitude=LATITUDE, start=date(2030, 1, 1))


def test_a_planting_date_outside_the_series_leaves_the_stage_gate_off():
    # Planted before the series begins: its stage can't be known, so the gated disease isn't gated (as with no planting)
    run = runner.run("tar-spot", dates=DATES, daily=WEATHER, latitude=LATITUDE, planting=date(2024, 5, 1))
    assert run.susceptibility is None and run.reason is None
