"""Imported cabbageworm, cabbage looper and crucifer flea beetle on AgWeather's 1996–2025 normals at Arlington, Hancock
and Rhinelander (part H, H3).

Each event's degree days from the model's own curves (a share of a stage's generation complete, a stage's peak, or a
window's edges), then the day the normal running total (`/api/v2/climate/normals`, the model's degree-day setting,
from its biofix) reaches it. A typical-year calendar, not a forecast: a normal total is the average of 30 years'
totals day by day.

    uv run app/manage.py shell < scripts/cole_pest_normals.py
"""

import csv
import io

import numpy as np
from django.test import Client

from agmodels.insects import cabbage_looper, crucifer_flea_beetle, imported_cabbageworm
from agmodels.phenology import DD_STEP, LifeStage, curves, dd_grid, generation_densities

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
client = Client(HTTP_HOST="localhost")
X = dd_grid()


def normal_totals(lat: float, lng: float, setting: str, start: str) -> list[tuple[str, float]]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": f"2026-{start}", "end": "2026-12-31", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return [(row["date"], float(row[column])) for row in rows]


def share(insect, generation: int, fraction: float) -> float:
    """Degree days at which a fraction of the first life stage's generation has entered it."""
    first = insect.life_stages[0]
    assert isinstance(first, LifeStage)
    done = [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=first)]
    return float(np.interp(fraction, done[generation - 1], X))


def peaks(insect, key: str) -> list[float]:
    """Local maxima of a stage's activity."""
    a = curves(insect)[f"activity_{key}"]
    k = np.flatnonzero((a[1:-1] > a[:-2]) & (a[1:-1] >= a[2:]) & (a[1:-1] > 0.05)) + 1
    return [float(X[i]) for i in k]


def windows(insect) -> list[tuple[float, float]]:
    out = []
    for key, table in curves(insect).items():
        if key.startswith("window_"):
            edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
            out += [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True) if X[a] < 4000]
    return out


def date_of(totals: list[tuple[str, float]], dd: float) -> str:
    for day, total in totals:
        if total >= dd:
            return day[5:]
    return "–"


def events(insect) -> dict[str, float | tuple[float, float]]:
    out: dict[str, float | tuple[float, float]] = {}
    first = insect.life_stages[0]
    for g in (1, 2):
        out[f"{first.label}, gen {g}, 10 %"] = share(insect, g, 0.1)
        out[f"{first.label}, gen {g}, 50 %"] = share(insect, g, 0.5)
    for s in insect.life_stages:
        for n, p in enumerate(peaks(insect, s.key)[:4], start=1):
            out[f"{s.label} peak {n}"] = p
    for n, w in enumerate(windows(insect), start=1):
        out[f"window {n}"] = w
    return out


MODELS = (
    (imported_cabbageworm.INSECT, "modified_50_86"),
    (cabbage_looper.INSECT, "sine_50_90"),
    (crucifer_flea_beetle.INSECT, "modified_50_86"),
)

for insect, setting in MODELS:
    totals = {p: normal_totals(*ll, setting, insect.biofix) for p, ll in PLACES.items()}
    print(f"\n{insect.id} ({setting}, from {insect.biofix})")
    print("| Event | DD | " + " | ".join(PLACES) + " |")
    print("| --- | --- | " + " | ".join("---" for _ in PLACES) + " |")
    for name, dd in events(insect).items():
        if isinstance(dd, tuple):
            cells = [f"{date_of(totals[p], dd[0])} to {date_of(totals[p], dd[1])}" for p in PLACES]
            print(f"| {name} | {dd[0]:.0f}–{dd[1]:.0f} | " + " | ".join(cells) + " |")
        else:
            print(f"| {name} | {dd:.0f} | " + " | ".join(date_of(totals[p], dd) for p in PLACES) + " |")
    print("| Normal total, October 15 | | " + " | ".join(f"{dict(totals[p])['2026-10-15']:.0f}" for p in PLACES) + " |")
