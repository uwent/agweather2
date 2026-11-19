"""Spotted wing drosophila (0.2): the refit of Kamiyama et al. 2020's trap counts read as a fitted stage (D36),
against the fit's own critical points (`tmp/R/kamiyama_2020_drosophila/swd_critical_points.csv`) and VDIFN's window
it replaces."""

import numpy as np
import pytest

from agmodels.insects.spotted_wing_drosophila import INSECT
from agmodels.phenology import FittedStage, curves, dd_grid
from agmodels.registry import all_models

STAGE = next(s for s in INSECT.life_stages if isinstance(s, FittedStage))


def crossing(activity: np.ndarray, x: np.ndarray, level: float, rising: bool) -> float:
    above = activity >= level
    k = np.flatnonzero(above)[0] if rising else np.flatnonzero(above)[-1]
    return float(x[k])


def test_the_curve_keeps_the_fits_critical_points():
    x, activity = dd_grid(), curves(INSECT)["activity_adult_activity"]
    assert float(x[np.argmax(activity)]) == pytest.approx(2334, abs=10)
    for level, rising, expected in [(0.5, True, 2094), (0.9, True, 2251), (0.9, False, 2423), (0.5, False, 2948)]:
        assert crossing(activity, x, level, rising) == pytest.approx(expected, abs=10)


def test_zero_before_the_data_and_held_after():
    m = all_models()["spotted-wing-drosophila"]
    assert m.explore(dd_total=170)["risk"] == 0
    assert m.explore(dd_total=3050)["risk"] == m.explore(dd_total=4000)["risk"] == pytest.approx(0.32, abs=0.01)


def test_vdifns_window_put_the_peak_after_the_flies():
    """VDIFN's (1276, 3180, 4000) took the paper's degree days (base 39 °F, modified average) as 45/86 °F single
    sine; on the refit, activity at VDIFN's start is about an eighth of the peak and VDIFN's peak is past the data,
    where activity is held at about a third."""
    m = all_models()["spotted-wing-drosophila"]
    assert 0.1 < m.explore(dd_total=1276)["risk"] < 0.15
    assert m.explore(dd_total=3180)["risk"] < 0.35
