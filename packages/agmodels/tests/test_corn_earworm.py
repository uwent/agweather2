"""Corn earworm (part H): Hartstack et al. 1976's development on single sine 55/92 °F from egg laying (USPest.org's
events), the egg-laying spread from DATCP's pheromone traps, and one generation."""

import numpy as np
import pytest

from agmodels.insects.corn_earworm import INSECT
from agmodels.phenology import DD_STEP, PhenologyModel, curves, dd_grid, generation_densities

MODEL = PhenologyModel(insect=INSECT, summary="")


def test_degree_days_are_uspests_single_sine_55_92_from_the_biofix():
    assert (INSECT.dd_method, INSECT.base_f, INSECT.upper_f) == ("sine", 55, 92)
    assert INSECT.biofix == "08-15"


def test_larvae_are_in_the_ears_from_73_to_437_after_each_egg():
    """USPest.org: egg hatch begins 73 degree days after egg laying; larvae exit the ears to pupate at 437."""
    t = curves(INSECT)
    x = dd_grid()
    assert x[np.argmax(t["activity_larvae_in_ears"] > 0)] == pytest.approx(73, abs=1)
    assert x[np.argmax(t["generations_larvae_in_ears"] > 0)] == pytest.approx(437, abs=1)
    out = MODEL.explore(dd_total=300)
    assert out["risk"] == pytest.approx(out["activity_larvae_in_ears"]) and out["risk"] > 0.75


def test_egg_laying_follows_the_main_flight_in_wisconsins_traps():
    """DATCP's pheromone catches after the main flight's first week of 35 or more moths, 2021–2026: 25, 50 and 75 % at
    81, 141 and 266 degree days from that week's start (scripts/check_corn_earworm.py)."""
    (density,) = generation_densities(insect=INSECT, stage=INSECT.life_stages[0])  # type: ignore[arg-type]
    done = np.cumsum(density) * DD_STEP
    for p, observed in ((0.25, 81), (0.5, 141), (0.75, 266)):
        assert float(np.interp(p, done, dd_grid())) == pytest.approx(observed, abs=15)


def test_one_generation():
    """Adults lay eggs 873 after the eggs they came from, more than Wisconsin reaches after mid-August."""
    assert len(generation_densities(insect=INSECT, stage=INSECT.life_stages[0])) == 1  # type: ignore[arg-type]
    assert MODEL.explore(dd_total=3000)["generations_larvae_in_ears"] == pytest.approx(1, abs=1e-3)
