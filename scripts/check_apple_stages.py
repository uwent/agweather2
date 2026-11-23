"""Apple stages (agmodels `apple-stages`) on real weather: against NEWA on the same station hours, and against the
stages UW's fruit program and Wisconsin growers observed (models plan B1, step 4; report:
docs/validation/models/apple-stages.md).

1. NEWA: for every station-season in tmp/newa/hours/ (scripts/fetch_newa.py), each stage's first day by our model
   (Baskerville–Emin's sine on NEWA's own daily max and min) against NEWA's (its sine, as scripts/newa_reference.py
   repeats it). Same weather, so only the sine differs.
2. Observations (docs/validation/data/wi-apple-stages/observations.csv, the rows with stage codes): the model on
   the archive's days at each site's cell, the stage it gives on the date observed, and how many days its window
   for the observed stage misses that date by (+ the model is late, − early, 0 inside).

    uv run python scripts/check_apple_stages.py [--out docs/validation/models/apple-stages/newa-and-observations.md]
"""

import argparse
import csv
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
OBSERVATIONS = Path("docs/validation/data/wi-apple-stages/observations.csv")
EARLY = ("Zestar", "Paula Red", "early cultivars")  # cultivars that bloom before McIntosh, as the sources name them


def code_of(stage: float) -> str:
    return "-" if stage < 0 else CODES[int(stage)]


def newa_part() -> list[str]:
    lines = ["## Same weather: our sine against NEWA's, first day of each stage (ours − NEWA's, days)", ""]
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
    lines += [f"{len(differences['GT'])} station-seasons", ""]
    lines += ["| Stage | −2 | −1 | 0 | +1 | +2 |", "| --- | --- | --- | --- | --- | --- |"]
    for code, diffs in differences.items():
        counts = [sum(1 for d in diffs if d == k) for k in (-2, -1, 0, 1, 2)]
        lines.append(f"| {code} | " + " | ".join(map(str, counts)) + " |")
    return lines


def read_observations(path: Path) -> list[dict[str, str]]:
    """The observations at a located site with the stages they can be in (the others are kept for the record)."""
    with path.open() as f:
        return [row for row in csv.DictReader(f) if row["codes"] and row["lat"]]


def summary(offs: list[int]) -> str:
    n = len(offs)
    return f"{n} observations: {sum(1 for o in offs if o == 0)} inside the model's window, {sum(1 for o in offs if abs(o) <= 3)} within 3 days; model late on {sum(1 for o in offs if o > 0)}, early on {sum(1 for o in offs if o < 0)}; mean {np.mean(offs):+.1f} days, median {np.median(offs):+.1f}."


def observed_part(data: Path, path: Path) -> list[str]:
    lines = ["", "## Observed stages against the model at each site's cell (archive)", ""]
    lines += [
        "| Site | Date | Cultivars | Observed | DD43 | Model stage | Days off |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    runs: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    offs: list[int] = []
    early: list[bool] = []
    for row in read_observations(path):
        site, day, allowed = row["site"], date.fromisoformat(row["date"]), row["codes"].split()
        key = (site, day.year)
        if key not in runs:
            cell = NDFD.cell_of(float(row["lat"]), float(row["lon"]))
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
        else:
            where = np.flatnonzero(inside)
            assert where.size, f"{site} {day}: the model never reaches {allowed}"
            off = int(where[0] - index) if where[0] > index else -int(index - where[-1])
        offs.append(off)
        early.append(any(name in row["cultivars"] for name in EARLY))
        taken = "*" if row["site_as_written"].lower() == "southern wisconsin" else ""
        lines.append(
            f"| {site} | {row['date']} | {row['cultivars']}{taken} | {row['stage_as_written']} ({' '.join(allowed)}) | {total[index]:.0f} | {code_of(stage[index])} | {f'{off:+d}' if off else '0'} |"
        )
    lines += ["", f"All: {summary(offs)}", ""]
    lines.append(
        f"Early cultivars (rows naming {', '.join(EARLY)}): {summary([o for o, e in zip(offs, early, strict=True) if e])}"
    )
    lines += ["", f"The rest: {summary([o for o, e in zip(offs, early, strict=True) if not e])}"]
    lines += ["", '* "southern Wisconsin" in the source, taken as WMARS.']
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/apple-stages/newa-and-observations.md")
    parser.add_argument("--observations", default=str(OBSERVATIONS))
    args = parser.parse_args()
    lines = [
        "# Apple stages: ours against NEWA's, and against observed stages in Wisconsin",
        "",
        "Written by `scripts/check_apple_stages.py`. Ours: degree days base 43 °F by Baskerville–Emin's single sine from January 1, NEWA's stage thresholds. NEWA: the same thresholds on its own sine (`scripts/newa_reference.py`), on the station's daily max and min (local clock). Observations: `docs/validation/data/wi-apple-stages/observations.csv`, against the model on the archive's days (CST) at each site's cell; the stage codes each observation can be in follow it in parentheses (- before silver tip).",
        "",
    ]
    lines += newa_part()
    lines += observed_part(Path("data"), Path(args.observations))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
