"""The alfalfa cut planner (`agmodels.alfalfa_plan`): its schedule against the UW alfalfa tool's own function, and
the plan's season, cuts and fall check."""

import csv
from pathlib import Path

import numpy as np
import pytest

from agmodels.alfalfa_plan import (
    FALL_OVER,
    FALL_UNDER,
    Climate,
    best_divisions,
    fall_rule_safe,
    plan,
    schedule,
)

FIXTURES = Path(__file__).parent / "fixtures"
JULY_1 = 181  # 2025's (not a leap year): day index of July 1


def _season() -> np.ndarray:
    with (FIXTURES / "alfalfa_plan_season.csv").open() as f:
        return np.array([float(row["gdd"]) for row in csv.DictReader(f)])


def _tool_cases() -> list[dict[str, str]]:
    with (FIXTURES / "alfalfa_plan_tool.csv").open() as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("case", _tool_cases(), ids=lambda c: c["case"])
def test_schedule_matches_the_tools(case):
    """The tool's `schedule_cut_dates` (run in R by make_alfalfa_plan.R) on a made-up season: the same cut days for
    every interval, number of cuts and held cuts. The season's start (after the freeze on day 100) and end (the
    tool's day 275, its first day at a 10 % chance) are given, so only the segment arithmetic is compared."""
    gdd = _season()
    start = 100  # day 101's index: the day after the freeze on day 100
    cum = np.zeros(gdd.size)
    cum[start:] = np.cumsum(gdd[start:])
    end = int(case["end_day"]) - 1
    held = [int(h) - 1 for h in case["held"].split()]
    interval = float(case["interval"]) if case["interval"] != "NA" else None
    count = int(case["count"]) if case["count"] != "NA" else None
    days = schedule(cum=cum, start=start, end=end, held=held, interval=interval, count=count)
    assert [d + 1 for d in days] == [int(d) for d in case["days"].split()]


def test_best_divisions_leans_to_more_cuts_on_a_tie():
    assert best_divisions(length=3000, target=1000) == 3
    assert best_divisions(length=2500, target=1000) == 3  # 833 and 1250 are equally far: the more cuts
    assert best_divisions(length=400, target=1000) == 1


def _climate(gdd: np.ndarray, **kw) -> Climate:
    found = {
        "normal_gdd": gdd,
        "spring_typical": 99,
        "fall_end": 274,
        "fall_typical": 290,
        "fall_freezes": (270, 280, 290, 300, None),
    }
    return Climate(**(found | kw))


def test_a_whole_season_on_the_normal():
    """No weather yet (January): the season starts after the typical last spring freeze and ends at the 1-in-10
    fall date; every cut rests on the normal."""
    normal = _season()
    unknown = np.full(normal.size, np.nan)
    p = plan(gdd=unknown, killed=unknown, climate=_climate(normal), july_1=JULY_1)
    assert (p.start, p.start_basis) == (100, "typical")
    assert (p.end, p.end_basis) == (274, "typical")
    assert [c.day + 1 for c in p.cuts] == [166, 212, 275]
    assert all(c.projected for c in p.cuts)
    assert p.interval == 1000 and p.count is None
    assert p.from_normal.all()
    # Each cut's GDD since the last: about a third of the season each, all within the window
    assert [c.status for c in p.cuts] == ["window", "window", "window"]
    assert sum(c.gdd for c in p.cuts) == pytest.approx(np.sum(normal[100:275]))
    # The sawtooth starts again the day after each cut
    assert p.since_cut[165] == pytest.approx(p.cuts[0].gdd)
    assert p.since_cut[166] == pytest.approx(normal[166])
    assert np.isnan(p.since_cut[99])


def test_this_years_weather_sets_the_start_and_the_end():
    normal = _season()
    weather = normal * 1.1
    weather[330:] = np.nan  # through November 26
    killed = np.zeros(normal.size)
    killed[[60, 110, 300]] = 1  # a late spring freeze on day 111, a fall one on day 301
    killed[330:] = np.nan
    p = plan(gdd=weather, killed=killed, climate=_climate(normal, fall_end=320), july_1=JULY_1)
    assert (p.start, p.start_basis) == (111, "observed")
    assert (p.end, p.end_basis) == (300, "observed")
    assert p.fall.observed == 300
    assert not p.cuts[0].projected
    # Growth stops at the fall freeze
    assert np.isnan(p.since_cut[301])
    assert p.since_cut[300] == pytest.approx(p.since_cut[299])


def test_a_spring_freeze_later_than_typical_while_spring_is_ahead():
    normal = _season()
    weather = np.full(normal.size, np.nan)
    weather[:80] = 1.0
    killed = np.full(normal.size, np.nan)
    killed[:80] = 0
    killed[70] = 1
    p = plan(gdd=weather, killed=killed, climate=_climate(normal, spring_typical=60), july_1=JULY_1)
    assert (p.start, p.start_basis) == (71, "observed")
    q = plan(gdd=weather, killed=killed, climate=_climate(normal, spring_typical=90), july_1=JULY_1)
    assert (q.start, q.start_basis) == (91, "typical")


def test_cuts_as_given_are_checked_not_moved():
    normal = _season()
    unknown = np.full(normal.size, np.nan)
    p = plan(gdd=unknown, killed=unknown, climate=_climate(normal), july_1=JULY_1, cuts=[150, 175, 260], held=[150])
    assert [c.day for c in p.cuts] == [150, 175, 260]
    assert [c.held for c in p.cuts] == [True, False, False]
    assert p.cuts[1].status == "early"  # 25 days after the first: well under 900 GDD
    assert p.cuts[2].status == "late"
    assert p.interval is None and p.count is None
    assert p.cuts[0].days == 51  # days 101 through 151 (indexes 100–150), as the tool's days since the freeze


def test_the_fall_check_counts_each_years_freeze():
    """From the last cut on day 261 (index 260), regrowth to each year's freeze: the earliest years fall in the risky
    band or under it, a year with no freeze by December 31 runs over 900 or stays between."""
    normal = _season()
    unknown = np.full(normal.size, np.nan)
    freezes = (250, 262, 275, 300, None)
    p = plan(
        gdd=unknown,
        killed=unknown,
        climate=_climate(normal, fall_freezes=freezes),
        july_1=JULY_1,
        cuts=[180, 260],
    )
    f = p.fall
    assert f.last_cut == 260 and f.years == 5
    assert f.before_cut == 1  # the year that froze on day 251
    after = [float(np.sum(normal[261:d])) for d in (262, 275, 300, normal.size)]
    assert f.under == sum(a < FALL_UNDER for a in after)
    assert f.over == sum(a > FALL_OVER for a in after)
    assert f.between == sum(FALL_UNDER <= a <= FALL_OVER for a in after)
    assert f.under + f.over + f.between + f.before_cut == 5
    assert f.typical_regrowth == pytest.approx(float(np.sum(normal[261:290])))


def test_by_number_of_cuts_with_a_held_cut():
    normal = _season()
    unknown = np.full(normal.size, np.nan)
    p = plan(gdd=unknown, killed=unknown, climate=_climate(normal), july_1=JULY_1, held=[149], count=4)
    assert len(p.cuts) == 4 and p.cuts[0].day == 149 and p.cuts[0].held
    assert p.count == 4 and p.interval is None


def test_no_climate_runs_to_the_years_end():
    normal = _season()
    unknown = np.full(normal.size, np.nan)
    p = plan(
        gdd=unknown,
        killed=unknown,
        climate=Climate(normal_gdd=normal, spring_typical=None, fall_end=None, fall_typical=None, fall_freezes=()),
        july_1=JULY_1,
    )
    assert (p.start, p.start_basis) == (0, "none")
    assert (p.end, p.end_basis) == (normal.size - 1, "none")
    assert p.fall.years == 0


def test_fall_rule_safe():
    assert fall_rule_safe(None) and fall_rule_safe(200) and fall_rule_safe(950)
    assert not fall_rule_safe(600)
