"""Codling moth (agmodels `codling-moth`) on real weather (models plan B4, step 4).

1. NEWA on the same weather: for every complete station-season in tmp/newa/hours/ (scripts/fetch_newa.py), NEWA's
   codling moth (scripts/newa_reference.py: DD50 without an upper from January 1, first catch at 404, its management
   guide after each biofix) against ours on the station's daily max and min, twice: with our first catch estimated
   from the station's latitude, and with NEWA's first catch day as the trap date, so the difference splits into the
   default first catch and the curves.
2. Ours on the archive at the station's cell (what the map shows), estimated first catch.
3. Across Wisconsin, 2016–2025 on the archive: each event's mean date, the second generation's size class, and the
   estimated first catch against apple bloom by `apple-stages` (NEWA: first catch "usually coincides with first
   bloom of 'Red Delicious'").

    uv run python scripts/check_codling_moth.py [--out docs/validation/models/codling-moth/newa-and-wisconsin.md]
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import CACHE, codling_moth, load_hours, make_days

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels import runner
from agmodels.insects.codling_moth import INSECT
from agmodels.models import apple_stages
from agmodels.phenology import PhenologyModel

MODEL = PhenologyModel(insect=INSECT, summary="")
WINDOW = "window_protect_fruit_during_egg_hatch"
SITES = {  # approximate locations of orchards or orchard towns
    "Gays Mills": (43.318, -90.851),
    "Baraboo": (43.47, -89.74),
    "Verona (WMARS)": (43.060, -89.532),
    "Fort Atkinson": (42.928, -88.837),
    "Eau Claire": (44.81, -91.50),
    "Sturgeon Bay (PARS)": (44.880, -87.337),
    "Bayfield": (46.81, -90.82),
}


def ours(lo_c: np.ndarray, hi_c: np.ndarray, year: int, latitude: float, biofix_index: int = 0) -> dict:
    days = [date(year, 1, 1) + timedelta(days=k) for k in range(len(lo_c))]
    good = np.isfinite(lo_c) & np.isfinite(hi_c)
    context = runner._context(days, latitude)
    inputs = {"air_temperature_min": np.where(good, lo_c, -20.0), "air_temperature_max": np.where(good, hi_c, -20.0)}
    return MODEL.outputs(inputs | {k: context[k] for k in MODEL.SPEC.context}, biofix_index=biofix_index)


def events(out: dict) -> dict[str, int | None]:
    """Each event's first day index (None if not reached)."""

    def first(mask) -> int | None:
        mask = np.nan_to_num(np.asarray(mask, dtype=float)) > 0
        return int(np.argmax(mask)) if mask.any() else None

    window = np.nan_to_num(out[WINDOW]) > 0
    edges = np.flatnonzero(np.diff(np.r_[0, window.astype(int)]) == 1)
    closes = np.flatnonzero(np.diff(np.r_[window.astype(int), 0]) == -1)
    estimated = out["first_catch_estimated"]
    catch = first(out["dd_after_first_catch"] > 0)
    if np.nanmax(estimated) == 0:  # a trap date: its own day
        catch = first(np.isfinite(out["dd_total"]))
    return {
        "first catch": catch,
        "window opens": int(edges[0]) if len(edges) else None,
        "half hatched": first(out["generations_egg_hatch"] >= 0.5),
        "window closes": int(closes[0]) if len(closes) else None,
        "second flight": first(out["generations_adult_flight"] >= 1.05),
        "second window opens": int(edges[1]) if len(edges) > 1 else None,
        "size": None
        if np.all(np.isnan(out["second_generation_size"]))
        else int(np.nanmax(out["second_generation_size"])),
    }


def fmt(year: int, k: int | None) -> str:
    return "–" if k is None else f"{date(year, 1, 1) + timedelta(days=k):%b %-d}"


def diff(a: int | None, b: int | None) -> str:
    return "–" if a is None or b is None else f"{a - b:+d}"


def daily_at(store: GridStore, cell: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    return tuple(store.read_point(n, *cell) for n in ("air_temperature_min", "air_temperature_max"))  # type: ignore[return-value]


def newa_part(data: Path, lines: list[str]) -> None:
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    lines += [
        "## 1–2. NEWA's codling moth against ours, on the station's hours and the archive's",
        "",
        "Dates. First catch: NEWA's default (404 DD50 from January 1) / ours estimated from latitude on the station's days / ours on the archive at the station's cell. Hatch: NEWA's first spray (250 DD after its first catch) / our window's opening with NEWA's first catch as the trap date / ours estimated (station) / ours estimated (grid). Second hatch: NEWA's (its second first catch, 1501 after the first) / ours with NEWA's first catch / ours estimated (station). Size: the second generation's class on the station's days and the grid's.",
        "",
        "| Station | Year | First catch NEWA / station / grid | First hatch NEWA / same catch / station / grid | Second hatch NEWA / same catch / station | Size station / grid |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    diffs: dict[str, list[int]] = {
        k: [] for k in ("catch station", "catch grid", "hatch same", "hatch station", "hatch grid", "second same")
    }
    for path in sorted((CACHE / "hours").glob("*.json")):
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        if year >= 2026:
            continue
        days = make_days(load_hours(path))
        if len(days) < 290:
            continue
        station = stations[sid]
        lo = np.array([(d.mint - 32) / 1.8 if np.isfinite(d.mint) else np.nan for d in days])
        hi = np.array([(d.maxt - 32) / 1.8 if np.isfinite(d.maxt) else np.nan for d in days])
        newa = codling_moth(days)["events"]
        if newa["first catch"] is None:
            continue
        station_est = events(ours(lo, hi, year, station["lat"]))
        same = events(ours(lo, hi, year, station["lat"], biofix_index=newa["first catch"]))
        cell = NDFD.cell_of(station["lat"], station["lon"])
        grid = None
        if cell is not None:
            if year not in stores:
                stores[year] = GridStore.open(data, DAILY, year, temps)
            g_lo, g_hi = daily_at(stores[year], cell)
            grid = events(ours(g_lo, g_hi, year, station["lat"]))
        g = grid or {}
        lines.append(
            f"| {station['name']} | {year} | {fmt(year, newa['first catch'])} / {fmt(year, station_est['first catch'])} / {fmt(year, g.get('first catch'))} | {fmt(year, newa['first spray'])} / {fmt(year, same['window opens'])} / {fmt(year, station_est['window opens'])} / {fmt(year, g.get('window opens'))} | {fmt(year, newa['second hatch'])} / {fmt(year, same['second window opens'])} / {fmt(year, station_est['second window opens'])} | {station_est['size'] or '–'} / {g.get('size') or '–'} |"
        )
        print(lines[-1], flush=True)
        for key, a, b in (
            ("catch station", station_est["first catch"], newa["first catch"]),
            ("catch grid", g.get("first catch"), newa["first catch"]),
            ("hatch same", same["window opens"], newa["first spray"]),
            ("hatch station", station_est["window opens"], newa["first spray"]),
            ("hatch grid", g.get("window opens"), newa["first spray"]),
            ("second same", same["second window opens"], newa["second hatch"]),
        ):
            if a is not None and b is not None:
                diffs[key].append(a - b)
    lines += ["", "Ours − NEWA's, days (median, 10th–90th percentile, n):", ""]
    labels = {
        "catch station": "First catch, ours estimated on the station's days",
        "catch grid": "First catch, ours estimated on the grid",
        "hatch same": "First hatch window against NEWA's first spray, the same first catch",
        "hatch station": "First hatch window, ours estimated (station)",
        "hatch grid": "First hatch window, ours estimated (grid)",
        "second same": "Second hatch, the same first catch",
    }
    for key, values in diffs.items():
        if values:
            v = np.array(values)
            lines.append(
                f"- {labels[key]}: {np.median(v):+.0f} ({np.percentile(v, 10):+.0f} to {np.percentile(v, 90):+.0f}), n = {len(v)}"
            )


def wisconsin_part(data: Path, lines: list[str]) -> None:
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    names = ["first catch", "window opens", "half hatched", "window closes", "second flight", "second window opens"]
    lines += [
        "",
        "## 3. Across Wisconsin on the archive, 2016–2025 (estimated first catch)",
        "",
        "Mean date of each event (years reaching it, if not all), the second generation's size class in each year, and first catch less the day `apple-stages` reaches bloom (346 DD43), mean (range).",
        "",
        "| Site | " + " | ".join(n.capitalize() for n in names) + " | Size classes | First catch − bloom, days |",
        "| --- | " + " | ".join("---" for _ in names) + " | --- | --- |",
    ]
    for site, (lat, lon) in SITES.items():
        cell = NDFD.cell_of(lat, lon)
        assert cell is not None
        found: dict[str, list[int]] = {n: [] for n in names}
        sizes, versus_bloom = [], []
        for year in range(2016, 2026):
            lo, hi = daily_at(GridStore.open(data, DAILY, year, temps), cell)
            e = events(ours(lo, hi, year, lat))
            for n in names:
                if e[n] is not None:
                    found[n].append(e[n])
            sizes.append(e["size"])
            good = np.isfinite(lo) & np.isfinite(hi)
            stage = apple_stages.outputs(
                {"air_temperature_min": np.where(good, lo, -20.0), "air_temperature_max": np.where(good, hi, -20.0)}
            )["stage"]
            bloom = int(np.argmax(stage >= 5))
            if e["first catch"] is not None:
                versus_bloom.append(e["first catch"] - bloom)
        cells = []
        for n in names:
            v = found[n]
            text = fmt(2021, round(float(np.mean(v)))) if v else "–"
            cells.append(text + ("" if len(v) == 10 else f" ({len(v)}/10)"))
        b = np.array(versus_bloom)
        lines.append(
            f"| {site} | "
            + " | ".join(cells)
            + f" | {', '.join(str(s or '–') for s in sizes)} | {b.mean():+.1f} ({b.min():+d} to {b.max():+d}) |"
        )
        print(lines[-1], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/codling-moth/newa-and-wisconsin.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    lines = [
        "# Codling moth: ours against NEWA's, and across Wisconsin",
        "",
        "Written by `scripts/check_codling_moth.py`. Ours: WSU's curves from first catch, degree days 50/86 °F single sine, first catch by Jones et al. 2013's latitude equation unless a trap date is given. NEWA: `scripts/newa_reference.py`'s reading of its page (DD50 without an upper, first catch at 404, first spray 250 after it, second first catch 1501 after it). Station days are NEWA's on the local clock; the archive's are CST.",
        "",
    ]
    newa_part(Path(args.data), lines)
    wisconsin_part(Path(args.data), lines)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
