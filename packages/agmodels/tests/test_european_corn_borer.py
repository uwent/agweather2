"""European corn borer (part H): UW–Madison's degree-day table on the modified average from January 1, egg masses and
young larvae timed from the flight, two generations, and the window to treat larvae before they bore in."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_modified
from agmodels.insects.european_corn_borer import INSECT
from agmodels.phenology import DD_STEP, PhenologyModel, curves, dd_grid, generation_densities

MODEL = PhenologyModel(insect=INSECT, summary="")
WINDOW = "window_scout_and_treat_young_larvae_before_they_bore_in"


def _share(cumulative: np.ndarray, p: float) -> float:
    return float(np.interp(p, cumulative, dd_grid()))


def test_degree_days_are_uw_madisons_modified_average_from_january_1():
    assert (INSECT.dd_method, INSECT.base_f, INSECT.upper_f, INSECT.biofix) == ("modified", 50, 86, "01-01")
    # A cool spring day: the minimum raised to 50, so (50 + 70) / 2 − 50 = 10; a hot one: the maximum capped at 86
    np.testing.assert_allclose(
        degree_days_modified(np.array([40.0, 70.0]), np.array([70.0, 95.0]), base=50, upper=86), [10, 28]
    )
    out = MODEL.outputs({"air_temperature_min": np.array([4.4, 21.1]), "air_temperature_max": np.array([21.1, 35.0])})
    np.testing.assert_allclose(out["dd"], [10, 28], atol=0.05)


def test_the_flights_follow_uw_madisons_first_moths_and_peaks():
    """UW–Madison (Delahaut 2012): first spring moths 375, peak 631; first summer moths 1,400, peak 1,733."""
    flights = generation_densities(insect=INSECT, stage=INSECT.life_stages[0])  # type: ignore[arg-type]
    assert len(flights) == 2
    spring, summer = (np.cumsum(d) * DD_STEP for d in flights)
    x = dd_grid()
    assert spring[x < 374].max() == 0 and spring[x == 380][0] > 0
    assert x[np.argmax(flights[0])] == pytest.approx(631, abs=1)
    assert _share(summer, 0.01) == pytest.approx(1400, abs=15)
    assert x[np.argmax(flights[1])] == pytest.approx(1733, abs=10)
    assert _share(summer, 0.99) == pytest.approx(2100, abs=50)  # UW's summer treatments end at 2,100


def test_eggs_hatch_about_100_after_laying_and_larvae_are_the_risk():
    """First eggs 76 after the first moths (UW: 375 and 450), hatch ~100 later; young larvae carry the risk."""
    t = curves(INSECT)
    x = dd_grid()
    first_hatch = x[np.argmax(t["generations_egg_masses"] > 0)]
    assert first_hatch == pytest.approx(374 + 76 + 100, abs=2)
    assert x[np.argmax(t["activity_egg_masses"] > 0)] == pytest.approx(450, abs=2)
    assert x[np.argmax(t["activity_young_larvae"] > 0)] == pytest.approx(first_hatch, abs=2)
    out = MODEL.explore(dd_total=631)
    assert out["risk"] == pytest.approx(out["activity_young_larvae"])
    assert out["activity_adult_flight"] == pytest.approx(1)


def test_the_windows_to_treat_young_larvae_bracket_uw_madisons():
    """10–90 % of each generation's hatch, against UW–Madison's 800–1,000 and 1,550–2,100 (Flandermeyer and Bick)."""
    x = dd_grid()
    open_ = curves(INSECT)[WINDOW] > 0
    edges = np.flatnonzero(np.diff(np.r_[0, open_.astype(int), 0]) != 0)
    windows = [(x[a], x[b - 1]) for a, b in zip(edges[::2], edges[1::2], strict=True)]
    assert len(windows) == 2
    (a1, b1), (a2, b2) = windows
    assert a1 == pytest.approx(671, abs=3) and b1 == pytest.approx(986, abs=3)
    assert a2 == pytest.approx(1713, abs=3) and b2 == pytest.approx(2142, abs=3)
    assert a1 < 800 < b1 <= 1000 and a2 < 2100 < b2


def test_two_generations_and_no_third():
    out = MODEL.explore(dd_total=3500)
    assert out["generations_adult_flight"] == pytest.approx(2, abs=1e-3)
    assert out["risk"] < 1e-3 and out[WINDOW] == 0


def test_one_flight_where_the_normal_season_is_short():
    """The univoltine north (part H, round 2): below 1,500 normal degree days (modified 50/86 °F) from January 1
    through August 1, one flight whose 10, 50 and 90 % bracket Wausau's traps' 1,112, 1,402 and 1,715, with the egg
    masses, young larvae and window timed from it, and one generation."""
    from agmodels.phenology import form_insect

    f = INSECT.place_form
    assert f is not None and f.below == 1500 and f.max_generations is None and f.generation_dd is None
    assert (f.normal.variable, f.normal.through, f.normal.period) == ("dd_modified_50_86", "08-01", "last30")
    one = form_insect(INSECT)
    flight = curves(one)["generations_adult_flight"]
    assert flight.max() == pytest.approx(1)  # one generation
    tenth, half, ninetieth = (_share(flight, p) for p in (0.1, 0.5, 0.9))
    assert 1112 < tenth < 1200 and abs(half - 1402) < 5 and 1600 < ninetieth < 1715
    open_ = dd_grid()[curves(one)[WINDOW] > 0]
    assert (open_[0], open_[-1]) == (1323, 1828)
    # Wausau (1,441) and Antigo (1,292) one flight, Hancock (1,571) and Arlington (1,684) two
    total = np.array([631.0, 1400.0])
    base = {"dd_total": total, "dd": np.zeros(2), MODEL.FREEZE: np.ones(2)}
    for normal, flights in ((1292.0, 1), (1441.0, 1), (1571.0, 2), (1684.0, 2)):
        out = MODEL.finish(base | {f.normal.key: np.array(normal)})
        assert out["one_flight"][0] == (flights == 1)
        spring = out["activity_adult_flight"][0]
        assert (spring == 0) if flights == 1 else (spring == pytest.approx(1))
