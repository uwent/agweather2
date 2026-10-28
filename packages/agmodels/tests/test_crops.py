"""Crop growth-stage models against their sources' benchmarks and the field seasons they were fitted or tested on."""

import csv
import datetime as dt
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from agmodels.crops import (
    MARGIN,
    SUSCEPTIBLE,
    CropModel,
    disease_susceptibility,
    stage_days,
    stage_reached,
    susceptibility,
)
from agmodels.degree_days import degree_days_modified
from agmodels.models import corn_stages as corn
from agmodels.models import soybean_stages as soy
from agmodels.registry import all_models
from agmodels.weather import day_length_hours

FIXTURES = Path(__file__).parent / "fixtures"


def season(site: str, year: int):
    """Day of year and daily min, max and mean temperature (°C) for a recorded field season."""
    with (FIXTURES / "phenology_weather.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if r["site"] == site and r["date"].startswith(str(year))]
    doy = np.array([dt.date.fromisoformat(r["date"]).timetuple().tm_yday for r in rows])
    lo, hi, mean = (
        np.array([float(r[k]) for r in rows]) for k in ("temperature_min", "temperature_max", "temperature_mean")
    )
    return doy, lo, hi, mean


def first_day(doy, stage, stages, code) -> int:
    passed = stage >= [s.code for s in stages].index(code)
    assert passed.any(), f"{code} never reached"
    return int(doy[np.argmax(passed)])


# The engine


def test_stage_reached_skips_stages_a_variety_lacks():
    thresholds = [10, 20, np.nan, 40]
    np.testing.assert_array_equal(stage_reached([0, 10, 25, 39, 40, np.nan], thresholds), [-1, 0, 1, 1, 3, np.nan])


def test_stage_days():
    stage = np.array([[-1, 0], [0, 0], [1, 2], [2, 2]], dtype=float)
    np.testing.assert_array_equal(stage_days(stage, 3), [[1, 0], [2, 2], [3, 2]])


def test_crop_models_have_stages_and_no_risk():
    crops = {k: m for k, m in all_models().items() if m.SPEC.group == "crop"}
    assert {"corn-stages", "soybean-stages"} <= set(crops)
    for model in crops.values():
        assert model.SPEC.risk is None and not hasattr(model, "risk")
        assert model.SPEC.biofix is not None and "Planting" in model.SPEC.biofix.label
        assert cast(CropModel, model).stages()


def test_day_length():
    assert day_length_hours(80, 43.0) == pytest.approx(12.1, abs=0.1)  # equinox: a little over 12 h with refraction
    assert day_length_hours(172, 43.0) == pytest.approx(15.4, abs=0.1)
    assert day_length_hours(172, 43.0, -6) > day_length_hours(172, 43.0)


# Corn


def corn_thresholds(rating):
    return dict(zip((s.code for s in corn.STAGES), corn.thresholds(rating), strict=True))


def test_corn_matches_nch40_for_a_2700_gdd_hybrid():
    # Neild and Newman (1987) Table 3, GDD from planting; R1 comes from Yang et al.'s fit, not NCH-40
    t = corn_thresholds(2700)
    assert t["R1"] == pytest.approx(1400, rel=0.05)
    for code, nch in {"R2": 1660, "R4": 1925, "R5": 2190, "R5.5": 2450, "R6": 2700}.items():
        assert t[code] == pytest.approx(nch, rel=0.03), code
    assert t["V9"] == pytest.approx(838, abs=20)  # Ohio State AGF-0101
    assert t["VE"] == 110 and t["V10"] - t["V9"] == 82 and t["V12"] - t["V11"] == 50


def test_corn_leaves_and_stages_scale_with_maturity():
    leaves = {}
    for rating in (2100, 2500, 2700, 2900, 3100):
        t = corn.thresholds(rating)
        assert np.all(np.diff(t[~np.isnan(t)]) > 0)
        v = [
            code
            for code, g in corn_thresholds(rating).items()
            if code[0] == "V" and code[1:].isdigit() and not np.isnan(g)
        ]
        leaves[rating] = int(v[-1][1:])
    assert leaves[2700] in range(18, 22) and leaves[2100] < leaves[2500] < leaves[2900] < leaves[3100]


@pytest.mark.parametrize(
    ("site", "year", "planting", "emergence", "silking", "maturity"),
    [  # Yang et al. (2004) Table 1, day of year
        ("lincoln", 1999, 133, 141, 202, 256),
        ("lincoln", 2000, 112, 120, 188, 233),
        ("lincoln", 2001, 116, 122, 191, 243),
        ("manchester", 2002, 128, 143, 203, 268),
    ],
)
def test_corn_seasons_from_yang_et_al(site, year, planting, emergence, silking, maturity):
    # As Yang et al. ran them: the season's own GDD to maturity as the rating, silking predicted from it
    doy, lo, hi, _ = season(site, year)
    start = int(np.where(doy == planting)[0][0])
    gdd = degree_days_modified(lo * 1.8 + 32, hi * 1.8 + 32, 50, 86)
    rating = gdd[start : int(np.where(doy == maturity)[0][0])].sum()
    out = corn.outputs(
        {"air_temperature_min": lo, "air_temperature_max": hi}, biofix_index=start, black_layer_gdd=str(rating)
    )
    assert abs(first_day(doy, out["stage"], corn.STAGES, "VE") - emergence) <= 3
    assert abs(first_day(doy, out["stage"], corn.STAGES, "R1") - silking) <= 3
    assert abs(first_day(doy, out["stage"], corn.STAGES, "R6") - maturity) <= 1


def test_corn_on_the_grid_and_through_gaps():
    doy, lo, hi, _ = season("lincoln", 2000)
    grid = {
        k: np.repeat(v[:, None, None], 2, axis=2) for k, v in (("air_temperature_min", lo), ("air_temperature_max", hi))
    }
    grid["air_temperature_min"][50:55, 0, 1] = np.nan  # five missing days hold development back
    stage = corn.outputs(grid, biofix_index=20)["stage"]
    assert stage.shape == (len(doy), 1, 2)
    assert np.isnan(stage[:20]).all() and (stage[60:, 0, 1] <= stage[60:, 0, 0]).all()
    assert (stage[-1] == len(corn.STAGES) - 1).all()


def test_corn_rating_option():
    with pytest.raises(ValueError, match="black_layer_gdd"):
        corn.outputs({"air_temperature_min": np.zeros(3), "air_temperature_max": np.ones(3)}, black_layer_gdd="early")


# Soybean


def test_response_functions():
    assert soy.temperature_response(31.5, soy.T_EMERGENCE) == pytest.approx(1)
    assert soy.temperature_response([5, 45, 50, -3], soy.T_EMERGENCE).tolist() == [0, 0, 0, 0]
    assert 0 < soy.temperature_response(20, soy.T_EMERGENCE) < 1
    f = soy.photoperiod_response([10, 12, 15, 18, 20], *soy.P_POST_FLOWERING)
    assert f[0] == f[1] == 1 and 0 < f[2] < 1 and f[3] == f[4] == 0
    p = soy.parameters(3.0)  # Fig. 4 at MG 3: optimum about 11 h, critical about 25 h (Table 2's V0–R0 values)
    assert p["induction_optimum"] == pytest.approx(11.07, abs=0.01)
    assert p["induction_critical"] == pytest.approx(25.20, abs=0.01)


@pytest.mark.parametrize(
    ("year", "emergence", "r1", "r7"),
    [  # Setiyono et al. (2007) Table 3: NE3001, MG 3.0, Lincoln
        (1999, 136, 175, 252),
        (2000, 134, 170, 248),
        (2001, 125, 169, 255),
        (2002, 140, 176, 252),
        (2004, 131, 174, 250),
        (2005, 130, 171, 249),
    ],
)
def test_soybean_seasons_from_setiyono_et_al(year, emergence, r1, r7):
    # The generalized model (from MG alone) has an RMSE of 3.6 days in the paper; ERA5 isn't the site's own weather
    doy, _, _, mean = season("lincoln", year)
    inputs = {"air_temperature_mean": mean, "day_of_year": doy, "latitude": np.array(40.83)}
    start = int(np.where(doy == emergence)[0][0])
    out = soy.outputs(inputs, biofix_index=start, maturity_group="3.0", biofix_event="emergence")
    assert abs(first_day(doy, out["stage"], soy.STAGES, "R1") - r1) <= 6
    assert abs(first_day(doy, out["stage"], soy.STAGES, "R7") - r7) <= 4
    assert 15 <= np.nanmax(out["nodes"]) <= 25


def test_soybean_from_planting_and_by_maturity_group():
    doy, _, _, mean = season("lincoln", 2004)
    inputs = {"air_temperature_mean": mean, "day_of_year": doy, "latitude": np.array(40.83)}
    start = int(np.where(doy == 125)[0][0])
    days = {}
    for mg in ("1.0", "2.0", "3.0"):
        stage = soy.outputs(inputs, biofix_index=start, maturity_group=mg)["stage"]
        days[mg] = [first_day(doy, stage, soy.STAGES, c) for c in ("VE", "VC", "V1", "R1", "R3", "R5", "R6", "R7")]
        assert days[mg] == sorted(days[mg]) and 128 <= days[mg][0] <= 140
    assert days["1.0"][-1] < days["2.0"][-1] < days["3.0"][-1]


def test_soybean_on_the_grid():
    doy, _, _, mean = season("lincoln", 2004)
    temp = np.repeat(mean[:, None], 3, axis=1)
    out = soy.outputs(
        {"air_temperature_mean": temp, "day_of_year": doy, "latitude": np.array([38.0, 41.0, 46.0])}, biofix_index=40
    )
    assert out["stage"].shape == temp.shape
    r1 = [first_day(doy, out["stage"][:, k], soy.STAGES, "R1") for k in range(3)]
    assert r1[0] < r1[2]  # same weather, longer days in the north delay flowering


# Disease risk by crop stage (D33)


def test_susceptibility_with_margins():
    stages = soy.STAGES
    r = [s.code for s in stages].index
    stage = np.array([np.nan] + [r("V3")] * 6 + [r("R1")] * 3 + [r("R2")] * 2 + [r("R4")] * 4 + [r("R5")] * 8)
    level = susceptibility(stage, stages, "R1", "R3", margin_days=2)
    np.testing.assert_array_equal(level, [np.nan, 0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 2, 1, 1, 0, 0, *[0] * 8])
    with pytest.raises(ValueError):
        susceptibility(stage, stages, "R3", "R1", 2)


def test_gated_models_name_real_stages():
    gated = {k: m.SPEC for k, m in all_models().items() if m.SPEC.susceptible is not None}
    assert {"tar-spot", "gray-leaf-spot", "gibberella-ear-rot-don", "white-mold", "frogeye-leaf-spot"} <= set(gated)
    for spec in gated.values():
        gate = spec.susceptible
        assert gate is not None and gate.source
        crop = cast(CropModel, all_models()[gate.crop])
        codes = [s.code for s in crop.stages()]
        assert codes.index(gate.first) <= codes.index(gate.last)
        assert set(crop.SPEC.crops) & set(spec.crops)
    anchored = all_models()["red-crown-rot"].SPEC.biofix_stage
    assert anchored is not None and anchored[1] in [s.code for s in soy.STAGES]


def test_tar_spot_and_don_windows_over_a_season():
    doy, lo, hi, _ = season("lincoln", 2000)
    stage = corn.outputs({"air_temperature_min": lo, "air_temperature_max": hi}, biofix_index=21)["stage"]  # Apr 22
    tar = disease_susceptibility(all_models()["tar-spot"].SPEC, stage)
    don = disease_susceptibility(all_models()["gibberella-ear-rot-don"].SPEC, stage)
    assert tar is not None and don is not None
    susceptible = lambda level: doy[level == SUSCEPTIBLE]  # noqa: E731
    assert 60 > len(susceptible(tar)) > 25  # V10 to the end of milk: about six weeks
    assert 3 <= len(susceptible(don)) <= 10  # silking
    assert susceptible(tar)[0] < susceptible(don)[0] and susceptible(don)[-1] < susceptible(tar)[-1]
    assert np.sum(tar == MARGIN) == 2 * corn.MARGIN_DAYS
    assert disease_susceptibility(all_models()["late-blight-dsv"].SPEC, stage) is None
