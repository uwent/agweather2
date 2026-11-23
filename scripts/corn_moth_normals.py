"""European corn borer's and corn earworm's events on AgWeather's 1996–2025 normals at Arlington, Hancock and Rhinelander, with Wausau and Marshfield for the corn borer's north (part H, H2).

Each event's degree days from the model's own curves, then the day the normal running total (`/api/v2/climate/normals`,
the model's degree-day setting) reaches it: from January 1 for the corn borer, from the biofix (the normal total less
its value the day before) for corn earworm. A typical-year calendar, not a forecast: a normal total is the average of 30
years' totals day by day.

    uv run app/manage.py shell < scripts/corn_moth_normals.py
"""

import csv
import io
from datetime import date

import numpy as np
from django.test import Client

from agmodels.insects import corn_earworm, european_corn_borer
from agmodels.phenology import curves, dd_grid, form_insect

PLACES = {
    "Arlington": (43.30, -89.35),
    "Hancock": (44.12, -89.53),
    "Rhinelander": (45.64, -89.41),
    "Wausau": (44.95, -89.60),
    "Marshfield": (44.66, -90.17),
}
client = Client(HTTP_HOST="localhost")


def normal_totals(lat: float, lng: float, setting: str) -> list[tuple[str, float]]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": "2026-01-01", "end": "2026-12-31", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return [(row["date"], float(row[column])) for row in rows]


def from_day(totals: list[tuple[str, float]], month_day: str) -> list[tuple[str, float]]:
    k = (date.fromisoformat(f"2026-{month_day}") - date(2026, 1, 1)).days
    before = totals[k - 1][1]
    return [(d, t - before) for d, t in totals[k:]]


def date_of(totals: list[tuple[str, float]], dd: float) -> str:
    for day, total in totals:
        if total >= dd:
            return f"{date.fromisoformat(day):%b %-d}"
    return "–"


def share(table: np.ndarray, value: float) -> float:
    return float(np.interp(value, table, dd_grid()))


def window_edges(insect) -> list[tuple[float, float]]:
    x = dd_grid()
    out = []
    for key, table in curves(insect).items():
        if key.startswith("window_"):
            edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
            out += [(float(x[a]), float(x[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True) if x[a] < 4500]
    return out


def print_table(title: str, events: dict[str, float | tuple[float, float]], totals: dict[str, list[tuple[str, float]]]):
    print(f"\n{title}")
    print("| Event | DD | " + " | ".join(totals) + " |")
    print("| --- | --- | " + " | ".join("---" for _ in totals) + " |")
    for name, dd in events.items():
        if isinstance(dd, tuple):
            cells = [f"{date_of(t, dd[0])} to {date_of(t, dd[1])}" for t in totals.values()]
            print(f"| {name} | {dd[0]:.0f}–{dd[1]:.0f} | " + " | ".join(cells) + " |")
        else:
            print(f"| {name} | {dd:.0f} | " + " | ".join(date_of(t, dd) for t in totals.values()) + " |")


ecb = european_corn_borer.INSECT
t = curves(ecb)
x = dd_grid()
act = t["activity_adult_flight"]
events: dict[str, float | tuple[float, float]] = {
    "spring moths, first (1 %)": share(t["generations_adult_flight"], 0.01),
    "spring flight, 50 %": share(t["generations_adult_flight"], 0.5),
    "spring flight, peak": float(x[np.argmax(np.where(x < 1200, act, 0))]),
    "summer moths, first (1 %)": share(t["generations_adult_flight"], 1.01),
    "summer flight, 50 %": share(t["generations_adult_flight"], 1.5),
    "summer flight, peak": float(x[np.argmax(np.where(x > 1200, act, 0))]),
    "summer flight, 99 %": share(t["generations_adult_flight"], 1.99),
}
for n, edges in enumerate(window_edges(ecb), start=1):
    events[f"treat young larvae, window {n}"] = edges
totals = {p: normal_totals(*ll, "modified_50_86") for p, ll in PLACES.items()}
print_table("european-corn-borer (modified_50_86 from January 1)", events, totals)
print("| Normal total, August 1 | | " + " | ".join(f"{dict(v)['2026-08-01']:.0f}" for v in totals.values()) + " |")
print("| Normal total, October 15 | | " + " | ".join(f"{dict(v)['2026-10-15']:.0f}" for v in totals.values()) + " |")

# The one-flight form (part H, round 2), where the normal total by August 1 is below 1,500
one = form_insect(ecb)
t1 = curves(one)
one_events: dict[str, float | tuple[float, float]] = {
    "one flight, first moths (1 %)": share(t1["generations_adult_flight"], 0.01),
    "one flight, 50 %": share(t1["generations_adult_flight"], 0.5),
    "one flight, peak": float(x[np.argmax(t1["activity_adult_flight"])]),
    "one flight, 99 %": share(t1["generations_adult_flight"], 0.99),
}
for n, edges in enumerate(window_edges(one), start=1):
    one_events[f"treat young larvae, window {n}"] = edges
north = {p: v for p, v in totals.items() if dict(v)["2026-08-01"] < 1500}
print_table("european-corn-borer, one flight (where the normal by August 1 is below 1,500)", one_events, north)

cew = corn_earworm.INSECT
t = curves(cew)
larvae = t["activity_larvae_in_ears"]
cew_events: dict[str, float | tuple[float, float]] = {
    "first larvae in ears (hatch begins)": 73.0,
    "larvae in ears, most (peak activity)": float(x[np.argmax(larvae)]),
    "first larvae leave the ears": 437.0,
    "half the larvae have left": share(t["generations_larvae_in_ears"], 0.5),
    "a generation (moths lay eggs)": 873.0,
}
sine = {p: normal_totals(*ll, "sine_55_92") for p, ll in PLACES.items() if p in ("Arlington", "Hancock", "Rhinelander")}
for start in ("08-15", "08-01"):
    print_table(f"corn-earworm (sine_55_92 from {start})", cew_events, {p: from_day(v, start) for p, v in sine.items()})
    print(
        "| Normal total, October 15 | | "
        + " | ".join(f"{dict(from_day(v, start))['2026-10-15']:.0f}" for v in sine.values())
        + " |"
    )
print(
    "\nlarvae activity >= 0.75 from",
    x[np.argmax(larvae >= 0.75)],
    "to",
    x[len(larvae) - 1 - np.argmax(larvae[::-1] >= 0.75)],
)
