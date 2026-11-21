"""Alfalfa weevil (docs/models-plan.md part H4): NEWA's method and table (D95), Harcourt 1981's stage durations and
Litsinger and Apple 1973's larval development as the curves' checks."""

import numpy as np
import pytest

from agmodels.insects.alfalfa_weevil import INSECT
from agmodels.phenology import DD_STEP, PhenologyModel, curves, dd_grid, generation_densities, pert_sd

MODEL = PhenologyModel(insect=INSECT, summary="")
WINDOW = "window_scout_stem_tips_for_larval_feeding"
# NEWA's table (°F·d above 48 °F from January 1, "peak (50%) occurrence", from R. I. Carruthers) and Harcourt 1981's
# peaks (°C·d above 9 °C from April 1, Table II), the same events
NEWA_F = {"hatch": 280, "instar 1": 315, "instar 2": 395, "instar 3": 470, "instar 4": 550, "cocooning": 600, "pupa": 725, "adults": 815}  # fmt: skip
HARCOURT_C = {"hatch": 155, "instar 1": 176, "instar 2": 218, "instar 3": 260, "instar 4": 306, "cocooning": 335, "pupa": 403, "adults": 454}  # fmt: skip


def at(name: str, fraction: float) -> float:
    return float(np.interp(fraction, curves(INSECT)[name], dd_grid()))


def test_newas_method_simple_average_above_48f_from_january_1_without_an_upper_threshold():
    assert (INSECT.dd_method, INSECT.base_f, INSECT.upper_f, INSECT.biofix) == ("average", 48, None, "01-01")
    lo_c = (np.array([40.0, 45.0, 60.0, 70.0]) - 32) / 1.8
    hi_c = (np.array([50.0, 60.0, 80.0, 100.0]) - 32) / 1.8
    out = MODEL.outputs({"air_temperature_min": lo_c, "air_temperature_max": hi_c})
    np.testing.assert_allclose(out["dd"], [0.0, 4.5, 22.0, 37.0], atol=1e-9)  # no cap at 86 °F on the hot day


def test_newas_table_is_harcourts_peaks_in_fahrenheit():
    for event, c in HARCOURT_C.items():
        assert abs(c * 1.8 - NEWA_F[event]) <= 4, event


def test_the_curves_pass_half_of_each_event_at_newas_totals():
    assert at("generations_egg_hatch", 0.5) == pytest.approx(NEWA_F["hatch"], abs=1)
    assert at("generations_larval_feeding", 0.5) == pytest.approx(NEWA_F["cocooning"], abs=1)
    assert at("generations_pupae_in_cocoons", 0.5) == pytest.approx(NEWA_F["adults"], abs=1)


def test_stage_durations_match_harcourts_and_litsinger_and_apples():
    larvae, cocoons, adults = INSECT.life_stages[1:]
    # Larval period, hatch to cocooning: Harcourt's four instars (42 + 42 + 46 + 58 °C·d) and Litsinger and Apple's
    # Wisconsin larvae (eclosion to 50 % prepupa, 297.9 TU above 48 °F) bracket NEWA's 320
    assert 297.9 <= larvae.duration <= (42 + 42 + 46 + 58) * 1.8  # type: ignore[union-attr]
    # Prepupa and pupa: Harcourt's 39 + 80 °C·d; NEWA's cocooning to adult emergence, 815 − 600
    assert cocoons.duration == pytest.approx((39 + 80) * 1.8, abs=2)  # type: ignore[union-attr]
    assert cocoons.lag + cocoons.duration == adults.lag == NEWA_F["adults"] - NEWA_F["hatch"]  # type: ignore[union-attr]


def test_hatch_is_spread_but_narrower_than_harcourts_pooled_probit():
    # Harcourt's Fig. 1: probit of % hatch = −1.3371 + 0.0086 × °C·d, so 10 and 90 % at 279 ∓ 268 °F·d
    probit_sd_f = 1.8 / 0.0086
    ten, ninety = at("generations_egg_hatch", 0.1), at("generations_egg_hatch", 0.9)
    assert (round(ten), round(ninety)) == (138, 421)
    hatch = INSECT.life_stages[0]
    assert pert_sd(start=hatch.start, peak=hatch.peak, end=hatch.end) / probit_sd_f == pytest.approx(0.5, abs=0.01)  # type: ignore[union-attr]


def test_one_generation_and_risk_is_larval_feeding():
    assert INSECT.generation_dd is None
    assert len(generation_densities(insect=INSECT, stage=INSECT.life_stages[0])) == 1  # type: ignore[arg-type]
    assert [s.weight for s in INSECT.life_stages] == [0, 1, 0, 0]
    peak = float(dd_grid()[np.argmax(curves(INSECT)["activity_larval_feeding"])])
    assert NEWA_F["instar 2"] < peak < NEWA_F["instar 3"]  # most larvae present between instar 2's and 3's peaks
    assert MODEL.explore(dd_total=peak)["risk"] == pytest.approx(1.0, abs=1e-3)
    assert MODEL.explore(dd_total=1200)["risk"] < 1e-3


def test_the_scouting_window_runs_from_half_the_eggs_hatched_until_all_have():
    open_dd = dd_grid()[curves(INSECT)[WINDOW] > 0]
    assert open_dd[0] == pytest.approx(NEWA_F["hatch"], abs=DD_STEP)
    # it closes about when NEWA's scouting does (315–599) and UW–Madison's heaviest feeding (600–800) begins
    assert 500 <= open_dd[-1] <= NEWA_F["cocooning"]
    assert np.all(np.diff(open_dd) == DD_STEP)  # one period
