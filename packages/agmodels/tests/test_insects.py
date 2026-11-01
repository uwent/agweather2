import csv
from pathlib import Path

import numpy as np
import pytest

from agmodels.models import oak_wilt
from agmodels.phenology import Insect, InsectModel, severity, stage_index
from agmodels.registry import all_insects, all_models, model

FIXTURES = Path(__file__).parent / "fixtures"
VDIFN_ARRAYS = {  # as in make_vdifn_fixtures.rb
    "generations_1": ((300, 504, 814),),
    "generations_2": ((325, 520, 750), (1115, 1310, 1540)),
    "touching": ((265, 895, 1115), (1115, 1375, 2500)),
    "generations_4": ((340, 675, 1010), (1010, 1350, 1685), (1685, 2025, 2360), (2360, 2700, 3375)),
}


def vdifn(name):
    with (FIXTURES / name).open() as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("array", list(VDIFN_ARRAYS))
def test_vdifn_generations_match_its_severity(array):
    rows = [r for r in vdifn("vdifn_insect_severity_sweep.csv") if r["array"] == array and r["freezing"] == "0"]
    insect = Insect(
        id="x",
        name="x",
        crops=(),
        base_f=50,
        upper_f=None,
        biofix="01-01",
        generations=VDIFN_ARRAYS[array],
    )
    dd = np.array([float(r["dd"]) for r in rows])
    np.testing.assert_array_equal(severity(dd, insect), [float(r["severity"]) for r in rows])


def test_oak_wilt_matches_vdifn():
    rows = vdifn("vdifn_oak_wilt_sweep.csv")
    dd = np.array([float(r["dd"]) for r in rows])
    doy = np.array([float(r["day_of_year"]) for r in rows])
    ours = [oak_wilt.explore(d, y)["risk"] for d, y in zip(dd, doy, strict=True)]
    np.testing.assert_array_equal(ours, [float(r["severity"]) for r in rows])


@pytest.mark.parametrize(
    # Seedcorn maggot left the tool's step table in 2.0 (D36, D37), so only these two still match it
    ("crt_id", "model_id"),
    [("afw", "alfalfa-weevil"), ("cpb", "colorado-potato-beetle")],
)
def test_crop_risk_tool_insects_match_over_a_year(crt, crt_id, model_id):
    daily, theirs = crt("daily_eau_claire_2025"), crt(f"insect_{crt_id}_eau_claire_2025")
    days = daily["date"].astype("datetime64[D]")
    inputs = {
        "air_temperature_min": daily["temperature_min"],
        "air_temperature_max": daily["temperature_max"],
        "day_of_year": (days - days.astype("datetime64[Y]")).astype(int) + 1,
    }
    m = model(model_id)
    insect = next(i for i in all_insects() if i.id == model_id)
    out = m.outputs(inputs)

    # Degree days match except where the tool skips the upper cutoff: its gdd_sine returns mean - base whenever the
    # min is above the base, before checking the max against the upper threshold (PLAN.md Phase 3 D)
    lo, hi = daily["temperature_min"] * 1.8 + 32, daily["temperature_max"] * 1.8 + 32
    skipped = (lo >= insect.base_f) & (hi > (insect.upper_f or np.inf))
    np.testing.assert_allclose(out["dd"][~skipped], theirs["gdd_f"][~skipped], atol=1e-9)
    np.testing.assert_allclose(theirs["gdd_f"][skipped], (lo + hi)[skipped] / 2 - insect.base_f, atol=1e-9)
    assert (out["dd"][skipped] < theirs["gdd_f"][skipped]).all()

    # From the tool's own totals, the severity, freeze reduction and stage label match exactly
    from_theirs = {"dd_total": theirs["cum_gdd"], "freeze_reduction": out["freeze_reduction"]}
    np.testing.assert_array_equal(m.risk(from_theirs), theirs["severity"])
    labels = ["Before spring emergence"] + [s.label for s in insect.stages]
    assert [labels[int(k) + 1] for k in stage_index(theirs["cum_gdd"], insect.stages)] == theirs["label"].tolist()


def test_every_insect_is_a_model_with_a_severity_rule():
    insects = [m for m in all_models().values() if isinstance(m, InsectModel)]
    assert len(insects) == len(all_insects()) == 26
    for m in insects:
        assert m.insect.life_stages or m.insect.stages or m.insect.generations, m.insect.id
        assert m.SPEC.crops, m.insect.id
        assert m.explore(dd_total=0)["risk" if m.insect.life_stages else "severity"] == 0


def test_oak_wilt_flight_is_cut_from_july_15_when_the_day_of_year_is_given():
    # A cool year at 800 degree days (Very high, level 4): from July 15 (day 196) at most Low, from July 22 (203) lower
    n = 300
    inputs = {"air_temperature_min": np.full(n, -2.0), "air_temperature_max": np.full(n, 12.0)}
    doy = np.arange(1, n + 1, dtype=float)
    plain = oak_wilt.outputs(inputs)
    assert "seasonal" not in plain and plain["flight"][205] == 4  # day 206: Very high without the date
    out = oak_wilt.outputs(inputs | {"day_of_year": doy})
    assert out["seasonal"][194] == out["flight"][194] == 4  # day 195
    assert out["seasonal"][195] == 1  # day 196, July 15: min(4 - 2, 1)
    assert out["seasonal"][202] == 0  # day 203, July 22: one lower again
    np.testing.assert_array_equal(oak_wilt.risk(out), out["seasonal"])
    np.testing.assert_array_equal(oak_wilt.risk(plain), plain["flight"])


def test_oak_wilts_july_reductions_apply_to_runs_and_follow_the_calendar_in_leap_years():
    from datetime import date, timedelta

    from agmodels import runner

    for year in (2025, 2024):
        dates = [date(year, 1, 1) + timedelta(days=n) for n in range(240)]
        cool = {"air_temperature_min": np.full(240, -2.0), "air_temperature_max": np.full(240, 12.0)}
        result = runner.run("oak-wilt-vectors", dates=dates, daily=cool, latitude=43.0)
        assert result.risk is not None
        level = dict(zip(result.dates, result.risk.tolist(), strict=True))
        # Flight is Very high (4) all July this cool year; Low (1) from July 15, Very low (0) from July 22
        assert [level[date(year, 7, d)] for d in (14, 15, 21, 22)] == [4, 1, 1, 0]
