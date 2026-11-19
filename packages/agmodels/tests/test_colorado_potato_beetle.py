"""Colorado potato beetle (0.2): the scouting fits read as fitted stages (D36), against the fits' own critical points
(Bradford and Groves, unpublished: `tmp/cpb/CPB GAM fit - all.png`) and the Crop Risk Tool on the same weather."""

import numpy as np
import pytest

from agmodels.insects.colorado_potato_beetle import END_OF_DATA_DD, INSECT
from agmodels.phenology import FittedStage, curves, dd_grid, evaluate
from agmodels.registry import all_models

STAGES = {s.key: s for s in INSECT.life_stages if isinstance(s, FittedStage)}


def critical_points(stage: FittedStage) -> dict[str, list[float]]:
    """Where the fit crosses zero upward, and its local maxima and minima (as the analysis found them)."""
    x, y = np.array(stage.dd), np.array(stage.log_count)
    up = [float(x[k]) for k in range(1, len(y)) if y[k - 1] < 0 <= y[k]]
    peaks = [float(x[k]) for k in range(1, len(y) - 1) if y[k - 1] < y[k] >= y[k + 1]]
    troughs = [float(x[k]) for k in range(1, len(y) - 1) if y[k - 1] > y[k] <= y[k + 1]]
    return {"up": up, "peaks": peaks, "troughs": troughs}


# The figure's labels (degree days 52/86 °F from January 1); the predictions are every 10, so within 10
@pytest.mark.parametrize(
    ("key", "kind", "expected"),
    [
        ("adults", "up", [210]),  # colonization
        ("adults", "peaks", [588, 1477, 1983]),  # first and second generation peaks, the partial third
        ("adults", "troughs", [957, 1880]),  # between generations; the second unlabelled, before the partial third
        ("larvae", "troughs", [374]),  # egg hatch (the curve's low point before it rises)
        ("adults_and_larvae", "up", [220]),  # refitted to each date's sum (2026-11-18)
        ("adults_and_larvae", "peaks", [811, 1354]),
        ("adults_and_larvae", "troughs", [1038]),
        ("egg_masses", "up", [239]),  # first eggs
    ],
)
def test_the_fits_critical_points_are_the_analysis_own(key, kind, expected):
    np.testing.assert_allclose(critical_points(STAGES[key])[kind], expected, atol=10)


def test_larval_peak_and_the_egg_peak_on_the_new_count_basis():
    # Larvae peak at 795 in the figure; egg masses, refitted per 10 plants (the figure: per plant, peak 565), peak at 580
    assert critical_points(STAGES["larvae"])["peaks"][-1] == pytest.approx(795, abs=10)
    assert critical_points(STAGES["egg_masses"])["peaks"][0] == pytest.approx(565, abs=20)


def test_counts_are_the_fit_back_transformed_and_held_past_the_data():
    table = curves(INSECT)
    x = dd_grid()
    adults = STAGES["adults"]
    at = np.searchsorted(x, 1480)
    assert table["count_adults"][at] == pytest.approx(np.expm1(adults.log_count[adults.dd.index(1480)]))
    assert table["activity_adults"].max() == 1 and (table["count_adults"] >= 0).all()  # below 0 is taken as 0
    assert adults.dd[-1] <= END_OF_DATA_DD
    beyond = evaluate(insect=INSECT, dd_total=np.array([2310.0, 2600.0, 4000.0]))["count_adults"]
    assert beyond[0] == beyond[1] == beyond[2] > 0


def test_risk_is_adults_and_larvae_share_of_its_peak():
    m = all_models()["colorado-potato-beetle"]
    peak = evaluate(insect=INSECT, dd_total=np.array([1350.0]))
    assert m.explore(dd_total=1350)["risk"] == pytest.approx(1.0, abs=0.01)
    assert m.explore(dd_total=0)["risk"] == 0
    assert peak["count_adults_and_larvae"][0] == pytest.approx(6.88, abs=0.01)


def test_adults_and_larvae_is_the_log_of_their_summed_counts():
    """The combined curve is fitted to each field date's adults plus larvae (refitted 2026-11-18; the first fit
    stacked the two stages' rows), so it tracks log(adults + larvae + 1) from the two curves, within 0.1."""
    table = curves(INSECT)
    season = (dd_grid() >= 220) & (dd_grid() <= 2310)
    summed = np.log1p(table["count_adults"] + table["count_larvae"])[season]
    np.testing.assert_allclose(np.log1p(table["count_adults_and_larvae"])[season], summed, atol=0.1)


def test_against_the_crop_risk_tool_at_eau_claire_2025(crt):
    """The tool's step table was a rounded reading of the same fits on 50/86 °F; on 52/86 each event comes later."""
    daily, theirs = crt("daily_eau_claire_2025"), crt("insect_cpb_eau_claire_2025")
    days = daily["date"].astype("datetime64[D]")
    inputs = {
        "air_temperature_min": daily["temperature_min"],
        "air_temperature_max": daily["temperature_max"],
        "day_of_year": (days - days.astype("datetime64[Y]")).astype(int) + 1,
    }
    ours = all_models()["colorado-potato-beetle"].outputs(inputs)["dd_total"]

    def first(total, dd):
        return str(days[np.argmax(total >= dd)])

    tool = np.asarray(theirs["cum_gdd"], dtype=float)
    pairs = {  # event: (the tool's step, the fit's own)
        "colonization": (200, 210),
        "egg hatch": (350, 374),
        "first-generation adult peak": (600, 588),
        "larval peak": (800, 795),
        "second-generation adult peak": (1470, 1477),
    }
    got = {name: (first(tool, a), first(ours, b)) for name, (a, b) in pairs.items()}
    assert got == {
        "colonization": ("2025-05-12", "2025-05-15"),
        "egg hatch": ("2025-05-30", "2025-06-06"),
        "first-generation adult peak": ("2025-06-17", "2025-06-21"),
        "larval peak": ("2025-06-24", "2025-07-01"),
        "second-generation adult peak": ("2025-07-25", "2025-08-03"),
    }
