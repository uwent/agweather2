"""Variegated cutworm (part H): Simonet et al. 1981's flights and development times."""

import numpy as np
import pytest

from agmodels.insects.variegated_cutworm import INSECT
from agmodels.phenology import DerivedStage, PhenologyModel, curves, dd_grid, generation_densities

MODEL = PhenologyModel(insect=INSECT, summary="")
X = dd_grid()


def test_thresholds_are_simonets():
    """7.2 °C (45 °F), no upper threshold, from January 1 (Simonet et al. 1981)."""
    assert INSECT.base_f == pytest.approx(7.2 * 1.8 + 32, abs=0.1)
    assert INSECT.upper_f is None
    assert INSECT.biofix == "01-01"


def test_flights_peak_where_wooster_s_light_traps_did():
    """Peaks at about 500 and 1,200 °C·d from January 1 (900 and 2,160 °F·d), 15 years of catches at Wooster."""
    flight = curves(INSECT)["activity_adult_flight"]
    first = X[np.argmax(flight[:1600])]
    second = X[1600 + np.argmax(flight[1600:3200])]
    assert first == pytest.approx(500 * 1.8, abs=5)
    assert second == pytest.approx(1200 * 1.8, abs=10)
    # the time between peaks, 733 ± 67 °C·d (range 625–925) in Wooster's catches
    assert 625 * 1.8 <= second - first <= 925 * 1.8


def test_two_flights_only():
    assert len(generation_densities(insect=INSECT, stage=INSECT.life_stages[0])) == 2  # type: ignore[arg-type]
    assert MODEL.explore(dd_total=4500)["generations_adult_flight"] == pytest.approx(2, abs=1e-3)


def test_larvae_follow_simonets_development_times():
    """Pre-oviposition 127.5 °C·d above 3.5 °C, egg 89.2 above 5.6, larva 386.6 above 6.2 (Simonet et al. 1981),
    carried to the 7.2 °C base at a 20 °C day."""
    larvae = INSECT.life_stages[1]
    assert isinstance(larvae, DerivedStage)

    def at_base(dd_c: float, base_c: float) -> float:
        return dd_c * (20 - 7.2) / (20 - base_c) * 1.8

    assert larvae.lag == pytest.approx(at_base(127.5, 3.5) + at_base(89.2, 5.6), abs=5)
    assert larvae.duration == pytest.approx(at_base(386.6, 6.2), abs=5)
    # Enviroweather's events put first hatch 302 after first flight; ours, 320 after each moth emerges
    assert abs(larvae.lag - 302) < 25


def test_the_scouting_window_opens_at_each_flights_peak():
    window = curves(INSECT)["window_scout_for_eggs_and_young_caterpillars"]
    opens = X[np.flatnonzero(np.diff(np.r_[0.0, window]) > 0)]
    assert len(opens) == 2
    assert opens[0] == pytest.approx(900, abs=20)
    assert opens[1] == pytest.approx(2160, abs=20)
