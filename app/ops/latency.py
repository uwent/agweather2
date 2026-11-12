"""Latency checks against PLAN.md §3's targets (Phase 5 H): the requests that must be fast, timed in process.

Each case is one request the frontend or a caller makes. A map is timed as its first tile, which computes the
whole map (the frontend's first view of it), then as the same tile again (kept); a point request is timed first
and then repeated, since a point is read afresh each time. `manage.py latency` runs them on the real archive;
`test_latency` runs them on the fixture archive with a generous bound, so the cases keep working and a large
regression (a map recomputed per tile) fails CI.
"""

import logging
import math
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

from django.test import Client

TILE_ZOOM = 6  # a state fills a screen of zoom 6 tiles
SITE_STEPS = tuple(round(-0.9 + 0.2 * k, 2) for k in range(10))  # degrees of longitude either side of the point
SITES = 5 * len(SITE_STEPS)  # a grid of sites around the point, as many as `points=` takes (a feed's worst case)


@dataclass(kw_only=True, frozen=True)
class Case:
    name: str
    target_ms: float
    path: str  # under /api/v2, with its query
    judged_on: str = "first"  # "first": the first request (a map's compute) or "repeat": the median of the repeats


@dataclass(kw_only=True, frozen=True)
class Timing:
    case: Case
    status: int
    first_ms: float
    repeat_ms: float  # median of the repeats
    nbytes: int

    @property
    def judged_ms(self) -> float:
        return self.first_ms if self.case.judged_on == "first" else self.repeat_ms

    @property
    def met(self) -> bool:
        return self.status == 200 and self.judged_ms <= self.case.target_ms


def tile_of(lat: float, lng: float, zoom: int = TILE_ZOOM) -> tuple[int, int, int]:
    """The web-mercator tile (z, x, y) holding a point."""
    n = 2**zoom
    x = int((lng + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return zoom, x, y


def cases(
    *,
    lat: float,
    lng: float,
    map_day: date,
    season_start: date,
    last_day: date,
    models: tuple[str, ...],
    spread: float = 1.0,
    period: str = "last30",
) -> list[Case]:
    """§3's paths: a risk map (a day and a week's maximum) per model, a custom degree-day map from `season_start`,
    climate maps (a degree-day departure, a month's normal) and a point's normals, of `period` (D86), a point's hourly
    season, and every model at a point through the forecast; and one model at 50 sites around the
    point, `spread` times ±0.4° by ±0.9° (the sites' feed, Phase 6 B; 2 s is its own target, not §3's)."""
    z, x, y = tile_of(lat, lng)
    tile = f"{z}/{x}/{y}.png"
    week = date.fromordinal(map_day.toordinal() - 6)
    found = []
    for model in models:
        found.append(Case(name=f"risk map, {model}, a day", target_ms=300, path=f"/tiles/{model}/{map_day}/{tile}"))
        found.append(
            Case(
                name=f"risk map, {model}, a week's maximum",
                target_ms=300,
                path=f"/tiles/{model}/{week}..{map_day}/{tile}?stat=max",
            )
        )
    found.append(
        Case(
            name="custom degree-day map, season to date",
            target_ms=2000,
            # sine 48/86: no running total is kept for it, so the season is computed from each day's min and max
            path=f"/tiles/degree_days/{season_start}..{last_day}/{tile}?stat=sum&dd=sine_48_86",
        )
    )
    month = date.fromordinal(map_day.toordinal() - 29)
    found.append(
        Case(
            name="degree-day departure from normal, season to date",
            target_ms=300,
            # D86: the running totals' change less the stored normal's (two reads of each)
            path=f"/tiles/degree_days/{season_start}..{last_day}/{tile}?stat=sum&dd=modified_50_86&climate=departure&period={period}",
        )
    )
    found.append(
        Case(
            name="normal map, a month's mean maximum",
            target_ms=300,
            path=f"/tiles/air_temperature_max/{month}..{map_day}/{tile}?stat=mean&climate=normal&period={period}",
        )
    )
    found.append(
        Case(
            name="heat days against normal, a month",
            target_ms=300,
            # D88: the month's count less the stored running count's change
            path=f"/tiles/air_temperature_max/{month}..{map_day}/{tile}?count=days_above_90&climate=departure&period={period}",
        )
    )
    point = urlencode({"lat": lat, "lng": lng})
    found.append(
        Case(
            name="point, 30-year normals with degree days",
            target_ms=1000,
            path=f"/climate/normals?{point}&dd=modified_50_86&percentiles=10,90&period={period}",
        )
    )
    found.append(
        Case(
            name="point, hourly season",
            target_ms=300,
            path=f"/weather/hourly?{point}&start={season_start}T01:00Z&end={last_day}T23:00Z&forecast=false",
            judged_on="repeat",
        )
    )
    found.append(
        Case(
            name="point, every model through the forecast",
            target_ms=1000,
            path=f"/models/run?{point}&models=all",
            judged_on="repeat",
        )
    )
    rows = (-0.4, -0.2, 0.0, 0.2, 0.4)  # within the box around Madison (outside, Open-Meteo: ~1.7 s each)
    sites = ";".join(f"{lat + spread * dy:.4f},{lng + spread * dx:.4f}" for dy in rows for dx in SITE_STEPS)
    found.append(
        Case(
            name=f"{SITES} sites, one model through the forecast",
            target_ms=2000,
            path=f"/models/{models[0]}/run?{urlencode({'points': sites, 'start': season_start})}",
            judged_on="repeat",
        )
    )
    return found


def measure(case: Case, repeats: int = 5, client: Client | None = None) -> Timing:
    """The first request's time, then the median of `repeats` more (none sends an ETag back)."""
    client = client or Client(HTTP_HOST="localhost")
    url = f"/api/v2{case.path}"

    def timed() -> tuple[float, int, int]:
        started = time.perf_counter()
        response = client.get(url)
        return (time.perf_counter() - started) * 1000, response.status_code, len(response.content)

    first_ms, status, nbytes = timed()
    again = [timed()[0] for _ in range(repeats)]
    return Timing(
        case=case,
        status=status,
        first_ms=first_ms,
        repeat_ms=statistics.median(again) if again else first_ms,
        nbytes=nbytes,
    )


def warm_up(*, lat: float, lng: float, day: date) -> float:
    """Load the code, open the stores and build the tables a server process builds once (ms taken): a weather tile
    and a crop's map (each cell's county, ~0.3 s over Wisconsin) on another day, and a point, so the first case's
    time is its own work, not the process's start."""
    z, x, y = tile_of(lat, lng)
    client = Client(HTTP_HOST="localhost")
    started = time.perf_counter()
    from api.layermaps import warm_kernels  # as a server process does at start (`config.asgi`)

    warm_kernels()
    client.get(f"/api/v2/tiles/air_temperature_max/{day}/{z}/{x}/{y}.png")
    client.get(f"/api/v2/tiles/corn-stages/{day}/{z}/{x}/{y}.png")
    client.get(f"/api/v2/weather/daily?lat={lat}&lng={lng}&date={day}")
    return (time.perf_counter() - started) * 1000


def run(found: list[Case], repeats: int = 5, on_timing: Callable[[Timing], None] | None = None) -> list[Timing]:
    client = Client(HTTP_HOST="localhost")
    timings = []
    requests = logging.getLogger("django.request")
    level = requests.level
    requests.setLevel(logging.CRITICAL)  # a 4xx is reported with its case, not logged per request
    try:
        for case in found:
            timing = measure(case, repeats=repeats, client=client)
            timings.append(timing)
            if on_timing is not None:
                on_timing(timing)
    finally:
        requests.setLevel(level)
    return timings


def describe(t: Timing) -> str:
    """The timing and its verdict, without the case's name."""
    verdict = "met" if t.met else (f"failed (status {t.status})" if t.status != 200 else "over")
    return (
        f"first {t.first_ms:,.0f} ms, then {t.repeat_ms:,.0f} ms "
        f"(target {t.case.target_ms:,.0f} ms on the {t.case.judged_on} request: {verdict}; {t.nbytes:,} bytes)"
    )
