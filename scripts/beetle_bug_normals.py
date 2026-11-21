"""Common asparagus beetle, corn rootworm and tarnished plant bug on AgWeather's 1996–2025 normals at Arlington, Hancock
and Rhinelander (part H, H4 and H5).

Each event's degree days from the model's own curves (a share of a generation entered, a stage's peak, a share of a
stage left, a window's edges), then the day the normal running total (`/api/v2/climate/normals`, the model's
degree-day setting, from January 1) reaches it. A typical-year calendar, not a forecast: a normal total is the average
of 30 years' totals day by day. Also the ratios behind tarnished plant bug's converted sums: June to August degree days
above 52 °F over those above 46.2 and 49.6 °F (single sine).

    uv run app/manage.py shell < scripts/beetle_bug_normals.py
"""

import csv
import io

import numpy as np
from django.test import Client

from agmodels.insects import common_asparagus_beetle, corn_rootworm, tarnished_plant_bug
from agmodels.phenology import DD_STEP, DerivedStage, Insect, LifeStage, curves, dd_grid, generation_densities

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
client = Client(HTTP_HOST="localhost")
X = dd_grid()


def normal_totals(lat: float, lng: float, setting: str) -> dict[str, float]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": "2026-01-01", "end": "2026-12-31", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return {row["date"][5:]: float(row[column]) for row in rows}


def date_of(totals: dict[str, float], dd: float) -> str:
    return next((day for day, total in totals.items() if total >= dd), "–")


def entered(insect: Insect, generation: int, fraction: float) -> float:
    """Degree days at which a fraction of the first life stage's generation has entered it."""
    first = insect.life_stages[0]
    assert isinstance(first, LifeStage)
    done = [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=first)]
    return float(np.interp(fraction, done[generation - 1], X))


def peaks(insect: Insect, key: str, count: int = 4) -> list[float]:
    a = curves(insect)[f"activity_{key}"]
    k = np.flatnonzero((a[1:-1] > a[:-2]) & (a[1:-1] >= a[2:]) & (a[1:-1] > 0.05)) + 1
    return [float(X[i]) for i in k][:count]


def left(insect: Insect, key: str, fraction: float) -> float:
    return float(X[np.argmax(curves(insect)[f"generations_{key}"] >= fraction)])


def windows(insect: Insect) -> list[tuple[float, float]]:
    out = []
    for key, table in curves(insect).items():
        if key.startswith("window_"):
            edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
            out += [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True) if X[a] < 3000]
    return out


def events(insect: Insect, generations: int) -> dict[str, float | tuple[float, float]]:
    first = insect.life_stages[0]
    out: dict[str, float | tuple[float, float]] = {}
    for g in range(1, generations + 1):
        for f in (0.1, 0.5, 0.9):
            out[f"{first.label}, generation {g}, {f:.0%}"] = entered(insect, g, f)
    for s in insect.life_stages:
        if isinstance(s, DerivedStage):
            out[f"{s.label}, first generation, 50 % in"] = entered(insect, 1, 0.5) + s.lag
            out[f"{s.label}, first generation, 50 % out"] = left(insect, s.key, 0.5)
        for n, p in enumerate(peaks(insect, s.key), start=1):
            out[f"{s.label}, peak {n}"] = p
    for n, w in enumerate(windows(insect), start=1):
        out[f"Window {n}"] = w
    return out


MODELS = (
    (common_asparagus_beetle.INSECT, "modified_50_86", 3),
    (corn_rootworm.INSECT, "sine_52", 1),
    (tarnished_plant_bug.INSECT, "sine_52", 4),
)

for insect, setting, generations in MODELS:
    totals = {p: normal_totals(*ll, setting) for p, ll in PLACES.items()}
    print(f"\n{insect.id} ({setting}, from {insect.biofix})")
    print("| Event | DD | " + " | ".join(PLACES) + " |")
    print("| --- | --- | " + " | ".join("---" for _ in PLACES) + " |")
    for name, dd in events(insect, generations).items():
        if isinstance(dd, tuple):
            cells = [f"{date_of(totals[p], dd[0])} to {date_of(totals[p], dd[1])}" for p in PLACES]
            print(f"| {name} | {dd[0]:.0f}–{dd[1]:.0f} | " + " | ".join(cells) + " |")
        else:
            print(f"| {name} | {dd:.0f} | " + " | ".join(date_of(totals[p], dd) for p in PLACES) + " |")
    for day in ("09-15", "10-15"):
        print(f"| Normal total, {day} | | " + " | ".join(f"{totals[p][day]:.0f}" for p in PLACES) + " |")

print("\nUW–Madison's 1,300 DD50 (modified 50/86 °F) for corn rootworm beetles, and degree days above 52 °F that day")
for p, ll in PLACES.items():
    modified, sine = normal_totals(*ll, "modified_50_86"), normal_totals(*ll, "sine_52")
    day = date_of(modified, 1300)
    print(f"{p}: {day}, {sine[day]:.0f}")

print("\nJune to August degree days above 52 °F over those above 46.2 and 49.6 °F (single sine)")
ratios = {46.2: [], 49.6: []}
for p, ll in PLACES.items():
    at52 = normal_totals(*ll, "sine_52")
    for base in ratios:
        other = normal_totals(*ll, f"sine_{base:g}")
        ratios[base].append((at52["08-31"] - at52["05-31"]) / (other["08-31"] - other["05-31"]))
    print(p, " ".join(f"{b:g}: {r[-1]:.3f}" for b, r in ratios.items()))
print("mean", " ".join(f"{b:g}: {np.mean(r):.3f}" for b, r in ratios.items()))
