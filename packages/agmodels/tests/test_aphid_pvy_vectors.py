"""Aphid PVY vectors (0.2): the refitted suction trap curve read as a fitted stage (D36), against the fit's own
critical points (`tmp/R/pvy-model/pvy_critical_points_v2.csv`) and VDIFN's window it replaces."""

import numpy as np
import pytest

from agmodels.insects.aphid_pvy_vectors import INSECT
from agmodels.phenology import FittedStage, curves, dd_grid
from agmodels.registry import all_models

STAGE = next(s for s in INSECT.life_stages if isinstance(s, FittedStage))


def crossing(activity: np.ndarray, x: np.ndarray, level: float, rising: bool) -> float:
    above = activity >= level
    k = np.flatnonzero(above)[0] if rising else np.flatnonzero(above)[-1]
    return float(x[k])


def test_the_curve_keeps_the_fits_critical_points():
    x, activity = dd_grid(), curves(INSECT)["activity_pvy_vector_pressure"]
    assert float(x[np.argmax(activity)]) == pytest.approx(3582, abs=10)
    for level, rising, expected in [(0.5, True, 2236), (0.9, True, 2980), (0.9, False, 3994), (0.5, False, 4985)]:
        assert crossing(activity, x, level, rising) == pytest.approx(expected, abs=10)


def test_zero_before_the_data_and_held_after():
    m = all_models()["aphid-pvy-vectors"]
    assert m.explore(dd_total=280)["risk"] == 0
    assert m.explore(dd_total=290)["risk"] == pytest.approx(np.exp(STAGE.log_count[0] - max(STAGE.log_count)), abs=1e-3)
    assert m.explore(dd_total=5490)["risk"] == m.explore(dd_total=7000)["risk"] > 0


def test_vdifns_window_ended_before_the_curves_peak():
    """VDIFN's (1838, 2515, 3228) put its peak at the old fit's crossing of the sample mean; on the refit, risk at
    VDIFN's peak is about half the curve's and still rising, and VDIFN's window had closed before the peak."""
    m = all_models()["aphid-pvy-vectors"]
    assert 0.5 < m.explore(dd_total=2515)["risk"] < 0.7
    assert m.explore(dd_total=3228)["risk"] < m.explore(dd_total=3582)["risk"]
