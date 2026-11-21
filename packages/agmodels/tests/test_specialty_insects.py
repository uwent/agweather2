"""Japanese beetle, mint root borer, mint flea beetle and squash vine borer (part H, H5): rebuilt on USPest's models
and the extension guides as D36 curves, checked against their sources' own numbers."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_sine
from agmodels.insects import japanese_beetle, mint_flea_beetle, mint_root_borer, squash_vine_borer
from agmodels.phenology import DD_STEP, DerivedStage, Insect, LifeStage, curves, dd_grid, generation_densities

X = dd_grid()
JB, MRB, MFB, SVB = (m.INSECT for m in (japanese_beetle, mint_root_borer, mint_flea_beetle, squash_vine_borer))


def stage(insect: Insect, label: str):
    return next(s for s in insect.life_stages if s.label == label)


def timed(insect: Insect, label: str) -> LifeStage:
    s = stage(insect, label)
    assert isinstance(s, LifeStage)
    return s


def derived(insect: Insect, label: str) -> DerivedStage:
    s = stage(insect, label)
    assert isinstance(s, DerivedStage)
    return s


def entered(insect: Insect, label: str) -> np.ndarray:
    """The share of a stage's individuals that have entered it (cumulative, 0 to 1) on the degree-day grid."""
    s = stage(insect, label)
    if isinstance(s, LifeStage):
        return np.cumsum(generation_densities(insect=insect, stage=s)[0]) * DD_STEP
    assert isinstance(s, DerivedStage)
    return np.interp(X - s.lag, X, entered(insect, s.follows), left=0)


def left(insect: Insect, label: str) -> np.ndarray:
    s = stage(insect, label)
    assert isinstance(s, DerivedStage)
    return np.interp(X - s.duration, X, entered(insect, label), left=0)


def dd_at(share: np.ndarray, fraction: float) -> float:
    return float(np.interp(fraction, share, X))


def window(insect: Insect) -> tuple[float, float]:
    (table,) = (t for k, t in curves(insect).items() if k.startswith("window_"))
    open_ = np.flatnonzero(table)
    assert np.all(np.diff(open_) == 1)  # one window: one generation
    return float(X[open_[0]]), float(X[open_[-1]])


@pytest.mark.parametrize("insect", [JB, MRB, MFB, SVB], ids=lambda i: i.id)
def test_one_generation_a_year(insect):
    assert insect.generation_dd is None
    assert insect.version == "0.2"


# --- Japanese beetle --------------------------------------------------------------------------------------------------

# Coop and Barker 2024 (USPest `jpb`, version 2): shares of adults trapped, DD50/92 single sine from January 1
USPEST_JB = {0.10: 1100, 0.50: 1540, 0.90: 1985, 0.94: 2110}


def test_japanese_beetle_is_uspests_method():
    assert (JB.dd_method, JB.base_f, JB.upper_f, JB.biofix) == ("sine", 50, 92, "01-01")


def test_japanese_beetle_follows_uspests_trap_shares():
    adults = entered(JB, "Adult beetles")
    for fraction, dd in USPEST_JB.items():
        assert abs(np.interp(dd, X, adults) - fraction) <= 0.012, fraction  # within 1.2 percentage points
    # USPest's "2 %" at 1,000 is set early on purpose (below its data's mean of 1,027); ours comes earlier still
    assert 900 <= dd_at(adults, 0.02) <= 1000
    # its last adults at 2,700: nearly all ours are done by then
    assert np.interp(2700, X, adults) == pytest.approx(1)


def test_japanese_beetle_scouting_window_from_first_beetles_to_the_end_of_main_activity():
    first, last = window(JB)
    assert abs(first - 921) <= 2 and abs(last - 2085) <= 2  # 2 % and 94 %, USPest's 920 "place traps" and 2,110


# --- Mint root borer --------------------------------------------------------------------------------------------------


def test_mint_root_borer_is_uspests_method():
    assert (MRB.dd_method, MRB.base_f, MRB.upper_f, MRB.biofix) == ("sine", 50, None, "04-01")


def test_mint_root_borer_moth_flight_is_uspests():
    moths = entered(MRB, "Moth flight")
    flight = timed(MRB, "Moth flight")
    assert flight.peak == 910  # peak moth catch
    assert abs(dd_at(moths, 0.02) - 430) <= 3  # first moth catch
    assert abs(dd_at(moths, 0.90) - 1350) <= 3  # 90 % moth catch
    # Tollerup et al. 2013: flight lasts about 60 days; 2–99 % here is about 1,170 degree days, 50–60 days in July
    assert 1100 <= dd_at(moths, 0.99) - dd_at(moths, 0.02) <= 1250


def test_mint_root_borer_larvae_hatch_and_overwinter_on_uspests_events():
    hatched, overwintering = entered(MRB, "Larvae in roots"), left(MRB, "Larvae in roots")
    assert abs(dd_at(hatched, 0.5) - 1280) <= 40  # peak egg hatch
    assert abs(dd_at(overwintering, 0.5) - 2150) <= 3  # 50 % in hibernacula
    assert 1650 <= dd_at(overwintering, 0.05) <= 1850  # USPest's 5 % at 1,850
    # the larvae stay until every one has its chamber, not half
    activity = curves(MRB)["activity_larvae_in_roots"]
    assert np.interp(2150, X, activity) > 0.3 and np.interp(2800, X, activity) > 0


def test_mint_root_borer_weights_the_larvae_not_the_moths():
    assert stage(MRB, "Moth flight").weight == 0 and stage(MRB, "Larvae in roots").weight == 1
    first, last = window(MRB)
    assert abs(first - 430) <= 3 and abs(last - 1350) <= 3


# --- Mint flea beetle -------------------------------------------------------------------------------------------------


def test_mint_flea_beetle_is_uspests_method_without_its_upper_threshold():
    assert (MFB.dd_method, MFB.base_f, MFB.upper_f, MFB.biofix) == ("sine", 41, None, "01-01")
    # USPest's 103 °F cap changes nothing until a day's high passes 103 °F
    lo, hi = np.array([60.0, 70.0]), np.array([95.0, 102.9])
    assert np.allclose(degree_days_sine(lo, hi, base=41, upper=None), degree_days_sine(lo, hi, base=41, upper=103))


def test_mint_flea_beetle_stages_begin_at_uspests_events():
    assert abs(dd_at(entered(MFB, "Egg hatch"), 0.02) - 405) <= 15  # eggs hatch, first instar
    assert abs(dd_at(left(MFB, "Larval feeding"), 0.02) - 900) <= 15  # larvae exit rhizomes
    assert abs(dd_at(entered(MFB, "Adult emergence"), 0.02) - 1475) <= 10  # adult emergence begins
    # and the larvae have left before the prepupae and pupae of USPest's table would turn into adults
    assert dd_at(left(MFB, "Larval feeding"), 0.98) < 1475


def test_mint_flea_beetle_weights_feeding_not_hatch_or_emergence():
    weights = {s.label: s.weight for s in MFB.life_stages}
    assert weights == {"Egg hatch": 0, "Larval feeding": 1, "Adult emergence": 0, "Adult feeding": 1}
    first, last = window(MFB)
    assert abs(first - 1479) <= 2 and abs(last - 2001) <= 2


# --- Squash vine borer ------------------------------------------------------------------------------------------------


def test_squash_vine_borer_is_uw_madisons_method():
    assert (SVB.dd_method, SVB.base_f, SVB.upper_f, SVB.biofix) == ("modified", 50, 86, "01-01")


def test_squash_vine_borer_flight_fits_the_guides():
    moths = entered(SVB, "Moth flight and egg laying")
    assert 800 <= dd_at(moths, 0.05) <= 900  # first moths: MSU's 800 emergence, UW–Madison's 900
    assert 1000 <= dd_at(moths, 0.5) <= 1100  # half: UW's egg laying centered on 1,000; SDSU, Ohio State 1,000
    # UW–Madison: egg laying goes on about a week and a half past 1,000 (about 240 degree days in July)
    assert 1200 <= dd_at(moths, 0.75) <= 1280
    assert timed(SVB, "Moth flight and egg laying").end <= 2000  # MSU: complete by 2,000


def test_squash_vine_borer_larvae_from_sdsu():
    larvae = derived(SVB, "Larvae in vines")
    assert 245 <= larvae.lag <= 300 and larvae.duration == 660
    assert stage(SVB, "Moth flight and egg laying").weight == 0 and larvae.weight == 1


def test_squash_vine_borer_protection_window_is_uw_madisons_three_weeks():
    first, last = window(SVB)
    assert abs(first - 824) <= 2 and abs(last - 1242) <= 2
