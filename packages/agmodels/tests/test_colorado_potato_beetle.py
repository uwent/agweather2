"""Colorado potato beetle (0.3): the scouting fits read as fitted stages (D36) on both clocks (D101), against the
refit's own events (`tmp/R/cpb/cv/10_cpb_cv.R`, COUNT_RULE=mean: `cv/out/cpb-mean/full-fit-events.csv`) and the Crop
Risk Tool on the same weather."""

import numpy as np
import pytest

from agmodels.insects.colorado_potato_beetle import INSECT
from agmodels.phenology import FittedStage, calendar_curves, curves, dd_grid, evaluate
from agmodels.registry import all_models

STAGES = {s.key: s for s in INSECT.life_stages if isinstance(s, FittedStage)}


def critical_points(x: tuple[float, ...], y: tuple[float, ...]) -> dict[str, list[float]]:
    """Where the fit crosses zero (or 0.1) upward, and its local maxima and minima (as the refit's events)."""
    xs, ys = np.array(x), np.array(y)
    up = [float(xs[k]) for k in range(1, len(ys)) if ys[k - 1] < 0 <= ys[k]]
    up01 = [float(xs[k]) for k in range(1, len(ys)) if ys[k - 1] < 0.1 <= ys[k]]
    peaks = [float(xs[k]) for k in range(1, len(ys) - 1) if ys[k - 1] < ys[k] >= ys[k + 1]]
    troughs = [float(xs[k]) for k in range(1, len(ys) - 1) if ys[k - 1] > ys[k] <= ys[k + 1]]
    return {"up": up, "up0.1": up01, "peaks": peaks, "troughs": troughs}


# The refit's events on the archive's degree days 52/86 °F from January 1; the curves are every 10, so within 10
@pytest.mark.parametrize(
    ("key", "kind", "expected"),
    [
        ("adults", "up", [203]),  # colonization
        ("adults", "peaks", [558, 1451]),  # overwintered adults, first-generation adults
        ("adults", "troughs", [907]),  # between them
        ("larvae", "up0.1", [402]),  # the larval rise (0.2's "egg hatch" at 374 was a 0.003 dip)
        ("larvae", "peaks", [734, 940]),  # and a shoulder as first-generation larvae wane
        ("adults_and_larvae", "up", [205]),
        ("adults_and_larvae", "peaks", [734, 1326]),
        ("adults_and_larvae", "troughs", [975]),
        ("egg_masses", "up", [217, 1860]),  # first eggs; the first-generation adults' eggs
        ("egg_masses", "peaks", [530]),
    ],
)
def test_the_degree_day_curves_events_are_the_refits(key, kind, expected):
    stage = STAGES[key]
    np.testing.assert_allclose(critical_points(stage.dd, stage.log_count)[kind], expected, atol=10)


# The same events on the calendar (days of year; every day, so within 1)
@pytest.mark.parametrize(
    ("key", "kind", "expected"),
    [
        ("adults", "peaks", [169, 217]),  # June 18, August 5
        ("adults", "troughs", [189]),
        ("larvae", "up0.1", [158]),
        ("larvae", "peaks", [183]),  # July 2
        ("adults_and_larvae", "peaks", [183, 209]),
        ("egg_masses", "peaks", [168, 204]),  # June 17; the first-generation adults' eggs
    ],
)
def test_the_calendar_curves_events_are_the_refits(key, kind, expected):
    stage = STAGES[key]
    np.testing.assert_allclose(critical_points(stage.days, stage.log_count_by_day)[kind], expected, atol=1)


def test_no_larvae_before_they_rise():
    """The larval spline started above 0 and dipped before rising (0.13 at 180, −0.08 at 300): held at its low."""
    table = curves(INSECT)
    before = dd_grid() < 360
    assert (table["count_larvae"][before] == 0).all()
    assert (calendar_curves(INSECT)["count_larvae"][:150] == 0).all()


def test_counts_are_the_fit_back_transformed_and_held_past_the_data():
    table = curves(INSECT)
    x = dd_grid()
    adults = STAGES["adults"]
    at = np.searchsorted(x, 1450)
    assert table["count_adults"][at] == pytest.approx(np.expm1(adults.log_count[adults.dd.index(1450)]))
    assert table["activity_adults"].max() == 1 and (table["count_adults"] >= 0).all()  # below 0 is taken as 0
    last = adults.dd[-1]
    beyond = evaluate(insect=INSECT, dd_total=np.array([last, last + 300, 4000.0]))["count_adults"]
    assert beyond[0] == beyond[1] == beyond[2] > 0


def test_risk_is_adults_and_larvae_share_of_its_peak():
    m = all_models()["colorado-potato-beetle"]
    peak_dd = STAGES["adults_and_larvae"].dd[int(np.argmax(STAGES["adults_and_larvae"].log_count))]
    assert m.explore(dd_total=peak_dd)["risk"] == pytest.approx(1.0)
    assert m.explore(dd_total=0)["risk"] == 0


def test_adults_and_larvae_tracks_the_log_of_their_summed_counts():
    """The combined curve is its own fit to each field date's adults plus larvae, so it tracks log(adults + larvae
    + 1) from the two curves, within 0.15 over the season."""
    table = curves(INSECT)
    season = (dd_grid() >= 250) & (dd_grid() <= 2170)
    summed = np.log1p(table["count_adults"] + table["count_larvae"])[season]
    np.testing.assert_allclose(np.log1p(table["count_adults_and_larvae"])[season], summed, atol=0.15)


def test_the_model_runs_where_its_data_came_from_and_beyond():
    spec = all_models()["colorado-potato-beetle"].SPEC
    assert spec.trained is not None and spec.trained.contains(state="WI", fips="55001")  # Adams County
    assert not spec.trained.contains(state="WI", fips="55079")  # Milwaukee County
    assert spec.region == ()  # shown everywhere, with a warning outside
    assert [o.name for o in spec.options] == ["clock"] and spec.options[0].default == "degree_days"


def test_against_the_crop_risk_tool_at_eau_claire_2025(crt):
    """The tool's step table was a rounded reading of 0.2's fits on 50/86 °F; on 52/86 and the refit, each event
    comes on these dates."""
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
    pairs = {  # event: (the tool's step, the refit's own)
        "colonization": (200, 203),
        "larval rise": (350, 402),  # the tool's "egg hatch"
        "overwintered adult peak": (600, 558),
        "larval peak": (800, 734),
        "first-generation adult peak": (1470, 1451),
    }
    got = {name: (first(tool, a), first(ours, b)) for name, (a, b) in pairs.items()}
    assert got == {
        "colonization": ("2025-05-12", "2025-05-15"),
        "larval rise": ("2025-05-30", "2025-06-08"),
        "overwintered adult peak": ("2025-06-17", "2025-06-20"),
        "larval peak": ("2025-06-24", "2025-06-28"),
        "first-generation adult peak": ("2025-07-25", "2025-08-02"),
    }
