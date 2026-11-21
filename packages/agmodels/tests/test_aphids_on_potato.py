"""Green peach aphid and potato aphid (0.1): the suction trap and scouting curves read as fitted stages (D36) on both
clocks (D101), against the fits' own events (`tmp/R/cpb/cv/out/aphids/aphid_events.csv`)."""

import numpy as np
import pytest

from agmodels.phenology import FittedStage, calendar_curves, curves, dd_grid
from agmodels.registry import all_models

DAYS = np.arange(1.0, 367.0)


def first_at(activity: np.ndarray, x: np.ndarray, level: float) -> float:
    return float(x[np.argmax(activity >= level)])


def last_at(activity: np.ndarray, x: np.ndarray, level: float) -> float:
    """The last point at or above `level` after the peak (where the curve falls through it)."""
    peak = int(np.argmax(activity))
    below = np.flatnonzero(activity[peak:] < level)
    return float(x[peak + below[0] - 1])


def _tables(model_id: str) -> tuple[np.ndarray, np.ndarray]:
    insect = all_models()[model_id].insect  # type: ignore[attr-defined]
    key = next(s.key for s in insect.life_stages if isinstance(s, FittedStage))
    return curves(insect)[f"activity_{key}"], calendar_curves(insect)[f"activity_{key}"]


def test_green_peach_aphid_keeps_the_traps_events():
    by_dd, by_day = _tables("green-peach-aphid")
    x = dd_grid()
    assert float(x[np.argmax(by_dd)]) == pytest.approx(3410, abs=10)
    assert first_at(by_dd, x, 0.1) == pytest.approx(2380, abs=10)
    assert first_at(by_dd, x, 0.5) == pytest.approx(2900, abs=10)
    assert last_at(by_dd, x, 0.5) == pytest.approx(3940, abs=10)
    assert float(DAYS[np.argmax(by_day)]) == 244  # September 1
    assert first_at(by_day, DAYS, 0.1) == 220  # August 8
    assert first_at(by_day, DAYS, 0.5) == 233  # August 21
    assert last_at(by_day, DAYS, 0.5) == pytest.approx(256, abs=1)  # September 13


def test_potato_aphid_keeps_the_scouting_events_and_holds_at_the_end_of_scouting():
    by_dd, by_day = _tables("potato-aphid")
    x = dd_grid()
    assert float(x[np.argmax(by_dd)]) == pytest.approx(3760, abs=10)
    assert first_at(by_dd, x, 0.1) == pytest.approx(2520, abs=10)
    assert first_at(by_dd, x, 0.5) == pytest.approx(3360, abs=10)
    assert first_at(by_day, DAYS, 0.1) == 213  # August 1
    assert first_at(by_day, DAYS, 0.5) == 242  # August 30
    assert float(DAYS[np.argmax(by_day)]) == 257  # the last day scouted: still rising
    assert by_day[300] == by_day[256] == 1


def test_default_clocks_and_training_areas():
    gpa, pa = (all_models()[k].SPEC for k in ("green-peach-aphid", "potato-aphid"))
    assert gpa.options[0].name == "clock" and gpa.options[0].default == "calendar"
    assert pa.options[0].default == "degree_days"
    assert gpa.trained is not None and gpa.trained.contains(state="WI", fips=None)
    assert pa.trained is not None and not pa.trained.contains(state="WI", fips="55085")  # Oneida County
    assert gpa.changelog[0].date == "2026-11-21"  # a new model's own 0.1, not a port's
