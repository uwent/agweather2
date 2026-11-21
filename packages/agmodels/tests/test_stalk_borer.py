"""Stalk borer (part H): caterpillars moving into corn (Lasack and Pedigo 1986; Iowa State; A3646), on Levine
1983's degree days."""

import numpy as np
import pytest

from agmodels.insects.stalk_borer import INSECT
from agmodels.phenology import LifeStage, PhenologyModel, curves, dd_grid

MODEL = PhenologyModel(insect=INSECT, summary="")
X = dd_grid()
MOVED = "generations_caterpillars_moving_into_corn"


def moved(fraction: float) -> float:
    return float(X[np.argmax(curves(INSECT)[MOVED] >= fraction)])


def test_degree_days_are_levines():
    """5.1 °C (41.2 °F) as 41 °F, Allen's sine, no upper threshold, from January 1."""
    assert (INSECT.base_f, INSECT.upper_f, INSECT.biofix, INSECT.dd_method) == (41, None, "01-01", "sine")


def test_movement_against_its_sources():
    """Lasack and Pedigo 1986 (via Rice and Davis 2010): first caught at about 600 °C·d (1,080–1,110 °F·d), half at
    900 (1,620–1,650), little after 1,100 (1,980). Iowa State: 10 % at 1,400, half at 1,700."""
    moving = INSECT.life_stages[0]
    assert isinstance(moving, LifeStage) and moving.start == pytest.approx(600 * 1.8, abs=30)
    assert moved(0.1) == pytest.approx(1400, abs=15)
    assert 900 * 1.8 <= moved(0.5) <= 1700
    assert moved(0.99) == pytest.approx(1100 * 1.8, abs=50)


def test_one_generation():
    assert INSECT.generation_dd is None
    assert MODEL.explore(dd_total=3000)[MOVED] == pytest.approx(1, abs=1e-6)


def test_the_window_runs_from_scouting_to_the_end_of_spraying():
    """A3646 and Iowa State: scout from 1,300–1,400; spray, if needed, between 1,400 and 1,700."""
    window = curves(INSECT)["window_scout_corn_borders_and_treat_if_needed"]
    days = X[window > 0]
    assert days[0] == pytest.approx(1300, abs=15)
    assert days[-1] == pytest.approx(1700, abs=10)
    assert np.all(np.diff(days) == 1)
