"""Apple stages (agmodels `apple-stages`) on real weather: against NEWA on the same station hours, and against the
stages UW's fruit program and Wisconsin growers observed (models-plan B1, step 4).

1. NEWA: for every station-season in tmp/newa/hours/ (scripts/fetch_newa.py), each stage's first day by our model
   (Baskerville–Emin's sine on NEWA's own daily max and min) against NEWA's (its sine, as scripts/newa_reference.py
   repeats it). Same weather, so only the sine differs.
2. Observations (tmp/references/apple/notes/wi-stage-observations.md, transcribed below): the model on the
   archive's days at each site's cell, the stage it gives on the date observed, and how many days its window for
   the observed stage misses that date by (+ the model is late, − early, 0 inside).

    uv run python scripts/check_apple_stages.py
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import CACHE, accumulate, load_hours, make_days, sine_dd_newa

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_sine
from agmodels.models import apple_stages as apple

CODES = [s.code for s in apple.STAGES]
BEFORE_BLOOM = ("-", "ST", "GT", "HIG", "TC", "P")

SITES = {  # approximate locations
    "WMARS (Verona)": (43.060, -89.532),
    "PARS (Sturgeon Bay)": (44.880, -87.337),
    "Sunrise Orchards (Gays Mills)": (43.318, -90.851),
    "Warm Belly Farm (Fort Atkinson)": (42.928, -88.837),
    "Gwenyn Hill Farm (Delafield)": (43.050, -88.390),
    "Blue Roof Orchard (Belmont)": (42.732, -90.333),
}

# (site, date, cultivars, stage as written, stages it can be in NEWA's list). "Southern Wisconsin" photos in the
# 2025–2026 reports are WMARS's (the June reports say so); the earlier ones are taken as WMARS too, and flagged.
OBSERVATIONS = [
    ("Sunrise Orchards (Gays Mills)", "2023-05-05", "orchard", "first blossoms opening", ("P", "B")),
    ("Sunrise Orchards (Gays Mills)", "2023-05-09", "orchard", "75% bloom", ("B",)),
    ("Sunrise Orchards (Gays Mills)", "2023-05-11", "orchard", "100% bloom", ("B",)),
    ("Sunrise Orchards (Gays Mills)", "2024-04-16", "orchard", "no blossoms open", BEFORE_BLOOM),
    ("Sunrise Orchards (Gays Mills)", "2024-04-25", "orchard", "a few blossoms open", ("P", "B")),
    ("Sunrise Orchards (Gays Mills)", "2024-04-29", "orchard", "1/3 open", ("B",)),
    ("Sunrise Orchards (Gays Mills)", "2024-04-30", "orchard", "75% bloom", ("B",)),
    ("Sunrise Orchards (Gays Mills)", "2025-04-21", "orchard", "no blossoms open", BEFORE_BLOOM),
    ("Sunrise Orchards (Gays Mills)", "2025-05-02", "orchard", "on the verge of opening", ("P",)),
    ("Sunrise Orchards (Gays Mills)", "2025-05-07", "orchard", "75% bloom", ("B",)),
    ("WMARS (Verona)", "2023-04-24", "Zestar, Paula Red*", "pink", ("P",)),
    ("WMARS (Verona)", "2024-04-11", "Zestar*", "late tight cluster", ("TC",)),
    ("WMARS (Verona)", "2024-04-11", "Liberty, Gala*", "green tip to half-inch green", ("GT", "HIG")),
    ("WMARS (Verona)", "2024-04-25", "Zestar", "king bloom", ("B",)),
    ("WMARS (Verona)", "2024-04-25", "Liberty, Gala*", "pink", ("P",)),
    ("WMARS (Verona)", "2025-04-10", "early cultivars*", "green tip", ("GT",)),
    ("WMARS (Verona)", "2025-04-10", "later cultivars*", "silver tip", ("ST",)),
    ("WMARS (Verona)", "2025-04-24", "Zestar, Ida Red*", "first pink", ("P",)),
    ("WMARS (Verona)", "2025-04-24", "Fuji, Honeycrisp, McIntosh*", "half-inch green to tight cluster", ("HIG", "TC")),
    ("WMARS (Verona)", "2025-05-07", "Gala, McIntosh*", "full bloom", ("B",)),
    ("WMARS (Verona)", "2025-05-07", "Honeycrisp*", "king bloom", ("B",)),
    ("WMARS (Verona)", "2025-05-07", "Zestar*", "early petal fall", ("B", "PF")),
    ("WMARS (Verona)", "2025-05-16", "not stated", "petal fall", ("PF",)),
    ("WMARS (Verona)", "2026-04-22", "Zestar, Ida Red*", "king bloom", ("B",)),
    ("WMARS (Verona)", "2026-04-22", "Fuji, Honeycrisp, McIntosh*", "tight cluster to early pink", ("TC", "P")),
    ("WMARS (Verona)", "2026-04-30", "most cultivars", "full bloom", ("B",)),
    ("WMARS (Verona)", "2026-05-20", "Honeycrisp, McIntosh", "fruit 6–8 mm", ("PF", "FS")),
    ("PARS (Sturgeon Bay)", "2023-05-18", "not stated", "entering king bloom", ("P", "B")),
    ("PARS (Sturgeon Bay)", "2024-04-11", "early cultivars", "green tip", ("GT",)),
    ("PARS (Sturgeon Bay)", "2024-04-11", "later cultivars", "silver tip", ("ST",)),
    ("PARS (Sturgeon Bay)", "2024-04-25", "apples", "tight cluster", ("TC",)),
    ("PARS (Sturgeon Bay)", "2024-05-09", "by variety", "pink to king bloom", ("P", "B")),
    ("PARS (Sturgeon Bay)", "2024-05-16", "by variety", "king to full bloom", ("B",)),
    ("PARS (Sturgeon Bay)", "2025-05-08", "Door County", "green tip to tight cluster", ("GT", "HIG", "TC")),
    ("PARS (Sturgeon Bay)", "2025-05-14", "Door County", "tight cluster to pink", ("TC", "P")),
    ("PARS (Sturgeon Bay)", "2025-05-21", "by variety", "late pink to full bloom", ("P", "B")),
    ("PARS (Sturgeon Bay)", "2025-05-28", "by variety", "full bloom to petal fall", ("B", "PF")),
    ("PARS (Sturgeon Bay)", "2025-06-05", "Door County", "petal fall", ("PF",)),
    ("PARS (Sturgeon Bay)", "2026-05-20", "Zestar", "king bloom", ("B",)),
    ("PARS (Sturgeon Bay)", "2026-05-20", "Honeycrisp, Liberty", "pink", ("P",)),
    ("PARS (Sturgeon Bay)", "2026-06-03", "Zestar", "petal fall", ("PF",)),
    ("PARS (Sturgeon Bay)", "2026-06-03", "Honeycrisp, Snow Sweet", "early petal fall", ("B", "PF")),
    ("PARS (Sturgeon Bay)", "2026-06-11", "Door County", "early fruit set", ("PF", "FS")),
    ("Warm Belly Farm (Fort Atkinson)", "2026-05-18", "most varieties", "petal fall, fruit 5–10 mm", ("PF",)),
    ("Gwenyn Hill Farm (Delafield)", "2025-04-21", "apples", "green tip", ("GT",)),
    ("Gwenyn Hill Farm (Delafield)", "2025-05-05", "apples", "full pink to king bloom", ("P", "B")),
    ("Blue Roof Orchard (Belmont)", "2024-05-13", "most varieties", "past petal fall", ("PF", "FS")),
]


def code_of(stage: float) -> str:
    return "-" if stage < 0 else CODES[int(stage)]


def newa_part():
    print("## Same weather: our sine against NEWA's, first day of each stage (ours − NEWA's, days)\n")
    differences: dict[str, list[int]] = {c: [] for c in CODES}
    files = sorted((CACHE / "hours").glob("*.json"))
    for path in files:
        days = make_days(load_hours(path))
        if len(days) < 180:
            continue
        lo = np.array([d.mint for d in days])
        hi = np.array([d.maxt for d in days])
        good = np.isfinite(lo) & np.isfinite(hi)
        ours = np.cumsum(
            np.where(good, degree_days_sine(np.where(good, lo, 50), np.where(good, hi, 50), apple.BASE_F), 0)
        )
        newa = np.array([total for _, total in accumulate(days, base=43, start=0, method=sine_dd_newa)], dtype=float)
        for k, code in enumerate(CODES):
            a, b = np.argmax(ours >= apple.THRESHOLDS[k]), np.argmax(newa >= apple.THRESHOLDS[k])
            if ours[-1] >= apple.THRESHOLDS[k] and newa[-1] >= apple.THRESHOLDS[k]:
                differences[code].append(int(a - b))
    n = len(differences["GT"])
    print(f"{n} station-seasons\n")
    print("| Stage | −2 | −1 | 0 | +1 | +2 |\n| --- | --- | --- | --- | --- | --- |")
    for code, diffs in differences.items():
        counts = [sum(1 for d in diffs if d == k) for k in (-2, -1, 0, 1, 2)]
        print(f"| {code} | " + " | ".join(map(str, counts)) + " |")


def observed_part(data: Path):
    print("\n## Observed stages against the model at each site's cell (archive)\n")
    print(
        "| Site | Date | Cultivars | Observed | DD43 | Model stage | Days off |\n| --- | --- | --- | --- | --- | --- | --- |"
    )
    runs: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    offs = []
    for site, when, cultivars, written, allowed in OBSERVATIONS:
        day = date.fromisoformat(when)
        key = (site, day.year)
        if key not in runs:
            cell = NDFD.cell_of(*SITES[site])
            assert cell is not None
            store = GridStore.open(
                data, DAILY, day.year, [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
            )
            lo, hi = (store.read_point(name, *cell) for name in ("air_temperature_min", "air_temperature_max"))
            out = apple.outputs({"air_temperature_min": lo, "air_temperature_max": hi})
            runs[key] = (out["stage"], out["dd_total"])
        stage, total = runs[key]
        index = day.timetuple().tm_yday - 1
        inside = np.array([code_of(s) in allowed for s in stage])
        if inside[index]:
            off = 0
        elif inside.any():
            where = np.flatnonzero(inside)
            off = int(where[0] - index) if where[0] > index else -int(index - where[-1])
        else:
            off = None
        offs.append(off)
        print(
            f"| {site} | {when} | {cultivars} | {written} | {total[index]:.0f} | {code_of(stage[index])} | {'' if off is None else f'{off:+d}' if off else '0'} |"
        )
    known = [o for o in offs if o is not None]
    print(
        f"\n{len(known)} observations: {sum(1 for o in known if o == 0)} inside the model's window, {sum(1 for o in known if abs(o) <= 3)} within 3 days; model late on {sum(1 for o in known if o > 0)}, early on {sum(1 for o in known if o < 0)}; mean {np.mean(known):+.1f} days, median {np.median(known):+.0f}."
    )
    print('\n* "southern Wisconsin" in the report, taken as WMARS.')


def main():
    newa_part()
    observed_part(Path("data"))


if __name__ == "__main__":
    main()
