"""The root maggots' events on AgWeather's 1996–2025 normals at Arlington, Hancock and Rhinelander (part H, H1).

Each event's degree days from the model's own curves (the share of a generation's flight, or a window's edges), then
the day the normal running total (`/api/v2/climate/normals`, the model's degree-day setting, from January 1) reaches
it. A typical-year calendar, not a forecast: a normal total is the average of 30 years' totals day by day.

    uv run app/manage.py shell < scripts/maggot_normals.py
"""

import csv
import io

import numpy as np
from django.test import Client

from agmodels.insects import cabbage_maggot, onion_maggot, seedcorn_maggot
from agmodels.phenology import DD_STEP, curves, dd_grid, generation_densities

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
client = Client(HTTP_HOST="localhost")


def normal_totals(lat: float, lng: float, setting: str) -> list[tuple[str, float]]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": "2026-01-01", "end": "2026-12-31", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return [(row["date"], float(row[column])) for row in rows]


def flight_events(insect, shares: dict[str, tuple[int, float]]) -> dict[str, float]:
    x = dd_grid()
    done = [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=insect.life_stages[0])]
    out = {name: float(np.interp(share, done[g - 1], x)) for name, (g, share) in shares.items() if g <= len(done)}
    for key, table in curves(insect).items():
        if key.startswith("window_"):
            edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
            for n, (a, b) in enumerate(zip(edges[::2], edges[1::2], strict=True)):
                if x[a] > 4500:  # past any Wisconsin season
                    break
                out[f"window {n + 1}"] = (float(x[a]), float(x[b - 1]))  # type: ignore[assignment]
    return out


def date_of(totals: list[tuple[str, float]], dd: float) -> str:
    for day, total in totals:
        if total >= dd:
            return day[5:]
    return "–"


MODELS = (
    (
        cabbage_maggot.INSECT,
        "average_40",
        {
            "first flies (5.9 %)": (1, 0.059),
            "spring 50 %": (1, 0.5),
            "spring 95 %": (1, 0.95),
            "2nd flight 50 %": (2, 0.5),
            "3rd flight 50 %": (3, 0.5),
            "4th flight 50 %": (4, 0.5),
        },
    ),
    (
        onion_maggot.INSECT,
        "average_40",
        {
            "first flies (5 %)": (1, 0.05),
            "spring 50 %": (1, 0.5),
            "spring 95 %": (1, 0.95),
            "2nd flight 5 %": (2, 0.05),
            "2nd flight 50 %": (2, 0.5),
            "3rd flight 50 %": (3, 0.5),
        },
    ),
    (
        seedcorn_maggot.INSECT,
        "average_39_84.2",
        {
            "spring 10 %": (1, 0.1),
            "spring 50 %": (1, 0.5),
            "spring 90 %": (1, 0.9),
            "2nd flight 50 %": (2, 0.5),
            "3rd flight 50 %": (3, 0.5),
        },
    ),
)

for insect, setting, shares in MODELS:
    events = flight_events(insect, shares)
    print(f"\n{insect.id} ({setting})")
    print("| Event | DD | " + " | ".join(PLACES) + " |")
    print("| --- | --- | " + " | ".join("---" for _ in PLACES) + " |")
    totals = {p: normal_totals(*ll, setting) for p, ll in PLACES.items()}
    for name, dd in events.items():
        if isinstance(dd, tuple):
            cells = [f"{date_of(totals[p], dd[0])} to {date_of(totals[p], dd[1])}" for p in PLACES]
            print(f"| {name} | {dd[0]:.0f}–{dd[1]:.0f} | " + " | ".join(cells) + " |")
        else:
            print(f"| {name} | {dd:.0f} | " + " | ".join(date_of(totals[p], dd) for p in PLACES) + " |")
    print("| Normal total, October 15 | | " + " | ".join(f"{dict(totals[p])['2026-10-15']:.0f}" for p in PLACES) + " |")
