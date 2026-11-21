"""Common asparagus beetle, corn rootworm and tarnished plant bug (part H, H4 and H5), rebuilt on their sources and
checked against those sources' own numbers."""

import numpy as np
import pytest

from agmodels.insects import common_asparagus_beetle, corn_rootworm, tarnished_plant_bug
from agmodels.phenology import (
    DD_STEP,
    DerivedStage,
    Insect,
    LifeStage,
    PhenologyModel,
    curves,
    dd_grid,
    generation_densities,
)

X = dd_grid()


def shares(insect: Insect) -> list[np.ndarray]:
    """Each generation of the first life stage, cumulative (0 to 1) on the degree-day grid."""
    first = insect.life_stages[0]
    assert isinstance(first, LifeStage)
    return [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=first)]


def dd_at(cumulative: np.ndarray, share: float) -> float:
    return float(np.interp(share, cumulative, X))


def stage(insect: Insect, label: str) -> DerivedStage:
    s = next(s for s in insect.life_stages if s.label == label)
    assert isinstance(s, DerivedStage)
    return s


def peaks(insect: Insect, key: str) -> list[float]:
    a = curves(insect)[f"activity_{key}"]
    k = np.flatnonzero((a[1:-1] > a[:-2]) & (a[1:-1] >= a[2:]) & (a[1:-1] > 0.05)) + 1
    return [float(X[i]) for i in k]


def window_edges(insect: Insect, key: str) -> list[tuple[float, float]]:
    table = curves(insect)[key]
    edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
    return [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def risk_stages(insect: Insect) -> set[str]:
    return {s.label for s in insect.life_stages if s.weight > 0}


# --- Common asparagus beetle ---------------------------------------------------------------------------------------

CAB = common_asparagus_beetle.INSECT


def test_asparagus_beetle_is_uw_madisons_method():
    """XHT1086/XHT1087: the modified average, 50/86 °F, from January 1."""
    assert (CAB.dd_method, CAB.base_f, CAB.upper_f, CAB.biofix) == ("modified", 50, 86, "01-01")


def test_asparagus_beetles_egg_laying_is_xht1087s_150_to_240():
    """XHT1087: asparagus beetle egg laying at 150–240 DD50, the overwintered beetles' 10 and 50 %."""
    spring = shares(CAB)[0]
    assert abs(dd_at(spring, 0.10) - 150) <= 2
    assert abs(dd_at(spring, 0.50) - 240) <= 2


def test_asparagus_beetle_adults_and_larvae_both_count():
    """Adults scar spears and lay eggs on them during harvest; larvae feed on spears and ferns."""
    assert risk_stages(CAB) == {"Adults feeding and laying eggs", "Larvae"}
    larvae = stage(CAB, "Larvae")
    assert larvae.duration == 405 - 105  # VDIFN's span from first hatch to the last larvae, a placeholder
    assert larvae.lag == common_asparagus_beetle.EGG == 100  # about a week at late May's rate


def test_asparagus_beetle_has_three_generations_from_uws_days():
    """Egg (100), larvae (300), pupa (about 120) and a few days before laying (about 80); Taylor 1979: three generations
    in eastern Ontario."""
    assert CAB.generation_dd == 600 and CAB.max_generations == 3
    gens = shares(CAB)
    assert len(gens) == 3
    assert abs((dd_at(gens[1], 0.5) - dd_at(gens[0], 0.5)) - 600) <= 10


def test_asparagus_beetle_scouting_window_covers_each_generations_egg_laying():
    windows = window_edges(CAB, "window_scout_for_beetles_and_eggs")
    assert len(windows) == 3
    first, last = windows[0]
    assert abs(first - 149) <= 2 and abs(last - 360) <= 2


# --- Corn rootworm -------------------------------------------------------------------------------------------------

CRW = corn_rootworm.INSECT
CRW_MODEL = PhenologyModel(insect=CRW, summary="")


def test_corn_rootworm_is_apple_et_al_s_threshold():
    """Apple, Walgenbach and Knee 1971: 52 °F; the method and start aren't stated (single sine from January 1)."""
    assert (CRW.dd_method, CRW.base_f, CRW.upper_f, CRW.biofix) == ("sine", 52, None, "01-01")


def test_corn_rootworm_hatch_against_apple_et_al():
    """First hatch 304.2 degree days (laboratory); median 533 in air on the day buried eggs reached median hatch."""
    hatch = CRW.life_stages[0]
    assert isinstance(hatch, LifeStage) and hatch.weight == 0
    assert abs(hatch.start - 304.2) <= 5
    assert abs(dd_at(shares(CRW)[0], 0.5) - 533) <= 3


def test_corn_rootworm_risk_is_the_larvae_and_beetles_follow_xht1087():
    """Larvae feed for about three weeks (350); half the beetles are out at about 1,075, the day the normals reach
    XHT1087's 1,300 DD50 (1,054 to 1,094 above 52 °F at the three places)."""
    assert risk_stages(CRW) == {"Larvae feeding on roots"}
    larvae, beetles = stage(CRW, "Larvae feeding on roots"), stage(CRW, "Beetles")
    assert (larvae.lag, larvae.duration) == (0, corn_rootworm.LARVAE)
    assert 1054 <= 533 + beetles.lag <= 1094
    assert beetles.lag - larvae.duration == pytest.approx(192)  # the pupa, about 11 days in July


def test_corn_rootworm_has_one_generation():
    assert CRW.generation_dd is None
    out = CRW_MODEL.explore(dd_total=3000)
    assert out["generations_egg_hatch"] == pytest.approx(1, abs=1e-5)


def test_corn_rootworm_root_digging_window_follows_the_larvae():
    (window,) = window_edges(CRW, "window_dig_and_rate_roots_for_larval_injury")
    assert abs(window[0] - 885) <= 3 and abs(window[1] - 1123) <= 3


# --- Tarnished plant bug -------------------------------------------------------------------------------------------

TPB = tarnished_plant_bug.INSECT
# Ugine 2012, Table 5: generation time in days at constant temperatures, °C
UGINE_GENERATION_DAYS = {18: 49.2, 21: 36.2, 25: 28.5, 27: 25.7, 30: 21.0}


def test_tarnished_plant_bug_keeps_uws_setting():
    assert (TPB.dd_method, TPB.base_f, TPB.upper_f, TPB.biofix) == ("sine", 52, None, "01-01")


def test_tarnished_plant_bug_sums_are_ugines_converted():
    """Ugine 2012 (Tables 2 and 5): nymphs 250.0 °C·d above 9.8 °C; first and second instars 62.5 + 50.0; a mean
    generation time of 483 °C·d above 7.9 °C; converted by the June–August ratios of degree days above 52 °F to those
    above 46.2 and 49.6 °F on the normals (scripts/beetle_bug_normals.py)."""
    generation_c = np.mean([days * (t - 7.9) for t, days in UGINE_GENERATION_DAYS.items()])
    assert generation_c == pytest.approx(483, abs=1)
    assert TPB.generation_dd == pytest.approx(generation_c * 1.8 * tarnished_plant_bug.RATIO_46, abs=3)
    assert pytest.approx(250.0 * 1.8 * tarnished_plant_bug.RATIO_49_6, abs=1) == tarnished_plant_bug.NYMPHS
    assert pytest.approx((62.5 + 50.0) * 1.8 * tarnished_plant_bug.RATIO_46, abs=2) == tarnished_plant_bug.YOUNG_NYMPHS
    nymphs, adults = stage(TPB, "Nymphs"), stage(TPB, "Adults")
    assert (nymphs.lag, nymphs.duration) == (0, tarnished_plant_bug.NYMPHS)
    assert adults.lag == tarnished_plant_bug.NYMPHS
    assert risk_stages(TPB) == {"Nymphs", "Adults"}


def test_tarnished_plant_bugs_young_nymphs_peak_at_275():
    """Simko's peak of first- and second-stage nymphs (USPest.org), as UW–Madison's newsletter uses it."""
    hatch = TPB.life_stages[0]
    young = Insect(
        id="young-nymphs",
        name="Young nymphs",
        crops=TPB.crops,
        base_f=52,
        upper_f=None,
        biofix="01-01",
        life_stages=(
            hatch,
            DerivedStage(label="Young nymphs", follows=hatch.label, lag=0, duration=tarnished_plant_bug.YOUNG_NYMPHS),
        ),
        generation_dd=TPB.generation_dd,
    )
    assert abs(peaks(young, "young_nymphs")[0] - 275) <= 2


def test_tarnished_plant_bug_generations_repeat_to_the_seasons_end():
    """UW–Madison's fruit program: four to five generations a year in the Midwest; no cap."""
    assert TPB.max_generations is None
    hatches = peaks(TPB, "egg_hatch")
    assert np.allclose(np.diff(hatches[:4]), 640, atol=15)
