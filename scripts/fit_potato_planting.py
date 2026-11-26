"""Fit and compare rules for potato's typical planting dates on the grid (`agdata.potatoplanting`), at UW Vegetable
Pathology's seven Wisconsin places (`docs/validation/data/vegpath-potato-planting/dates.csv`, 120 plantings,
2020–2026), on the archive in DATA_DIR. Results in `docs/validation/models/potato-stages.md`.

Every rule gives a place's early, mid and late dates from a climatological statistic of the place's cell, fitted per
tier as the median over the training rows, and is scored held out by place (each place's dates predicted from the
other six):

- freeze: the cell's median last spring freeze (28 or 32 °F) over a stored normal (`last30`, `last10`), plus days,
  as the cell's own and averaged over the area around it (`agdata.springfreeze`, 50 km, D127; the rule in use);
- soil degree days: the first day the archive's normal running total of 4 cm soil temperature above 0 °C from
  January 1 (the last 10 complete years, each day's mean over the years) reaches a threshold (the 2026-11-03 fit on
  Open-Meteo, here on the archive);
- air degree days: the same on the stored normals of the running degree days above 32 °F (single sine) and 39.2 °F
  (average).

The fitted freeze offsets (all 120 rows, on the area's 28 °F freeze over `last30`) are checked against
`potatoplanting.OFFSETS`. The speckle of each rule's mid date over the normals' area is measured too: the mean over
land cells of the largest difference from a neighbouring cell (the 8 around it), and the share of cells more than 3 days
from one.

uv run python scripts/fit_potato_planting.py [--data-dir data] [--quiet]
"""

import argparse
import csv
from collections.abc import Callable
from datetime import date
from pathlib import Path

import numpy as np

from agdata import normals, potatoplanting, regions, springfreeze
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD, Window
from agdata.progress import Reporter
from agdata.store import DAILY, GridStore

REPO = Path(__file__).resolve().parent.parent
DATES = REPO / "docs" / "validation" / "data" / "vegpath-potato-planting" / "dates.csv"
TIERS = ("early", "mid", "late")
SOIL = "soil_temperature_4cm_mean"
DAYS = 212  # January 1 to July 31
SOIL_YEARS = range(2016, 2026)


def slot_of(text: str) -> int:
    """A date's calendar slot (`climatology.slot`: a leap year's day of year from 0)."""
    d = date.fromisoformat(text)
    return (date(2000, d.month, d.day) - date(2000, 1, 1)).days


def running_first(running: np.ndarray, threshold: float) -> float:
    """The slot the running total (from January 1, slot 0) first reaches `threshold`, NaN if it doesn't."""
    reached = np.nonzero(running >= threshold)[0]
    return float(reached[0]) if len(reached) else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=REPO / "data")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    regions.use_terrain(lambda: args.data_dir)  # open water as the app takes it
    with report.activate():
        rows = list(csv.DictReader(DATES.open()))
        places = {r["location"]: (float(r["lat"]), float(r["lng"])) for r in rows}
        cells = {n: NDFD.cell_of(*ll) for n, ll in places.items()}
        report.step(f"{len(rows)} plantings at {len(places)} places, {DATES.relative_to(REPO)}")

        def single(period: str, name: str) -> dict[str, float]:
            out = {}
            for n, cell in cells.items():
                assert cell is not None
                w = Window(j0=cell[0], j1=cell[0] + 1, i0=cell[1], i1=cell[1] + 1)
                out[n] = float(normals.read_within(args.data_dir, period, name, None, w)[0, 0])
            return out

        def running(period: str, name: str) -> dict[str, np.ndarray]:
            out = {}
            for n, cell in cells.items():
                assert cell is not None
                w = Window(j0=cell[0], j1=cell[0] + 1, i0=cell[1], i1=cell[1] + 1)
                days = [date(2000, 1, 1).toordinal() + k for k in range(DAYS)]
                out[n] = np.array(
                    [
                        normals.read_within(args.data_dir, period, f"{name}/mean", date.fromordinal(d), w)[0, 0]
                        for d in days
                    ]
                )
            report.detail(f"{period} {name}: read at {len(cells)} cells")
            return out

        def soil() -> dict[str, np.ndarray]:
            names = list(cells)
            by_year = []
            for year in SOIL_YEARS:
                store = GridStore.open(args.data_dir, DAILY, year, [DAILY_VARIABLES[SOIL]], read_only=True)
                by_year.append(store.read_cells(SOIL, [c for c in cells.values() if c is not None], 0, DAYS))
                report.progress("soil temperature years", year - SOIL_YEARS[0] + 1, len(SOIL_YEARS))
            mean_dd = np.nanmean([np.maximum(v, 0.0) for v in by_year], axis=0)
            return {n: np.cumsum(mean_dd[:, k]) for k, n in enumerate(names)}

        results: list[tuple[str, np.ndarray, dict[str, float]]] = []

        def score(name: str, predict: Callable[[str, list[dict]], float]) -> None:
            errors, by_place = [], {n: [] for n in places}
            for r in rows:
                train = [o for o in rows if o["location"] != r["location"] and o["planting"] == r["planting"]]
                e = predict(r["location"], train) - slot_of(r["planting_date"])
                errors.append(e)
                by_place[r["location"]].append(e)
            results.append((name, np.array(errors, float), {n: float(np.mean(v)) for n, v in by_place.items()}))

        def offset_rule(stat: dict[str, float]) -> Callable[[str, list[dict]], float]:
            return lambda n, train: (
                round(stat[n])
                + float(np.median([slot_of(o["planting_date"]) - round(stat[o["location"]]) for o in train]))
            )

        def total_rule(curve: dict[str, np.ndarray]) -> Callable[[str, list[dict]], float]:
            return lambda n, train: running_first(
                curve[n], float(np.median([curve[o["location"]][slot_of(o["planting_date"])] for o in train]))
            )

        def area(period: str, name: str) -> dict[str, float]:
            out = {}
            for n, cell in cells.items():
                assert cell is not None
                out[n] = springfreeze.at(args.data_dir, name, *cell, period=period)
            return out

        freeze = {}
        for period in ("last30", "last10"):
            for f in (28, 32):
                name = f"freeze_{f}/spring_p50"
                score(
                    f"{period}: last {f} °F spring freeze (median), the cell's + days",
                    offset_rule(single(period, name)),
                )
                freeze[(period, f)] = area(period, name)
                score(
                    f"{period}: last {f} °F spring freeze (median), over {springfreeze.RADIUS_KM:g} km + days",
                    offset_rule(freeze[(period, f)]),
                )
        score("archive 2016–2025: soil (4 cm) degree days above 0 °C", total_rule(soil()))
        for name, label in (
            ("dd_sine_32", "air degree days above 32 °F (sine)"),
            ("dd_average_39p2", "air degree days above 39.2 °F (average)"),
        ):
            score(f"last30: {label}", total_rule(running("last30", name)))

        report.step("held out by place (days; error = estimate − Veg Path's date)")
        for name, e, by_place in results:
            per = ", ".join(f"{n} {v:+.1f}" for n, v in by_place.items())
            report.step(
                f"{name}: MAE {np.abs(e).mean():.1f}, RMSE {np.sqrt((e**2).mean()):.1f}, bias {e.mean():+.1f}; by place {per}"
            )

        chosen = freeze[("last30", 28)]
        report.step(
            f"last30's median last 28 °F spring freeze over {springfreeze.RADIUS_KM:g} km at each place: "
            + ", ".join(f"{n} {potatoplanting.slot_text(round(v))}" for n, v in chosen.items())
        )
        fitted = {
            t: round(
                float(
                    np.median(
                        [slot_of(r["planting_date"]) - round(chosen[r["location"]]) for r in rows if r["planting"] == t]
                    )
                )
            )
            for t in TIERS
        }
        report.step(f"offsets fitted on every row: {fitted}; potatoplanting.OFFSETS {potatoplanting.OFFSETS}")
        if fitted != potatoplanting.OFFSETS:
            report.warn("the fitted offsets differ from potatoplanting.OFFSETS")
        for t in TIERS:
            mean = {
                n: float(
                    np.mean([slot_of(r["planting_date"]) for r in rows if r["location"] == n and r["planting"] == t])
                )
                for n in places
            }
            report.detail(
                f"{t}: "
                + ", ".join(
                    f"{n} {potatoplanting.slot_text(round(chosen[n]) + fitted[t])} (Veg Path's mean {potatoplanting.slot_text(round(mean[n]))})"
                    for n in places
                )
            )
        speckle(report, args.data_dir)
    report.finish("fitted")


def speckle(report: Reporter, data_dir: Path) -> None:
    """How much the mid planting date jumps between neighbouring land cells over the normals' area, by the cell's own
    freeze and by the area's."""
    w = Window(**(normals.info(data_dir, "last30") or {})["window"])
    land = ~regions.water(w)
    for label, freeze in (
        ("the cell's own freeze", normals.read_within(data_dir, "last30", potatoplanting.FREEZE, None, w)),
        (f"the freeze over {springfreeze.RADIUS_KM:g} km", springfreeze.within(data_dir, potatoplanting.FREEZE, w)),
    ):
        mid = np.where(land, np.round(freeze), np.nan)
        jumps = np.full((8, *mid.shape), np.nan)
        padded = np.pad(mid, 1, constant_values=np.nan)
        k = 0
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                if dj or di:
                    jumps[k] = np.abs(padded[1 + dj : 1 + dj + mid.shape[0], 1 + di : 1 + di + mid.shape[1]] - mid)
                    k += 1
        largest = np.nanmax(np.where(np.isfinite(jumps), jumps, -1.0), axis=0)
        cells = np.isfinite(mid) & (largest >= 0)
        report.step(
            f"speckle by {label}: {int(cells.sum())} land cells, the largest step to a neighbour {largest[cells].mean():.2f} days on average, {100 * (largest[cells] > 3).mean():.1f}% of cells more than 3 days from one, SD of mid dates {np.nanstd(mid):.1f} days"
        )


if __name__ == "__main__":
    main()
