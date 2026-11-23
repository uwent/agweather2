"""What per-generation weights change (part H, round 2): each weighted insect's risk on AgWeather's 1996–2025 normals
at Arlington, Hancock and Rhinelander, with equal generations (version 0.2) and with its weights (0.3).

The normal running total of the model's degree-day setting (`/api/v2/climate/normals`, from the model's biofix), the
risk read off the model's risk curve at each day's total (`agmodels.phenology.risk_curve`), without the fall freeze
factor (a normal season has no freezes of its own). For each peak of the equal-weights risk through October 15: its
date, the risk and its level before and after, and the days at High or above. A typical-year calendar, not a forecast.

    uv run app/manage.py shell < scripts/generation_weights_normals.py
"""

import csv
import io
from dataclasses import replace

import numpy as np
from django.test import Client

from agmodels.insects import cabbage_looper, cabbage_maggot, imported_cabbageworm, onion_maggot, seedcorn_maggot
from agmodels.phenology import RISK_THRESHOLDS, dd_grid, risk_curve
from agmodels.spec import SEVERITY_LEVELS

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
MODELS = (
    (cabbage_maggot.INSECT, "average_40"),
    (onion_maggot.INSECT, "average_40"),
    (seedcorn_maggot.INSECT, "average_39_84.2"),
    (imported_cabbageworm.INSECT, "modified_50_86"),
    (cabbage_looper.INSECT, "sine_50_90"),
)
client = Client(HTTP_HOST="localhost")
X = dd_grid()


def normal_totals(lat: float, lng: float, setting: str, start: str) -> tuple[list[str], np.ndarray]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": f"2026-{start}", "end": "2026-10-15", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return [row["date"] for row in rows], np.array([float(row[column]) for row in rows])


def level(value: float) -> str:
    return SEVERITY_LEVELS[int(np.searchsorted(np.asarray(RISK_THRESHOLDS), value, side="right"))]


def day(text: str) -> str:
    month, d = text[5:7], int(text[8:])
    return f"{['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(month)]} {d}"


for insect, setting in MODELS:
    equal = replace(insect, generation_weights=())
    print(f"\n{insect.id} (weights {insect.generation_weights}; {setting} from {insect.biofix})")
    print("| Place | Peak | Equal generations | Weighted |")
    print("| --- | --- | --- | --- |")
    for place, (lat, lng) in PLACES.items():
        dates, total = normal_totals(lat, lng, setting, insect.biofix)
        before = np.interp(total, X, risk_curve(equal))
        after = np.interp(total, X, risk_curve(insect))
        peaks = [k for k in range(1, len(before) - 1) if before[k] >= before[k - 1] and before[k] > before[k + 1]]
        for k in peaks:
            if before[k] < 0.05:
                continue
            print(
                f"| {place} | {day(dates[k])} | {before[k]:.2f} ({level(before[k])}) | {after[k]:.2f} ({level(after[k])}) |"
            )
        high_before, high_after = int(np.sum(before >= 0.5)), int(np.sum(after >= 0.5))
        print(f"| {place} | days at High or above | {high_before} | {high_after} |")
