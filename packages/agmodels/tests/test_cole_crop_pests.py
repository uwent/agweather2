"""The cole-crop caterpillars and flea beetle (part H, H3): imported cabbageworm, cabbage looper and crucifer flea beetle
rebuilt on their sources, checked against those sources' own numbers."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_modified
from agmodels.insects import cabbage_looper, crucifer_flea_beetle, imported_cabbageworm
from agmodels.phenology import DD_STEP, DerivedStage, LifeStage, PhenologyModel, curves, dd_grid, generation_densities

X = dd_grid()


def shares(insect) -> list[np.ndarray]:
    """Each generation of the first life stage, cumulative (0 to 1) on the degree-day grid."""
    first = insect.life_stages[0]
    assert isinstance(first, LifeStage)
    return [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=first)]


def dd_at(cumulative: np.ndarray, share: float) -> float:
    return float(np.interp(share, cumulative, X))


def stage(insect, label: str) -> DerivedStage:
    s = next(s for s in insect.life_stages if s.label == label)
    assert isinstance(s, DerivedStage)
    return s


def window_edges(insect, key: str) -> list[tuple[float, float]]:
    table = curves(insect)[key]
    edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
    return [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def risk_stages(insect) -> set[str]:
    return {s.label for s in insect.life_stages if s.weight > 0}


# --- Imported cabbageworm ------------------------------------------------------------------------------------------

ICW = imported_cabbageworm.INSECT


def test_imported_cabbageworm_is_uw_madisons_method():
    """XHT1086/XHT1087: the modified average, the minimum raised to 50 °F and the maximum capped at 86 °F, from
    January 1."""
    assert (ICW.dd_method, ICW.base_f, ICW.upper_f, ICW.biofix) == ("modified", 50, 86, "01-01")
    assert degree_days_modified(np.array([40.0]), np.array([90.0]), base=50, upper=86)[0] == 18


def test_imported_cabbageworms_spring_flight_is_xht1087s_150_to_240():
    """XHT1087: adult butterflies at 150–240 DD50, the spring flight's 10 and 50 %."""
    spring = shares(ICW)[0]
    assert abs(dd_at(spring, 0.10) - 150) <= 2
    assert abs(dd_at(spring, 0.50) - 240) <= 2


def test_imported_cabbageworm_larvae_are_tatchells_349():
    """Tatchell 1981 (UC IPM): larvae 193.9 °C·d above 9.4 °C, 349 °F·d."""
    larvae = stage(ICW, "Larval feeding")
    assert larvae.duration == pytest.approx(193.9 * 1.8, abs=0.5)
    assert larvae.lag == stage(ICW, "Eggs").lag + stage(ICW, "Eggs").duration
    assert risk_stages(ICW) == {"Larval feeding"}


def test_imported_cabbageworm_generations_match_its_development_and_wisconsins_records():
    """Development times sum to 739 (the shorter readings of UW's days) to about 820; Wisconsin's iNaturalist records
    put the flights' middles at 234, 1,066 and 1,927 on the model's degree days (scripts/check_imported_cabbageworm.py)."""
    s = stage(ICW, "Eggs")
    assert ICW.generation_dd is not None
    assert (
        739
        <= s.lag + s.duration + stage(ICW, "Larval feeding").duration + imported_cabbageworm.PUPA
        <= ICW.generation_dd
    )
    flights = shares(ICW)
    for g, middle in enumerate((234, 1066, 1927)):
        assert abs(dd_at(flights[g], 0.5) - middle) <= 20, g
    assert ICW.max_generations is None


def test_imported_cabbageworm_scouting_window_follows_egg_hatch():
    windows = window_edges(ICW, "window_scout_for_eggs_and_young_caterpillars")
    first, last = windows[0]
    assert abs(first - 359) <= 3 and abs(last - 570) <= 3
    assert len([w for w in windows if w[0] < 2800]) == 4


# --- Cabbage looper ------------------------------------------------------------------------------------------------

CL = cabbage_looper.INSECT
# USPest.org's cabbage looper events (single sine 50/90 °F from the first catch)
USPEST = {"first eggs": 120, "first hatch": 218, "first fourth instar": 428, "first pupae": 638, "first adults": 912}


def test_cabbage_looper_is_uspests_method_from_a_first_catch():
    assert (CL.dd_method, CL.base_f, CL.upper_f) == ("sine", 50, 90)
    assert CL.biofix == "07-15"
    assert CL.biofix_label is not None and "pheromone trap" in CL.biofix_label and "July 15" in CL.biofix_label


def test_cabbage_looper_stages_follow_uspests_events():
    laying = CL.life_stages[0]
    assert isinstance(laying, LifeStage) and laying.start == USPEST["first eggs"]
    eggs, larvae = stage(CL, "Eggs"), stage(CL, "Larval feeding")
    assert USPEST["first eggs"] + eggs.duration == USPEST["first hatch"]
    assert USPEST["first eggs"] + larvae.lag + larvae.duration == USPEST["first pupae"]
    assert risk_stages(CL) == {"Larval feeding"}


def test_cabbage_looper_generation_is_toba_egg_to_adult_plus_uspests_preoviposition():
    """Toba et al. 1973: 791.5 °F·d (base 50) from egg to adult, averaged over Table 1; USPest's first adults at 912,
    120 after the first catch to the first eggs."""
    assert CL.generation_dd == USPEST["first adults"]
    assert abs((USPEST["first adults"] - USPEST["first eggs"]) - 791.5) <= 1
    assert CL.max_generations is None  # to the season's end, so the damaging late-summer generation is covered
    gens = shares(CL)
    assert abs((dd_at(gens[1], 0.5) - dd_at(gens[0], 0.5)) - 912) <= 10


def test_cabbage_looper_scouting_window_follows_egg_hatch():
    windows = window_edges(CL, "window_scout_for_small_caterpillars")
    first, last = windows[0]
    assert abs(first - 254) <= 3 and abs(last - 408) <= 3
    assert abs(windows[1][0] - 1134) <= 5


# --- Crucifer flea beetle ------------------------------------------------------------------------------------------

CFB = crucifer_flea_beetle.INSECT


def test_crucifer_flea_beetle_is_uw_madisons_method():
    assert (CFB.dd_method, CFB.base_f, CFB.upper_f, CFB.biofix) == ("modified", 50, 86, "01-01")


def test_crucifer_flea_beetles_spring_adults_are_xht1087s_150_to_200():
    """XHT1087: flea beetles at 150–200 DD50: the overwintered adults' 10 % and peak."""
    adults = CFB.life_stages[0]
    assert isinstance(adults, LifeStage) and adults.peak == 200 and adults.weight == 1
    assert abs(dd_at(shares(CFB)[0], 0.10) - 150) <= 7


def test_crucifer_flea_beetles_new_adults_follow_kinoshitas_development():
    """Kinoshita et al. 1979: 820.6 °F·d above 51.8 °F from egg to adult, about 911 on the model's degree days in
    summer (× 1.10–1.14, scripts/check_crucifer_flea_beetle.py); the summer adults come that long after the middle of
    the overwintered beetles' egg laying."""
    assert pytest.approx(820.6 * 1.11, abs=1) == crucifer_flea_beetle.EGG_TO_ADULT
    laying = stage(CFB, "Egg laying")
    assert abs(CFB.generation_dd - (laying.lag + laying.duration / 2 + crucifer_flea_beetle.EGG_TO_ADULT)) <= 15  # type: ignore[operator]
    gens = shares(CFB)
    assert len(gens) == 2  # the overwintered adults and the new summer adults
    assert abs((dd_at(gens[1], 0.5) - dd_at(gens[0], 0.5)) - 1350) <= 10


def test_crucifer_flea_beetle_weighs_spring_adults_as_the_damage():
    assert risk_stages(CFB) == {"Adults feeding"}
    model = PhenologyModel(insect=CFB, summary="")
    assert model.explore(dd_total=200)["activity_adults_feeding"] == pytest.approx(1, abs=0.02)


def test_crucifer_flea_beetle_scouting_window_covers_the_spring_adults():
    windows = window_edges(CFB, "window_scout_new_plantings_every_one_to_two_days")
    assert len(windows) == 2
    first, last = windows[0]
    assert abs(first - 129) <= 3 and abs(last - 410) <= 3


@pytest.mark.parametrize("insect", [imported_cabbageworm.INSECT, cabbage_looper.INSECT], ids=lambda i: i.id)
def test_the_second_generation_weighs_most(insect):
    """UW–Madison: the second generation of caterpillars does the most damage (part H, round 2): weights 0.5, 1, 0.5."""
    from agmodels.phenology import risk_curve

    assert insect.generation_weights == (0.5, 1.0, 0.5)
    unweighted = risk_curve(type(insect)(**{**insect.__dict__, "generation_weights": ()}))
    weighted = risk_curve(insect)
    gen = insect.generation_dd
    first_gen = gen * 0.6 > X  # the first generation's caterpillars, before the second's hatch
    np.testing.assert_allclose(weighted[first_gen], unweighted[first_gen] / 2)
    assert weighted.max() == pytest.approx(weighted[(gen < X) & (2 * gen > X)].max())  # the peak is the second's
