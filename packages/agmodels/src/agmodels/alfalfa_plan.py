"""Alfalfa's season of cuttings (F5; Phase 7 track 5): when to cut, by growing degree days (single sine, 41/86 °F)
since the season's start or the last cut, and whether the last cut leaves the stand safe for winter.

Ported from the UW alfalfa tool's cut scheduler (`tmp/R/alfalfa-tool/app/src/3_timing.R`, `schedule_cut_dates`, on
`global.R`'s `buildGrowthData`). The season's GDD are the year's own where we have weather (observed, then the
forecast) and the period's normal mean daily GDD after (smooth, so a plan doesn't jump as it's edited); they count
from the last spring killing freeze (24 °F or colder). Cuts sit in GDD along that path: held cuts stay where they
are, and each stretch between them, and from the last to the season's end, is split into equal parts, either to
come nearest a target interval (800–1,200 GDD, default 1,000) or to give a number of cuts (the extra cuts going one
at a time to the stretch with the widest parts). A last stretch under 360 GDD is left uncut. The season's end, on
which the last cut lands, is the date by which one year in ten has had its first fall killing freeze.

The fall rule (Newell; the 360 and 900 GDD, base 41 °F, of `alfalfa_growth`) is checked against each of the
period's years: the regrowth from the last cut to that year's own first fall killing freeze, along this season's
path, is safe under 360 or over 900 GDD, or when the freeze came before the last cut.

Intended differences from the tool, each a latent bug or a choice it left inconsistent (Ben, 2026-11-26):

(a) The tool keeps generated cuts with `between(gen_days, 60, end_gdd)`, a day of the year against a GDD total, so
    its upper bound never applies; we keep every cut up to the season's end, and none before its start.
(b) The tool's chance of a killing freeze by a date is 1 − ∏(1 − p) over the days before it, which treats days as
    independent and runs high; ours counts each year's own first fall (last spring) killing freeze
    (`agdata.climatology.freezes`), the chance `/climate/frost/chances` gives.
(c) The tool projects a killing freeze on every day whose cumulative chance is at least 95 %, so the season starts
    and ends on those days; we start the season at the typical (median) last spring killing freeze while this
    year's spring is still ahead of it, and at this year's observed one after.
(d) The tool's thresholds disagree: 900–1,100 GDD in its growth text, 800–1,100 in its timing text, intervals
    800–1,200, and a fall rule of "under 360 or over 800". We use the model's 900–1,100 window, Newell's fall rule
    (under 360 or over 900) and intervals 800–1,200, default 1,000.
(e) Future days come from the normal's mean daily GDD, as the tool's do, where the degree-day projections (D63) run
    each earlier year's weather: a plan needs one path to put cuts on, and the years' spread is checked where it
    matters, at the fall freeze.

The tool places a cut on the day whose GDD is nearest the target, as we do; between its held cuts and its season's
end, the segment arithmetic is the tool's (`test_alfalfa_plan.py` holds it to the tool's own function).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from agmodels.models.alfalfa_growth import CUT_FROM, CUT_UNTIL

KILL_F = 24.0  # a killing freeze for alfalfa: the day's minimum at or below
FALL_UNDER, FALL_OVER = 360.0, 900.0  # Newell's fall rule: regrowth before the killing freeze under, or over
INTERVAL_MIN, INTERVAL_MAX, INTERVAL_DEFAULT = 800.0, 1200.0, 1000.0
INTERVALS = (INTERVAL_MIN, INTERVAL_MAX, INTERVAL_DEFAULT)
COUNT_MIN, COUNT_MAX = 1, 8  # cuts a plan by number can ask for
FALL_END_SHARE = 0.10  # the season ends on the date by which this share of years had a fall killing freeze
TYPICAL_SHARE = 0.50  # the typical (median) last spring killing freeze

Status = Literal["early", "window", "late"]
Basis = Literal["observed", "typical", "none"]


@dataclass(frozen=True, kw_only=True)
class Climate:
    """What the period's years say at the place, as days of the plan's year (0 = January 1)."""

    normal_gdd: np.ndarray  # mean daily GDD (°F·d) on each day of the year
    spring_typical: int | None  # the median last spring killing freeze; None where most springs have none
    fall_end: int | None  # the day by which `FALL_END_SHARE` of years had their first fall killing freeze
    fall_typical: int | None  # the median first fall killing freeze; None where most falls have none by December 31
    fall_freezes: Sequence[int | None]  # each counted year's first fall killing freeze; None: none by December 31


@dataclass(frozen=True, kw_only=True)
class Cut:
    day: int
    held: bool
    gdd: float  # since the season's start or the previous cut, through the cut's day
    days: int  # since the season's start (the day after the freeze) or the previous cut
    status: Status  # against the cutting window: before it, in it, past it
    projected: bool  # its growth reaches past the weather we have, onto the normal


@dataclass(frozen=True, kw_only=True)
class FallCheck:
    """The regrowth from the last cut to each year's first fall killing freeze (Newell's rule)."""

    last_cut: int | None
    years: int  # the years counted
    under: int  # regrowth under `FALL_UNDER`: too little to draw down the roots' reserves
    over: int  # over `FALL_OVER`: enough to rebuild them
    between: int  # in between: the risk to the stand the rule warns of
    before_cut: int  # the freeze came on or before the last cut
    typical: int | None  # the median first fall killing freeze
    typical_regrowth: float | None  # to it
    observed: int | None  # this year's first fall killing freeze, where the weather has it
    observed_regrowth: float | None


@dataclass(frozen=True, kw_only=True)
class Plan:
    start: int  # the first day whose GDD count: the day after the last spring killing freeze, or January 1
    start_basis: Basis  # this year's freeze, the typical one, or none (January 1)
    end: int  # the season's end, where the last cut of a schedule lands
    end_basis: Basis  # this year's fall killing freeze, the typical (1-in-10) date, or none (December 31)
    cuts: list[Cut]
    gdd: np.ndarray  # each day's GDD on the path: the weather's, or the normal's
    from_normal: np.ndarray  # the days whose GDD are the normal's
    since_cut: (
        np.ndarray
    )  # GDD since the start or the last cut, through each day (NaN before the start, after a fall freeze)
    fall: FallCheck
    interval: float | None = None
    count: int | None = None
    held: tuple[int, ...] = field(default_factory=tuple)


def plan(
    *,
    gdd: np.ndarray,
    killed: np.ndarray,
    climate: Climate,
    july_1: int,
    cuts: Sequence[int] | None = None,
    held: Sequence[int] = (),
    interval: float | None = None,
    count: int | None = None,
) -> Plan:
    """The season's plan on one calendar year's days.

    `gdd`: each day's GDD (°F·d) from the weather, NaN where we have none (after the forecast, or a gap too long to
    estimate). `killed`: 1 where the day's minimum was a killing freeze, 0 where it wasn't, NaN where unknown.
    `july_1`: the day index of July 1 (spring is before it). `cuts`: the dates to check as given (no scheduling);
    otherwise a schedule keeps `held` and fills in by `interval` (default `INTERVAL_DEFAULT`) or `count`."""
    gdd = np.asarray(gdd, dtype=float)
    killed = np.asarray(killed, dtype=float)
    n = gdd.size
    normal = np.nan_to_num(np.asarray(climate.normal_gdd, dtype=float))
    known = np.isfinite(gdd)
    path = np.where(known, gdd, normal)
    from_normal = ~known
    data_end = int(np.flatnonzero(known)[-1]) if known.any() else -1
    froze = np.flatnonzero(killed == 1)

    # The season's start: the day after the last spring killing freeze
    spring_seen = froze[froze < july_1]
    spring_over = data_end >= july_1 - 1 or climate.spring_typical is None or data_end >= climate.spring_typical
    if not spring_over:
        assert climate.spring_typical is not None
        last = max(climate.spring_typical, int(spring_seen[-1]) if spring_seen.size else -1)
        start, start_basis = last + 1, "typical" if last == climate.spring_typical else "observed"
    elif spring_seen.size:
        start, start_basis = int(spring_seen[-1]) + 1, "observed"
    else:
        start, start_basis = 0, "none"

    # The season's end: this year's first fall killing freeze, or the 1-in-10 date, whichever comes first
    fall_seen = froze[froze >= july_1]
    observed_fall = int(fall_seen[0]) if fall_seen.size else None
    ends = [(d, b) for d, b in ((observed_fall, "observed"), (climate.fall_end, "typical")) if d is not None]
    end, end_basis = min(ends) if ends else (n - 1, "none")
    end = max(end, start)

    cum = np.full(n, np.nan)
    cum[start:] = np.cumsum(path[start:])
    at = np.where(np.isfinite(cum), cum, 0.0)  # a day before the start sits at the season's 0

    held_days = sorted({int(h) for h in held})
    if cuts is not None:
        days = sorted({int(c) for c in cuts})
    else:
        days = schedule(
            cum=at, start=start, end=end, held=held_days, interval=interval if count is None else None, count=count
        )
    held_set = set(held_days)
    found: list[Cut] = []
    before_day, before_gdd = start - 1, 0.0
    for d in days:
        grown = float(at[d] - before_gdd) if d >= start else 0.0
        found.append(
            Cut(
                day=d,
                held=d in held_set,
                gdd=max(grown, 0.0),
                days=max(d - before_day, 0),
                status=_status(round(grown)),  # on whole degree days, as they are shown
                projected=bool(from_normal[max(before_day + 1, 0) : d + 1].any()),
            )
        )
        if d >= start:
            before_day, before_gdd = d, float(at[d])

    since = np.full(n, np.nan)
    running, cut_set = 0.0, set(days)
    stop = observed_fall if observed_fall is not None else n
    for d in range(start, min(stop + 1, n)):
        running += path[d] if d < stop else 0.0  # the freeze's day adds nothing, and growth stops there
        since[d] = running
        if d in cut_set:
            running = 0.0

    return Plan(
        start=start,
        start_basis=start_basis,  # type: ignore[arg-type]
        end=end,
        end_basis=end_basis,  # type: ignore[arg-type]
        cuts=found,
        gdd=path,
        from_normal=from_normal,
        since_cut=since,
        fall=_fall_check(
            at=at, start=start, last_cut=days[-1] if days else None, climate=climate, observed=observed_fall, n=n
        ),
        interval=None if cuts is not None or count is not None else (interval or INTERVAL_DEFAULT),
        count=count if cuts is None else None,
        held=tuple(held_days),
    )


def schedule(
    *,
    cum: np.ndarray,
    start: int,
    end: int,
    held: Sequence[int] = (),
    interval: float | None = None,
    count: int | None = None,
) -> list[int]:
    """Cut days: `held` kept, the rest placed in GDD along `cum` (the running total from the season's start, 0
    before it) between them and from the last to `end`, by `interval` or `count` (the tool's `schedule_cut_dates`)."""
    end_gdd = float(cum[end])
    held_gdd = [float(cum[h]) for h in held]
    if held_gdd and max(held_gdd) >= end_gdd:  # a held cut at or past the end: no stretch after it
        points = sorted({0.0, *held_gdd})
        has_tail = False
    else:
        points = sorted({0.0, *held_gdd, end_gdd})
        has_tail = True
    lows, highs = points[:-1], points[1:]
    lengths = [hi - lo for lo, hi in zip(lows, highs, strict=True)]
    segments = len(lengths)
    tail = [has_tail and k == segments - 1 for k in range(segments)]
    if count is not None:
        divisions = [1] * segments
        for _ in range(max(0, count - segments)):
            widest = max(range(segments), key=lambda k: lengths[k] / divisions[k])  # first of equals, as which.max
            divisions[widest] += 1
    else:
        target = interval or INTERVAL_DEFAULT
        divisions = [
            0 if tail[k] and lengths[k] < FALL_UNDER else best_divisions(length=lengths[k], target=target)
            for k in range(segments)
        ]
    positions: list[float] = []
    for k in range(segments):
        if divisions[k] < 1:
            continue
        steps = range(1, divisions[k] + 1) if tail[k] else range(1, divisions[k])
        positions += [lows[k] + lengths[k] * s / divisions[k] for s in steps]
    span = cum[start : end + 1]
    placed = [start + int(np.argmin(np.abs(span - p))) for p in positions] if span.size else []
    return sorted({*held, *placed})


def best_divisions(*, length: float, target: float) -> int:
    """How many equal parts of `length` come nearest `target`, the more on a tie (more, shorter cuts)."""
    if length <= 0:
        return 1
    r = length / target
    candidates = sorted({max(1, int(np.floor(r))), max(1, int(np.ceil(r)))}, reverse=True)
    return min(candidates, key=lambda c: abs(length / c - target))


def _status(grown: float) -> Status:
    if grown < CUT_FROM:
        return "early"
    return "window" if grown <= CUT_UNTIL else "late"


def _fall_check(
    *, at: np.ndarray, start: int, last_cut: int | None, climate: Climate, observed: int | None, n: int
) -> FallCheck:
    from_day = last_cut if last_cut is not None and last_cut >= start else start - 1
    base = float(at[from_day]) if from_day >= 0 else 0.0

    def regrowth(freeze: int | None) -> float | None:
        """GDD after the last cut through the day before the freeze (the freeze's day adds nothing, as the tool's)."""
        day = n if freeze is None else freeze
        if day <= from_day:
            return None
        return float(at[day - 1] - base) if day - 1 >= 0 else 0.0

    under = over = between = before = 0
    for f in climate.fall_freezes:
        grown = regrowth(f)
        if grown is None:
            before += 1
        elif grown < FALL_UNDER:
            under += 1
        elif grown > FALL_OVER:
            over += 1
        else:
            between += 1
    return FallCheck(
        last_cut=last_cut,
        years=len(climate.fall_freezes),
        under=under,
        over=over,
        between=between,
        before_cut=before,
        typical=climate.fall_typical,
        typical_regrowth=regrowth(climate.fall_typical) if climate.fall_typical is not None else None,
        observed=observed,
        observed_regrowth=regrowth(observed) if observed is not None else None,
    )


def fall_rule_safe(regrowth: float | None) -> bool:
    """Whether a last cut's regrowth before the killing freeze keeps to the fall rule (None: the freeze came first)."""
    return regrowth is None or regrowth < FALL_UNDER or regrowth > FALL_OVER
