"""County and state summaries (docs/api.md, "Summaries"; PLAN.md Phase 6 C5): a layer's statistics over each
county's or state's cells, on one day or hour, each step of a range, a range reduced by `stat`, or each month of it.

A region's cells are those `agdata.regions.summary_counties` gives it (open water left out). Coverage is the share
of all its cells on the 2.5 km grid that have a value here, so a county partly outside the area we cover, or with
cells missing data, has less than 100%; under `min_coverage` its statistics are null, but its row stays, so a
table of counties is always whole. What the map is and how it's computed is `api.layermaps`, as for `/grids`.
"""

import time
from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Literal

import numpy as np
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from ninja import Field, Query, Router

from agdata import regions
from api import clock, layermaps
from api.envelope import Column, Result, etag_for, not_modified, requested_format, respond
from api.errors import ApiError
from api.events import to_date
from api.layermaps import LayerAsk, LayerQuery
from api.params import OutputQuery
from api.schemas import TableResponse, responses

router = Router(tags=["Maps and grids"])
FORMATS = ("json", "csv")
MAX_ROWS = 200_000  # a year of days for every county in the launch box is ~370,000


class SummaryQuery(LayerQuery):
    """A layer's step or range (`LayerQuery`), summarized by county or state."""

    by: Literal["county", "state"] = "county"
    region: str | None = None
    min_coverage: float = Field(50, ge=0, le=100)
    interval: Literal["month"] | None = None


@router.get("/summaries/{layer}", response=responses(TableResponse), summary="A layer by county or state")
def summary(request: HttpRequest, layer: str, query: Query[SummaryQuery], output: Query[OutputQuery]) -> HttpResponse:
    """A layer's mean, min and max over each county's or state's cells (for a map of levels, the percent of cells at
    each), with each region's land area, cells and coverage; a row per region and step, month or range."""
    started = time.perf_counter()
    fmt = requested_format(request, FORMATS)
    now = clock.now()
    a = layermaps.ask(request, layer, query, output.units, now)
    by = query.by
    archive = layermaps.archive_window(settings.DATA_DIR, a.stores)
    labels = regions.area_labels(by, archive)
    echo: dict[str, Any] = {"by": by}
    if query.region is not None:
        region = layermaps.find_region(query.region)
        wanted = regions.area_indices(region, by)
        echo["region"] = {"id": region.id, "name": region.name}
    else:
        wanted = [int(k) for k in np.unique(labels) if k > 0]
    inside = np.isin(labels, wanted)
    if not inside.any():
        name = echo["region"]["name"] if "region" in echo else "The region"
        raise ApiError("outside_box", f"{name} is outside the area we cover, so it has no grid cells here.", "region")
    periods = _periods(a, query.interval)
    steps = len(periods) if a.stat is not None else a.steps
    if len(wanted) * steps > MAX_ROWS:
        raise ApiError(
            "too_large",
            f"This request would make {len(wanted) * steps:,} rows ({len(wanted)} {_plural(by)} × {steps} steps), and "
            f"the limit is {MAX_ROWS:,}. Choose a smaller region or a shorter range, or summarize the range with "
            "'stat'.",
            None,
        )

    computed = {
        **a.echo(),
        **echo,
        "min_coverage": query.min_coverage,
        **({"interval": query.interval} if query.interval else {}),
        "format": fmt,
    }
    etag = etag_for(request, computed, layermaps.stamp(a, now))
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged

    window, crop = layermaps.window_around(archive, inside)
    rows_in = slice(window.j0 - archive.j0, window.j1 - archive.j0)
    cols_in = slice(window.i0 - archive.i0, window.i1 - archive.i0)
    labels_in = np.where(crop, labels[rows_in, cols_in], 0)
    table = regions.areas(by)
    categories = a.categories
    levels = len(categories) if categories else None
    rows = _Rows(by=by, a=a, wanted=wanted, table=table, min_coverage=query.min_coverage, categories=categories)
    rows.events = a.event is not None
    sources: dict[str, None] = {}
    compute_ms = 0.0
    kinds_seen: list[str | None] = []
    for label, p in periods:
        c = layermaps.compute(p, window, now)
        compute_ms += c.ms
        sources.update(dict.fromkeys(c.sources))
        kinds_seen += c.kinds
        found = c.extra.get("found")  # a first or last day's: 1 found, 0 none in the range, NaN no data
        present = None if found is None else np.isfinite(found)
        for k in range(c.values.shape[0]):
            stats = regions.area_stats(c.values[k], labels_in, len(table), levels=levels, present=present)
            when = label if a.stat is not None else c.steps[k]
            rows.add(stats, when=when, kind=None if a.stat is not None else c.kinds[k])

    warnings = a.warnings
    if rows.below:
        warnings.append(
            f"{rows.below} of the {len(wanted)} {_plural(by)} have less than {query.min_coverage:g}% of their land "
            f"with data here, so their statistics are empty (null). Lower 'min_coverage' to include them."
        )
    summary_meta: dict[str, Any] = {
        "regions": len(wanted),
        "rows": rows.count,
        "below_coverage": rows.below,
        "kinds": {kind or "missing": kinds_seen.count(kind) for kind in dict.fromkeys(kinds_seen)},
        **({"stat": a.stat} if a.stat else {}),
    }
    first, last = a.first, a.last
    result = Result(
        request=computed,
        summary=summary_meta,
        sources=list(sources),
        warnings=warnings,
        etag=etag,
        filename=f"agweather-{a.layer.id}-by-{by}-{first:%Y%m%d}" + (f"-{last:%Y%m%d}" if last != first else ""),
        formats=FORMATS,
        timings={"compute": compute_ms},
    )
    result.columns = rows.columns(time_axis=a.layer.time_axis, interval=query.interval)
    result.timings["read_and_shape"] = (time.perf_counter() - started) * 1000 - compute_ms
    return respond(request, result)


def _plural(by: str) -> str:
    return "counties" if by == "county" else "states"


def _periods(a: LayerAsk, interval: str | None) -> list[tuple[str | None, LayerAsk]]:
    """The request's one period, or with `interval=month` each calendar month of its range, each a `LayerAsk`."""
    if interval is None:
        return [(None, a)]
    if a.roll is not None:
        raise ApiError(
            "conflict",
            "'roll' summarizes one window of days, so it can't go with 'interval=month'. Leave out one of them.",
            "interval",
        )
    if a.stat is None or a.first == a.last:
        raise ApiError(
            "not_applicable",
            "'interval=month' summarizes each month of a range, so it needs a range ('start' and 'end') and a "
            "statistic ('stat', 'count', 'first' or 'last').",
            "interval",
        )
    if a.layer.time_axis != "day" or (a.model is not None and (a.model.season is not None or a.model.projected)):
        raise ApiError(
            "not_applicable",
            f"'interval=month' is for daily layers, and {a.label} isn't one. Ask for each month's range instead.",
            "interval",
        )
    found = []
    month = date(a.first.year, a.first.month, 1)
    while month <= a.last:
        following = (month + timedelta(days=32)).replace(day=1)
        first, last = max(a.first, month), min(a.last, following - timedelta(days=1))
        found.append((f"{month:%Y-%m}", replace(a, first=first, last=last)))
        month = following
    return found


class _Rows:
    """The table's columns, built a step at a time: per step, a row for each wanted region."""

    def __init__(self, *, by, a: LayerAsk, wanted, table, min_coverage, categories):
        self.by, self.a, self.wanted, self.table = by, a, wanted, table
        self.min_coverage, self.categories = min_coverage, categories
        self.when: list[Any] = []
        self.kinds: list[str | None] = []
        self.with_data: list[int] = []
        self.none: list[int] = []
        self.events = False
        self.shown: list[bool] = []  # statistics given (coverage at or above the threshold)
        self.stats: dict[str, list[float]] = {"mean": [], "min": [], "max": []}
        self.levels: list[np.ndarray] = []
        self.below = 0  # regions under the threshold in any step (counted once each)
        self._below: set[int] = set()

    @property
    def count(self) -> int:
        return len(self.with_data)

    def add(self, stats: regions.AreaStats, *, when, kind) -> None:
        for k in self.wanted:
            area = self.table[k]
            assert area is not None
            n = int(stats.with_data[k])
            shown = area.cells > 0 and n > 0 and n * 100 >= self.min_coverage * area.cells
            if not shown and k not in self._below:
                self._below.add(k)
                self.below += 1
            self.when.append(when)
            self.kinds.append(kind)
            self.with_data.append(n)
            self.none.append(int(stats.none[k]))
            self.shown.append(shown)
            for name in self.stats:
                self.stats[name].append(float(getattr(stats, name)[k]) if shown else np.nan)
            if stats.levels is not None:
                self.levels.append(stats.levels[k] * (100 / n) if shown else np.full(stats.levels.shape[1], np.nan))

    def columns(self, *, time_axis: str, interval: str | None) -> list[Column]:
        repeat = self.count // max(1, len(self.wanted))
        areas = [self.table[k] for k in self.wanted] * repeat
        cells = np.array([a.cells for a in areas if a is not None])
        with np.errstate(invalid="ignore", divide="ignore"):
            coverage = np.where(cells > 0, np.array(self.with_data) * 100 / cells, np.nan)
        out = [
            Column(name="fips", values=[a.fips for a in areas if a is not None]),
            Column(name="name", values=[a.name for a in areas if a is not None]),
        ]
        if self.by == "county":
            out.append(Column(name="state", values=[a.state for a in areas if a is not None]))
        if self.a.stat is None and time_axis != "none":  # elevation and freeze dates have no time
            out.append(Column(name="time" if time_axis == "hour" else "date", values=self.when))
            out.append(Column(name="kind", values=self.kinds))
        elif interval == "month":
            out.append(Column(name="month", values=self.when))
        out += [
            Column(
                name="area", values=np.array([a.land_m2 / 1e6 for a in areas if a is not None]), unit="km2", step=2.59
            ),
            Column(name="cells", values=cells.tolist()),
            Column(name="cells_with_data", values=self.with_data),
            *([Column(name="cells_none", values=self.none)] if self.events else []),
            Column(name="coverage", values=np.round(coverage, 1), unit="percent", step=0.1),
            Column(name="complete", values=[bool(c >= 100) for c in np.nan_to_num(coverage)]),
        ]
        if self.categories is not None:
            shares = np.array(self.levels).reshape(len(self.with_data), len(self.categories))
            for j, level in enumerate(self.categories):
                out.append(
                    Column(name=f"pct_{_slug(level)}", values=np.round(shares[:, j], 1), unit="percent", step=0.1)
                )
            highest = self.stats["max"]
            out.append(Column(name="highest", values=[None if v != v else self.categories[round(v)] for v in highest]))
            return out
        a = self.a
        for name, values in self.stats.items():
            if a.unit == "date":  # a first or last day's (D78): ISO dates, the mean rounded to a day
                out.append(
                    Column(name=name, values=[None if v != v else to_date(round(v)).isoformat() for v in values])
                )
            else:
                variable = a.layer.variable or a.layer.id
                out.append(Column(name=name, values=np.array(values), unit=a.unit, step=a.step, variable=variable))
        return out


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text.lower()).strip("_")
