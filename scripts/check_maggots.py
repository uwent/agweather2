"""The root maggots (agmodels `cabbage-maggot`, `onion-maggot`, `seedcorn-maggot`) against NEWA's on the same weather
(`docs/plans/models.md` part H, H1).

For every complete station-season in tmp/newa/hours/ (scripts/fetch_newa.py), NEWA's maggot models
(scripts/newa_reference.py: the simple average above 40 °F from January 1, or 3.9 °C for seedcorn maggot, and the
first day reaching each event of NEWA's tables) against ours on the station's daily max and min, and ours on the
archive at the station's cell (what the map shows). Ours: the first day each curve reaches a share of a generation
(`generations_adult_flight` ≥ n − 1 + share). For cabbage maggot, also the days the station's single sine above
43 °F reaches 290 and 365 (Eckenrode and Chapman 1972's Wisconsin spring emergence) and the DD43 between our spring
and first summer peaks (their generation: 1,176), with the days by which their generation would put the summer peak later;
the DD40 their 1,176 DD43 spans from our spring peak, and again from there (what their generation is at our base); and
how many station-seasons reach a fourth flight's first flies (5 %) by October 15 (the model shows a fourth flight since version 0.5, ended partway by fall freezes).

    uv run python scripts/check_maggots.py   # writes docs/validation/models/<id>/newa.md for each
"""

import argparse
import json
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import (
    CABBAGE_MAGGOT,
    CACHE,
    ONION_MAGGOT,
    SEEDCORN_MAGGOT_C,
    Day,
    load_hours,
    maggot,
    make_days,
)

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels import runner
from agmodels.degree_days import degree_days_sine
from agmodels.insects import cabbage_maggot, onion_maggot, seedcorn_maggot
from agmodels.phenology import DD_STEP, Insect, PhenologyModel, dd_grid, generation_densities

# NEWA's events and the share of our generation each is compared with (generation, share of it)
CABBAGE = {"first emergence": (1, 0.059), "25%": (1, 0.25), "spring peak": (1, 0.5), "75%": (1, 0.75), "95%": (1, 0.95), "first generation peak": (2, 0.5), "second generation peak": (3, 0.5), "third generation peak": (4, 0.5)}  # fmt: skip
ONION = {"first emergence": (1, 0.05), "spring peak": (1, 0.5), "first generation first": (2, 0.05), "first generation peak": (2, 0.5), "second generation first": (3, 0.05), "second generation peak": (3, 0.5)}  # fmt: skip
SEEDCORN = {"first emergence": (1, 0.0), "emergence complete": (1, 0.5)}


def ours(insect: Insect, lo_c: np.ndarray, hi_c: np.ndarray, year: int, latitude: float) -> dict:
    model = PhenologyModel(insect=insect, summary="")
    days = [date(year, 1, 1) + timedelta(days=k) for k in range(len(lo_c))]
    good = np.isfinite(lo_c) & np.isfinite(hi_c)
    context = runner._context(days, latitude)
    inputs = {"air_temperature_min": np.where(good, lo_c, -20.0), "air_temperature_max": np.where(good, hi_c, -20.0)}
    return model.outputs(inputs | {k: context[k] for k in model.SPEC.context})


def first(mask) -> int | None:
    mask = np.nan_to_num(np.asarray(mask, dtype=float)) > 0
    return int(np.argmax(mask)) if mask.any() else None


def our_events(out: dict, events: dict[str, tuple[int, float]]) -> dict[str, int | None]:
    done = out["generations_adult_flight"]
    found = {}
    for name, (generation, share) in events.items():
        if share == 0.0:  # the curve's start: the first day with any flight
            found[name] = first(out["activity_adult_flight"] > 0)
        else:
            found[name] = first(done >= generation - 1 + share)
    return found


def fmt(year: int, k: int | None) -> str:
    return "–" if k is None else f"{date(year, 1, 1) + timedelta(days=k):%b %-d}"


def station_seasons():
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    for path in sorted((CACHE / "hours").glob("*.json")):
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        if year >= 2026:
            continue
        days = make_days(load_hours(path))
        if len(days) < 290:
            continue
        yield stations[sid], year, days


def celsius(days: list[Day]) -> tuple[np.ndarray, np.ndarray]:
    lo = np.array([(d.mint - 32) / 1.8 if np.isfinite(d.mint) else np.nan for d in days])
    hi = np.array([(d.maxt - 32) / 1.8 if np.isfinite(d.maxt) else np.nan for d in days])
    return lo, hi


def summarize(lines: list[str], diffs: dict[str, list[int]], title: str) -> None:
    lines += ["", f"{title} (days, ours − NEWA's: median, 10th–90th percentile, range, n):", ""]
    for key, values in diffs.items():
        if values:
            v = np.array(values)
            lines.append(
                f"- {key}: {np.median(v):+.0f} ({np.percentile(v, 10):+.0f} to {np.percentile(v, 90):+.0f}; {v.min():+d} to {v.max():+d}), n = {len(v)}"
            )


def part(
    *, lines: list[str], data: Path, insect: Insect, table: dict, events: dict, base: float, celsius_dd: bool
) -> None:
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    names = list(events)
    lines += [
        "",
        f"## {insect.name}",
        "",
        "Each cell: NEWA / ours on the station's days / ours on the archive at the station's cell.",
        *(
            [
                "",
                "NEWA's generation peaks are matched with ours in order, so its third generation peak (its fourth flight) is set beside our fourth flight's 50 %.",
            ]
            if insect.id == "cabbage-maggot"
            else []
        ),
        "",
        "<!-- prettier-ignore -->",
        "| Station | Year | " + " | ".join(names) + " |",
        "| --- | --- | " + " | ".join("---" for _ in names) + " |",
    ]
    station_diffs: dict[str, list[int]] = {n: [] for n in names}
    grid_diffs: dict[str, list[int]] = {n: [] for n in names}
    e_and_c: dict[str, list[float]] = {"first 290 DD43 − ours 5.9 %": [], "first 365 DD43 − ours 5.9 %": [], "DD43 between our spring and first summer peaks": [], "days from our first summer peak to 1,176 DD43 after our spring peak": [], "DD40 from our spring peak to 1,176 DD43 after it": [], "DD40 over the next 1,176 DD43": []}  # fmt: skip
    fourth_first = fourth_flight_start(insect) if insect.id == "cabbage-maggot" else None
    reached: list[bool] = []
    for station, year, days in station_seasons():
        lo, hi = celsius(days)
        newa = maggot(days, table, base=base, celsius=celsius_dd)["events"]
        mine = our_events(ours(insect, lo, hi, year, station["lat"]), events)
        cell = NDFD.cell_of(station["lat"], station["lon"])
        grid: dict[str, int | None] = {}
        if cell is not None:
            if year not in stores:
                stores[year] = GridStore.open(data, DAILY, year, temps)
            g_lo, g_hi = (stores[year].read_point(n, *cell) for n in ("air_temperature_min", "air_temperature_max"))
            grid = our_events(ours(insect, g_lo, g_hi, year, station["lat"]), events)
        cells = [f"{fmt(year, newa[n])} / {fmt(year, mine[n])} / {fmt(year, grid.get(n))}" for n in names]
        lines.append(f"| {station['name']} | {year} | " + " | ".join(cells) + " |")
        print(lines[-1], flush=True)
        for n in names:
            if newa[n] is not None and mine[n] is not None:
                station_diffs[n].append(mine[n] - newa[n])
            if newa[n] is not None and grid.get(n) is not None:
                grid_diffs[n].append(grid[n] - newa[n])  # type: ignore[operator]
        if insect.id == "cabbage-maggot":
            good = np.isfinite(lo) & np.isfinite(hi)
            dd43 = np.cumsum(
                np.where(
                    good,
                    degree_days_sine(
                        np.where(good, lo, 0) * 1.8 + 32, np.where(good, hi, 0) * 1.8 + 32, base=43, upper=None
                    ),
                    0,
                )
            )
            ours_first = mine["first emergence"]
            for target in (290, 365):
                k = first(dd43 >= target)
                if k is not None and ours_first is not None:
                    e_and_c[f"first {target} DD43 − ours 5.9 %"].append(k - ours_first)
            a, b = mine["spring peak"], mine["first generation peak"]
            if a is not None and b is not None:
                e_and_c["DD43 between our spring and first summer peaks"].append(float(dd43[b] - dd43[a]))
                k = first(dd43 >= dd43[a] + 1176)
                if k is not None:
                    e_and_c["days from our first summer peak to 1,176 DD43 after our spring peak"].append(k - b)
            dd40 = np.cumsum(np.where(good, (np.where(good, lo + hi, 0) / 2 * 1.8 + 32 - 40).clip(min=0), 0))
            if a is not None:
                k = first(dd43 >= dd43[a] + 1176)
                if k is not None:
                    e_and_c["DD40 from our spring peak to 1,176 DD43 after it"].append(float(dd40[k] - dd40[a]))
                    k2 = first(dd43 >= dd43[k] + 1176)
                    if k2 is not None:
                        e_and_c["DD40 over the next 1,176 DD43"].append(float(dd40[k2] - dd40[k]))
            october_15 = (date(year, 10, 15) - date(year, 1, 1)).days
            reached.append(bool(dd40[min(october_15, len(dd40) - 1)] >= fourth_first))
    summarize(lines, station_diffs, "Ours on the station's days against NEWA")
    summarize(lines, grid_diffs, "Ours on the archive at the station's cell against NEWA on the station")
    if insect.id == "cabbage-maggot":
        lines += ["", "Against Eckenrode and Chapman 1972's Wisconsin numbers, on the station's days (single sine above 43 °F, no upper, from January 1):", ""]  # fmt: skip
        for key, values in e_and_c.items():
            v = np.array(values)
            lines.append(
                f"- {key}: median {np.median(v):+.0f}, 10th–90th percentile {np.percentile(v, 10):+.0f} to {np.percentile(v, 90):+.0f}, n = {len(v)}"
            )
        lines.append(
            f"- station-seasons whose DD40 reaches a fourth flight's first flies ({fourth_first:.0f}, 5 %) by October 15: {sum(reached)} of {len(reached)}"
        )


def fourth_flight_start(insect: Insect) -> float:
    """The degree days at which a fourth flight's first flies (5 %) come (the model shows four flights since version 0.5)."""
    uncapped = replace(insect, max_generations=4)
    densities = generation_densities(insect=uncapped, stage=uncapped.life_stages[0])
    return float(np.interp(0.05, np.cumsum(densities[3]) * DD_STEP, dd_grid()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models", help="each model's table goes in <out>/<id>/newa.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    data = Path(args.data)
    for insect, table, events, base, celsius_dd in (
        (cabbage_maggot.INSECT, CABBAGE_MAGGOT, CABBAGE, 40, False),
        (onion_maggot.INSECT, ONION_MAGGOT, ONION, 40, False),
        (seedcorn_maggot.INSECT, SEEDCORN_MAGGOT_C, SEEDCORN, 3.9, True),
    ):
        lines = [
            f"# {insect.name}: ours against NEWA's on the same weather",
            "",
            "Written by `scripts/check_maggots.py`. NEWA: `scripts/newa_reference.py`'s reading of its maggot pages (the simple average above 40 °F, or 3.9 °C for seedcorn maggot as deployed, from January 1; an event the first day the total reaches it). Ours: the first day a flight curve reaches the share of a generation NEWA's event stands for (cabbage maggot's first emergence at 5.9 %, onion maggot's at 5 %, each peak at 50 %; seedcorn maggot's first emergence against our flight's first day, and NEWA's 'emergence complete' against our 50 %). Station days are NEWA's on the local clock; the archive's are CST. Wisconsin NEWA stations, 2024 and 2025.",
        ]
        part(lines=lines, data=data, insect=insect, table=table, events=events, base=base, celsius_dd=celsius_dd)
        out = Path(args.out) / insect.id / "newa.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n")
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
