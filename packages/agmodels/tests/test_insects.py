import csv
from pathlib import Path

import numpy as np
import pytest

from agmodels.models import oak_wilt
from agmodels.phenology import Insect, InsectModel, _sine_ramp, _sine_ramp_reference, severity
from agmodels.registry import all_insects, all_models

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


def test_the_sine_ramp_by_its_steps_matches_the_sine():
    """The ramp found from its steps equals VDIFN's sine rounded up, at every 0.01 °F·d (the steps themselves
    included) and at random totals, for every insect's generations and the fixtures'."""
    spans = {g for i in all_insects() for g in i.generations} | {g for a in VDIFN_ARRAYS.values() for g in a}
    rng = np.random.default_rng(seed=1)
    for start, peak, end in sorted(spans):
        total = np.concatenate([np.round(np.arange(start, end + 0.005, 0.01), 2), rng.uniform(start, end, 2000)])
        np.testing.assert_array_equal(
            _sine_ramp(total, start, peak, end),
            _sine_ramp_reference(total, start, peak, end),
            err_msg=str((start, peak, end)),
        )


@pytest.mark.parametrize("array", list(VDIFN_ARRAYS))
def test_vdifn_generations_match_its_severity(array):
    rows = [r for r in vdifn("vdifn_insect_severity_sweep.csv") if r["array"] == array and r["freezing"] == "0"]
    insect = Insect(
        opens="calendar",
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


def test_oak_wilts_share_flown_follows_jagemanns_table_4():
    """`flown` is the highest of Table 4's percentiles reached, at the table's degree days × 1.8 rounded to whole °F,
    the same bounds as the flight levels' (5, 10, 25, 75, 90 and 95%)."""
    table_c = {5: 128.3, 10: 157.4, 25: 215.8, 50: 354.2, 75: 507.2, 90: 995.4, 95: 1206.7}  # Jagemann et al. 2018
    bounds = dict(oak_wilt.FLOWN_F)
    assert bounds == {5: 231, 10: 283, 25: 388, 50: 638, 75: 913, 90: 1792, 95: 2172}
    for percent, dd_c in table_c.items():
        assert abs(bounds[percent] - dd_c * 1.8) < 0.5
    levels = {bound for bound, _ in oak_wilt.FLIGHT if np.isfinite(bound)} - {180}
    assert levels == {bounds[p] for p in (5, 10, 25, 75, 90, 95)}
    totals = [0, 230.9, 231, 282.9, 283, 388, 637.9, 638, 912.9, 913, 1792, 2171.9, 2172, 5000, np.nan]
    np.testing.assert_array_equal(
        oak_wilt.flown_percent(totals), [0, 0, 5, 5, 10, 25, 25, 50, 50, 75, 90, 90, 95, 95, np.nan]
    )
    grid = oak_wilt.flown_percent(np.full((4, 2, 3), 700.0))
    assert grid.shape == (4, 2, 3) and (grid == 50).all()


def test_oak_wilts_runs_give_the_share_flown():
    inputs = {"air_temperature_min": np.full(200, -2.0), "air_temperature_max": np.full(200, 12.0)}
    out = oak_wilt.outputs(inputs)
    np.testing.assert_array_equal(out["flown"], oak_wilt.flown_percent(out["dd_total"]))
    assert out["flown"][0] == 0 and out["flown"][-1] == 50  # ~802 °F·d by day 200 of this cool year


def test_every_insect_is_a_model_with_a_severity_rule():
    insects = [m for m in all_models().values() if isinstance(m, InsectModel)]
    assert len(insects) == len(all_insects()) == 29
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
