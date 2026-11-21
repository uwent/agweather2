"""Black cutworm (part H): Luckmann et al. 1976's development times from a significant moth capture, against
Purdue's and Iowa State's stage table, and the default capture date."""

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


def test_development_times_are_luckmanns_table_2():
    """Median °C·d above 10.4 °C from oviposition: hatch 52, third molt 170, pupation 405 (Luckmann et al. 1976)."""
    assert round(52 * 1.8) == HATCH_F
    assert round(170 * 1.8) == FOURTH_INSTAR_F
    assert round(405 * 1.8) == PUPATION_F
    # their larval period, 353 °C·d (635 °F·d), is pupation less hatch
    assert pytest.approx(353 * 1.8, abs=2) == PUPATION_F - HATCH_F


def test_stages_against_purdues_and_iowa_states_table():
    """Purdue (Krupke and Obermeyer 2023) and Iowa State, after a significant capture: hatch at 90, leaf feeding
    91–311, cutting from the fourth instar at 312, pupae from 641."""
    c = curves(INSECT)
    # the first caterpillars hatch, and the first reach cutting size, where the table says
    assert abs(first(c["activity_leaf_feeding_caterpillars"], 0.01) - 90) <= 10
    assert abs(first(c["activity_cutting_caterpillars"], 0.01) - 312) <= 5
    # half the eggs are laid by 82 after the capture, so half the caterpillars can cut by about 390
    assert first(c["generations_egg_laying"], 0.5) == pytest.approx(82, abs=2)
    assert first(c["activity_cutting_caterpillars"], 0.5) == pytest.approx(388, abs=5)
    # nearly every caterpillar is in the cutting stages from about 600, while the table has them pupating from 641:
    # Luckmann's pupation (729 after the egg) is later than the table's, and eggs are laid over weeks, not on the
    # biofix day, so half have pupated only by about 810
    assert first(c["activity_cutting_caterpillars"], 0.999) == pytest.approx(597, abs=5)
    assert first(c["generations_cutting_caterpillars"], 0.5) == pytest.approx(811, abs=5)
    assert first(c["generations_cutting_caterpillars"], 0.9) == pytest.approx(904, abs=5)
    assert last(c["activity_cutting_caterpillars"], 0.01) < 1000


def test_one_generation_and_cutting_is_the_risk():
    for stage in INSECT.life_stages[:1]:
        assert len(generation_densities(insect=INSECT, stage=stage)) == 1  # type: ignore[arg-type]
    assert [s.weight for s in INSECT.life_stages] == [0, 0, 1]
    assert MODEL.explore(dd_total=200)["risk"] == 0
    assert MODEL.explore(dd_total=700)["risk"] == pytest.approx(1, abs=1e-3)
    assert MODEL.explore(dd_total=1200)["risk"] == pytest.approx(0, abs=1e-6)


def test_default_capture_is_may_first():
    """The median first week with 9 or more moths in DATCP's pheromone traps, 2021–2023 and 2026, is day 120–121."""
    biofix = MODEL.SPEC.biofix
    assert biofix is not None and biofix.default == "05-01"
    assert "May 1" in biofix.label
