"""Japanese beetle, mint root borer, mint flea beetle and squash vine borer on AgWeather's 1996–2025 normals at
Arlington, Hancock and Rhinelander (part H, H5).

Each event's degree days from the model's own curves (a share of a stage entered or left, a stage's peak, or a
window's edges), then the day the normal running total (`/api/v2/climate/normals`, the model's degree-day setting,
from its biofix) reaches it. A typical-year calendar, not a forecast: a normal total is the average of 30 years'
totals day by day.

    uv run app/manage.py shell < scripts/specialty_insect_normals.py
"""

import csv
import io

import numpy as np
from django.test import Client

from agmodels.insects import japanese_beetle, mint_flea_beetle, mint_root_borer, squash_vine_borer
from agmodels.phenology import DD_STEP, DerivedStage, Insect, LifeStage, curves, dd_grid, generation_densities

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
client = Client(HTTP_HOST="localhost")
X = dd_grid()


def normal_totals(lat: float, lng: float, setting: str, start: str) -> list[tuple[str, float]]:
    r = client.get("/api/v2/climate/normals", {"lat": lat, "lng": lng, "dd": setting, "start": f"2026-{start}", "end": "2026-12-31", "format": "csv"})  # fmt: skip
    assert r.status_code == 200, r.content[:400]
    rows = list(csv.DictReader(io.StringIO("\n".join(x for x in r.content.decode().splitlines() if x and not x.startswith("#")))))  # fmt: skip
    column = next(k for k in rows[0] if k.endswith("_cum"))
    return [(row["date"], float(row[column])) for row in rows]


def entered(insect: Insect, label: str) -> np.ndarray:
    """The share of a stage's individuals that have entered it, on the degree-day grid."""
    stage = next(s for s in insect.life_stages if s.label == label)
    if isinstance(stage, LifeStage):
        return np.cumsum(generation_densities(insect=insect, stage=stage)[0]) * DD_STEP
    assert isinstance(stage, DerivedStage)
    return np.interp(X - stage.lag, X, entered(insect, stage.follows), left=0)


def left(insect: Insect, label: str) -> np.ndarray:
    stage = next(s for s in insect.life_stages if s.label == label)
    assert isinstance(stage, DerivedStage)
    return np.interp(X - stage.duration, X, entered(insect, label), left=0)


def at(share: np.ndarray, fraction: float) -> float:
    return float(np.interp(fraction, share, X))


def peak(insect: Insect, label: str) -> float:
    key = next(s.key for s in insect.life_stages if s.label == label)
    return float(X[np.argmax(curves(insect)[f"activity_{key}"])])


def windows(insect: Insect) -> list[tuple[float, float]]:
    out = []
    for key, table in curves(insect).items():
        if key.startswith("window_"):
            edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
            out += [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True)]
    return out


def date_of(totals: list[tuple[str, float]], dd: float) -> str:
    for day, total in totals:
        if total >= dd:
            return day[5:]
    return "–"


JB, MRB, MFB, SVB = (m.INSECT for m in (japanese_beetle, mint_root_borer, mint_flea_beetle, squash_vine_borer))
MODELS: tuple[tuple[Insect, str, dict[str, float | tuple[float, float]]], ...] = (
    (
        JB,
        "sine_50_92",
        {
            "first beetles, 2 %": at(entered(JB, "Adult beetles"), 0.02),
            "10 %": at(entered(JB, "Adult beetles"), 0.1),
            "half, 50 %": at(entered(JB, "Adult beetles"), 0.5),
            "90 %": at(entered(JB, "Adult beetles"), 0.9),
            "end of main activity, 94 %": at(entered(JB, "Adult beetles"), 0.94),
            "scouting window": windows(JB)[0],
        },
    ),
    (
        MRB,
        "sine_50",
        {
            "first moths, 2 %": at(entered(MRB, "Moth flight"), 0.02),
            "moth flight peak": peak(MRB, "Moth flight"),
            "moths 90 %": at(entered(MRB, "Moth flight"), 0.9),
            "larvae, half hatched": at(entered(MRB, "Larvae in roots"), 0.5),
            "larvae, most in roots (peak)": peak(MRB, "Larvae in roots"),
            "5 % in winter chambers": at(left(MRB, "Larvae in roots"), 0.05),
            "half in winter chambers": at(left(MRB, "Larvae in roots"), 0.5),
            "moth window": windows(MRB)[0],
        },
    ),
    (
        MFB,
        "sine_41",
        {
            "hatch begins, 2 %": at(entered(MFB, "Egg hatch"), 0.02),
            "larval feeding peak": peak(MFB, "Larval feeding"),
            "first larvae leave rhizomes, 2 %": at(left(MFB, "Larval feeding"), 0.02),
            "adults begin, 2 %": at(entered(MFB, "Adult emergence"), 0.02),
            "adults half emerged": at(entered(MFB, "Adult emergence"), 0.5),
            "adult feeding peak": peak(MFB, "Adult feeding"),
            "sweep window": windows(MFB)[0],
        },
    ),
    (
        SVB,
        "modified_50_86",
        {
            "first moths, 5 %": at(entered(SVB, "Moth flight and egg laying"), 0.05),
            "half the moths": at(entered(SVB, "Moth flight and egg laying"), 0.5),
            "75 %": at(entered(SVB, "Moth flight and egg laying"), 0.75),
            "95 %": at(entered(SVB, "Moth flight and egg laying"), 0.95),
            "larvae in vines, peak": peak(SVB, "Larvae in vines"),
            "half the larvae out of the vines": at(left(SVB, "Larvae in vines"), 0.5),
            "protection window": windows(SVB)[0],
        },
    ),
)

for insect, setting, events in MODELS:
    totals = {p: normal_totals(*ll, setting, insect.biofix) for p, ll in PLACES.items()}
    print(f"\n{insect.id} ({setting}, from {insect.biofix})")
    print("| Event | DD | " + " | ".join(PLACES) + " |")
    print("| --- | --- | " + " | ".join("---" for _ in PLACES) + " |")
    for name, dd in events.items():
        if isinstance(dd, tuple):
            cells = [f"{date_of(totals[p], dd[0])} to {date_of(totals[p], dd[1])}" for p in PLACES]
            print(f"| {name} | {dd[0]:.0f}–{dd[1]:.0f} | " + " | ".join(cells) + " |")
        else:
            print(f"| {name} | {dd:.0f} | " + " | ".join(date_of(totals[p], dd) for p in PLACES) + " |")
    print("| Normal total, October 15 | | " + " | ".join(f"{dict(totals[p])['2026-10-15']:.0f}" for p in PLACES) + " |")
