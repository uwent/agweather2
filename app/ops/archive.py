"""The archive a year at a time: what each year holds (`manage.py archive`, the dashboard), and filling whole years
(`archive fill`), newest first so each finished year is usable at once.

A year's fill is the TODO recipe it replaces, in one process:

1. its URMA/RTMA/HRRR hours (`ops.backfill`: the next block downloads while this one is written);
2. its December 31, which needs the next year's first UTC hours (in already, going backwards);
3. its ERA5-Land soil and snow, a month per CDS request (`ops.era5land.backfill_era5land`);
4. its copy laid out for points (`agdata.pastyears`, the projection's);
5. the models' ingredients (`agdata.modelmaps`, Phase 5 F).

Steps 3 to 5 run in a second thread while the main thread starts the next year's hours, so the CDS's queue (about
an hour a year) overlaps the downloads rather than adding to them. The two threads share the write lock like any
two writers, politely.
"""

import queue
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import zarr

from agdata import modelmaps, pastyears
from agdata.cumulative import update_days
from agdata.grid import Window
from agdata.ingest import SOIL
from agdata.progress import Reporter
from agdata.rebuild import find_stale
from agdata.store import DAILY, HOURLY, SOURCES
from ops import backfill
from ops.era5land import backfill_era5land, missing_days

SECONDS_PER_HOUR = 4.7  # URMA backfill here, measured over 2024 (11.5 h for 8,784 hours) when nothing better is known
ERA5LAND_MONTH_S = 5 * 60  # a month's request with 3 in flight, measured over 2024 (12 months in about an hour)


@dataclass(kw_only=True)
class YearState:
    year: int
    hours: int  # hours in the year (through now, this year)
    analysis: int  # hours with an analysis (temperature)
    urma: int
    rtma: int
    precip: int
    shortwave: int
    days: int  # days in the year (through yesterday, this year)
    era5land_days: int  # UTC days whose 24 hours of soil are all ERA5-Land's
    rolled_up: int  # local days with a daily minimum temperature
    past_years: str  # "current", why it needs building, or "–" (this year has none)
    stale: list[str] = field(default_factory=list)  # store kinds with stale variables

    @property
    def complete(self) -> bool:
        return (
            self.analysis >= self.hours
            and self.precip >= self.hours
            and self.shortwave >= self.hours
            and self.era5land_days >= self.days
            and self.rolled_up >= self.days
            and self.past_years in ("current", "–")
            and not self.stale
        )


def year_states(data_dir: Path, years: list[int] | None = None, now: datetime | None = None) -> list[YearState]:
    """Each year on disk (or in `years`), newest first. Reads source metadata only, without the lock (~0.1 s a
    year)."""
    now = now or datetime.now(UTC)
    on_disk = set(pastyears.years_on_disk(data_dir, HOURLY)) | set(pastyears.years_on_disk(data_dir, DAILY))
    wanted = sorted(on_disk | set(years or []), reverse=True)
    stale: dict[int, list[str]] = {}
    for key in find_stale(data_dir).stale:
        kind, year = key.split("/")
        stale.setdefault(int(year), []).append(kind)
    out = []
    for year in wanted:
        start = datetime(year, 1, 1, tzinfo=UTC)
        end = min(datetime(year + 1, 1, 1, tzinfo=UTC), now)
        hours = max(0, int((end - start) / timedelta(hours=1)))
        days = max(0, (min(date(year + 1, 1, 1), now.date()) - date(year, 1, 1)).days)
        analysis = _codes(HOURLY.path(data_dir, year), "air_temperature")
        precip = _codes(HOURLY.path(data_dir, year), "precipitation")
        shortwave = _codes(HOURLY.path(data_dir, year), "shortwave_radiation")
        soil = _codes(HOURLY.path(data_dir, year), SOIL[0])
        daily = _codes(DAILY.path(data_dir, year), "air_temperature_min")
        era5 = 0
        if soil is not None:
            whole = soil[: len(soil) // 24 * 24].reshape(-1, 24)
            era5 = int((whole == SOURCES["era5land"]).all(axis=1)[:days].sum())
        if year >= now.year:
            past = "–"
        elif not DAILY.path(data_dir, year).exists():
            past = "missing"
        else:
            past = pastyears.status(data_dir, year) or "current"
        out.append(
            YearState(
                year=year,
                hours=hours,
                analysis=_count(analysis, hours),
                urma=_count(analysis, hours, SOURCES["urma"]),
                rtma=_count(analysis, hours, SOURCES["rtma"]),
                precip=_count(precip, hours),
                shortwave=_count(shortwave, hours),
                days=days,
                era5land_days=era5,
                rolled_up=_count(daily, days),
                past_years=past,
                stale=sorted(stale.get(year, [])),
            )
        )
    return out


def seconds_per_hour() -> float:
    """The backfill's measured rate: wall time per hour fetched over its recent blocks (`IngestRecord`), or the
    2024 figure without them."""
    from ops.models import IngestRecord

    rows = list(
        IngestRecord.objects.filter(kind=IngestRecord.Kind.BACKFILL, hours__gte=24).order_by("-started_at")[:50]
    )
    hours = sum(r.hours for r in rows)
    seconds = sum((r.finished_at - r.started_at).total_seconds() for r in rows)
    return seconds / hours if hours >= 240 and seconds > 0 else SECONDS_PER_HOUR


@dataclass(kw_only=True)
class YearPlan:
    year: int
    first: date
    end: date  # exclusive
    hours: backfill.Plan
    era5land_days: int
    past_years: bool  # needs building


@dataclass(kw_only=True)
class FillResult:
    years: list[int] = field(default_factory=list)  # finished
    fetched: int = 0
    failed: int = 0
    stopped: bool = False


Lock = Callable[..., AbstractContextManager[None]]


def plan_years(
    data_dir: Path, window: Window, years: list[int], block_days: int, today: date | None = None
) -> list[YearPlan]:
    """What each year lacks, newest first. The caller holds the write lock (an absent year's stores are made)."""
    today = today or datetime.now(UTC).date()
    out = []
    for year in sorted(years, reverse=True):
        first, end = date(year, 1, 1), min(date(year + 1, 1, 1), today)
        hours = backfill.plan(data_dir, window, _midnight(first), _midnight(end), block_days)
        era5_last = min(end, today - timedelta(days=5)) - timedelta(days=1)  # ERA5-Land's lag
        era5 = len(missing_days(data_dir, window, first, era5_last)) if era5_last >= first else 0
        past = year < today.year and (
            not DAILY.path(data_dir, year).exists() or pastyears.status(data_dir, year) is not None
        )
        out.append(YearPlan(year=year, first=first, end=end, hours=hours, era5land_days=era5, past_years=past))
    return out


def estimate_s(plans: list[YearPlan], per_hour: float) -> float:
    """The fill's time: the hours' downloads, plus the last year's ERA5-Land (the others overlap the next year)."""
    hours = sum(p.hours.hours for p in plans) * per_hour
    last = next((p for p in reversed(plans) if p.era5land_days), None)
    tail = (last.era5land_days / 30 * ERA5LAND_MONTH_S) if last else 0
    return hours + tail


def fill(
    *,
    data_dir: Path,
    window: Window,
    box: str,
    plans: list[YearPlan],
    report: Reporter,
    lock: Lock,
    stopping: threading.Event,
    workers: int,
    key: str | None,
    overlap: bool = True,
    soil: bool = True,
    past: bool = True,
) -> FillResult:
    """Fills the planned years newest first (see the module). Without `key` (no CDS), soil is skipped with a
    warning."""
    result = FillResult()
    total = sum(p.hours.hours for p in plans)
    span = f"{plans[-1].year}–{plans[0].year}" if len(plans) > 1 else str(plans[0].year)
    label = f"hours {span}"
    if soil and not key:
        report.warn("COPERNICUS_API_KEY isn't set: no ERA5-Land soil and snow (rerun with it to add them)")
        soil = False
    later: queue.Queue = queue.Queue()  # years whose hours are in, for ERA5-Land and the past-years copy
    errors: list[BaseException] = []

    def finish_years() -> None:
        while (plan := later.get()) is not None:
            if stopping.is_set():
                continue
            try:
                finish_year(plan)
            except BaseException as error:  # reported; the main thread carries on with the next year's hours
                errors.append(error)
                report.fail(f"{plan.year} soil and past years", error)

    def finish_year(plan: YearPlan) -> None:
        if soil and plan.era5land_days:
            backfill_era5land(
                data_dir=data_dir,
                window=window,
                first=plan.first,
                end=plan.end,
                key=key or "",
                report=report,
                lock=lock,
                stopping=stopping,
                label=f"ERA5-Land {plan.year}",
            )
        if not stopping.is_set() and modelmaps.status(data_dir, plan.year) is not None:
            began = time.monotonic()
            modelmaps.build(
                data_dir,
                window,
                plan.year,
                lock=lambda: lock(polite=True),
                progress=lambda done, n: report.progress(f"ingredients {plan.year}", done, n),
            )
            report.step(f"{plan.year}: models' ingredients built in {time.monotonic() - began:.0f} s")
        if past and not stopping.is_set():
            # Rolling up December 31 rewrote the next year's daily store too: its copy may be out of date now
            following = plan.year + 1
            if (
                following < datetime.now(UTC).year
                and pastyears.PAST.path(data_dir, following).exists()
                and pastyears.status(data_dir, following) is not None
            ):
                build_past(following)
        if past and plan.past_years and not stopping.is_set():
            build_past(plan.year)

    def build_past(year: int) -> None:
        began = time.monotonic()
        try:
            pastyears.build(data_dir, year, progress=lambda done, n: report.progress(f"past years {year}", done, n))
        except ValueError as error:  # stale daily variables: `rebuild --stale` first
            report.warn(f"{year}'s past-years copy not built: {error}")
            return
        report.step(f"{year}: past-years copy built in {time.monotonic() - began:.0f} s")

    helper = threading.Thread(target=finish_years, name="fill-soil", daemon=True)
    helper.start()
    done = 0
    try:
        for plan in plans:
            if stopping.is_set():
                break
            report.step(
                f"{plan.year}: {plan.hours.hours} hours to fetch, {plan.era5land_days} days of ERA5-Land, "
                f"past-years copy {'to build' if plan.past_years else 'current'}"
            )
            run = backfill.run(  # a year whose hours are all in only rolls up days that aren't
                data_dir=data_dir,
                window=window,
                box=box,
                first=plan.first,
                the_plan=plan.hours,
                report=report,
                lock=lock,
                workers=workers,
                stopping=stopping,
                label=label,
                base=done,
                total=total,
            )
            done += plan.hours.hours
            result.fetched += run.fetched
            result.failed += run.failed
            if run.stopped:
                break
            if plan.end == date(plan.year + 1, 1, 1) and HOURLY.path(data_dir, plan.year + 1).exists():
                with lock(polite=True):  # December 31 runs into the next year's first UTC hours
                    update_days(data_dir, window, date(plan.year, 12, 31), date(plan.year, 12, 31), ingredients=False)
                report.detail(f"{plan.year}: rolled up December 31")
            report.step(f"{plan.year}: hours in" + (" (soil and past years next, alongside)" if overlap else ""))
            later.put(plan)
            if not overlap:
                _drain(later, helper)
                helper = threading.Thread(target=finish_years, name="fill-soil", daemon=True)
                helper.start()
            result.years.append(plan.year)
    finally:
        later.put(None)
        while helper.is_alive():  # ERA5-Land's last year, or a stop's dropped requests
            helper.join(timeout=1)
    result.stopped = stopping.is_set()
    return result


def _drain(later: queue.Queue, helper: threading.Thread) -> None:
    later.put(None)
    helper.join()


def _codes(path: Path, name: str) -> np.ndarray | None:
    try:
        return np.asarray(zarr.open_group(path, mode="r")[f"_meta/{name}.source"][:])  # type: ignore[index]
    except (FileNotFoundError, KeyError):
        return None


def _count(codes: np.ndarray | None, n: int, code: int | None = None) -> int:
    if codes is None:
        return 0
    head = codes[:n]
    return int((head == code).sum() if code is not None else (head > 0).sum())


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)
