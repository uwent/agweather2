"""Black cutworm (part H): Kaster and Showers 1984's outdoor development times, with Luckmann et al. 1976's egg, from
a significant moth capture, against Purdue's and Iowa State's stage table, and the default capture date."""

import numpy as np
import pytest

from agmodels.insects.black_cutworm import FOURTH_INSTAR_F, HATCH_F, INSECT, PUPATION_F
from agmodels.phenology import PhenologyModel, curves, dd_grid, generation_densities

MODEL = PhenologyModel(insect=INSECT, summary="")
X = dd_grid()


def first(table: np.ndarray, at_least: float) -> float:
    return float(X[np.argmax(table >= at_least)])


def last(table: np.ndarray, at_least: float) -> float:
    return float(X[len(table) - 1 - np.argmax(table[::-1] >= at_least)])


def test_development_times_are_kaster_and_showers_spring_times_after_luckmanns_egg():
    """Kaster and Showers 1984, Table 1, spring: median °C·d above 10.4 °C from hatch to the fourth instar 105.7 and to
    pupation 288.3; the egg from Luckmann et al. 1976's Table 2, hatch 52 °C·d after oviposition."""
    assert round(52 * 1.8) == HATCH_F
    assert round((52 + 105.7) * 1.8) == FOURTH_INSTAR_F == 284
    assert round((52 + 288.3) * 1.8) == PUPATION_F == 613
    # Luckmann's constant-temperature times (third molt 170, pupation 405 °C·d from oviposition) ran behind
    assert FOURTH_INSTAR_F < 170 * 1.8 and PUPATION_F < 405 * 1.8


def test_stages_against_purdues_and_iowa_states_table():
    """Purdue (Krupke and Obermeyer 2023) and Iowa State, after a significant capture: hatch at 90, leaf feeding
    91–311, cutting from the fourth instar at 312, pupae 641–989."""
    c = curves(INSECT)
    # the first caterpillars hatch where the table says, and the first reach cutting size a day or so before its 312
    assert abs(first(c["activity_leaf_feeding_caterpillars"], 0.01) - 90) <= 10
    assert first(c["activity_cutting_caterpillars"], 0.01) == pytest.approx(289, abs=3)
    # half the eggs are laid by 82 after the capture, so half the caterpillars can cut by about 366
    assert first(c["generations_egg_laying"], 0.5) == pytest.approx(82, abs=2)
    assert first(c["activity_cutting_caterpillars"], 0.5) == pytest.approx(366, abs=5)
    # nearly every caterpillar is in the cutting stages from about 575; each pupates 613 after its egg, near the
    # table's 641, and with eggs laid over weeks half have pupated by about 695 and 90 % by 788, inside the table's
    # pupal span (641–989)
    assert first(c["activity_cutting_caterpillars"], 0.999) == pytest.approx(575, abs=5)
    assert first(c["generations_cutting_caterpillars"], 0.5) == pytest.approx(695, abs=5)
    assert first(c["generations_cutting_caterpillars"], 0.9) == pytest.approx(788, abs=5)
    assert 641 < first(c["generations_cutting_caterpillars"], 0.5) < 989
    assert last(c["activity_cutting_caterpillars"], 0.01) < 900


def test_one_generation_and_cutting_is_the_risk():
    for stage in INSECT.life_stages[:1]:
        assert len(generation_densities(insect=INSECT, stage=stage)) == 1  # type: ignore[arg-type]
    assert [s.weight for s in INSECT.life_stages] == [0, 0, 1]
    assert MODEL.explore(dd_total=200)["risk"] == 0
    assert MODEL.explore(dd_total=600)["risk"] == pytest.approx(1, abs=1e-3)
    assert MODEL.explore(dd_total=1200)["risk"] == pytest.approx(0, abs=1e-6)


def test_default_capture_is_may_first():
    """The median first week with 9 or more moths in DATCP's pheromone traps, 2021–2023 and 2026, is day 120–121."""
    biofix = MODEL.SPEC.biofix
    assert biofix is not None and biofix.default == "05-01"
    assert "May 1" in biofix.label


def test_the_cutting_window_opens_with_the_first_cutting_caterpillars():
    """Part H, round 2: a 'present' window, from 1 % in the cutting stages (289; the table's 312) until 90 % have
    pupated (787)."""
    (window,) = INSECT.action_windows
    assert window.when == "present" and window.stage == "Cutting caterpillars" and window.between == (0.01, 0.9)
    table = curves(INSECT)["window_scout_and_treat_while_caterpillars_can_cut_plants"]
    assert (first(table, 1), last(table, 1)) == (289, 787)
    assert np.all(table[(X >= 289) & (X <= 787)] == 1)  # one period
