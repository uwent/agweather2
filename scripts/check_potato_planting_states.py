"""Potato planting rules outside Wisconsin: each rule fitted at UW Vegetable Pathology's seven places and applied to
potato areas of the states USDA NASS's Usual Planting and Harvesting Dates (Agricultural Handbook 628, 2010) lists
in the launch area (Michigan, Minnesota, North Dakota, Ohio), and to two southern places with no NASS dates.

The development archive covers Wisconsin only, so this reads Open-Meteo's historical API at the places (ERA5-Land's
0–7 cm soil temperature and ERA5's daily air minimum and maximum, 2016–2025, January 1 to July 31; 20 requests,
cached in tmp/potato-states/). Rules, each a place's statistic over the 10 years:

- soil degree days above 0 °C from January 1 (the mean daily total over the years, summed) reaching a threshold;
- air degree days above 0 °C (daily mean temperature), the same;
- the median last spring freeze at 28 °F and at 32 °F, plus days (`agdata.potatoplanting`'s rule; the grid reads it
  from the 30-year normal instead).

NASS's dates are crop progress, state-wide, 1990–2009: "most active" is 15–85% planted. Veg Path's early, mid and
late are its tiers, which come earlier than NASS's percentages in Wisconsin, so the check is whether a rule keeps the
states' spread NASS gives (the residuals' spread across the states), not their level.

uv run python scripts/check_potato_planting_states.py [--quiet]   # OPEN_METEO_API_KEY from the environment, if set
"""

import argparse
import csv
import json
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.potatoplanting import OFFSETS
from agdata.progress import Reporter

REPO = Path(__file__).resolve().parent.parent
DATES = REPO / "docs" / "validation" / "data" / "vegpath-potato-planting" / "dates.csv"
CACHE = REPO / "tmp" / "potato-states"
YEARS = range(2016, 2026)
DAYS = 212
TIERS = ("early", "mid", "late")
# name: ((lat, lng), NASS's begin, most active start and end, end; None without)
OTHER = {
    "Montcalm Co., MI": ((43.35, -85.15), ("04-16", "04-24", "05-31", "06-08")),
    "Sherburne Co., MN (sands)": ((45.45, -93.85), ("04-20", "04-25", "05-30", "06-10")),
    "Clay Co., MN (Red River Valley)": ((47.0, -96.5), ("04-20", "04-25", "05-30", "06-10")),
    "Walsh Co., ND": ((48.35, -97.6), ("04-28", "05-05", "05-30", "06-06")),
    "Wayne Co., OH": ((40.8, -81.9), ("04-10", "04-20", "05-28", "06-08")),
    "Fayette Co., KY": ((38.05, -84.5), None),
    "Jackson Co., IL": ((37.75, -89.3), None),
}


def doy(text: str) -> int:
    """Day of the year from 1 (a non-leap year)."""
    return date.fromisoformat(text).timetuple().tm_yday


def md(day: float) -> str:
    return "--" if np.isnan(day) else (date(2025, 1, 1) + timedelta(days=int(day) - 1)).strftime("%b %d")


def fetched(report: Reporter, places: dict[str, tuple[float, float]]) -> dict:
    saved = CACHE / "series.json"
    if saved.exists():
        return json.loads(saved.read_text())
    client = OpenMeteoPoints(endpoint="historical", cache_dir=CACHE, api_key=os.environ.get("OPEN_METEO_API_KEY"))
    names, out = list(places), {n: {} for n in places}
    for k, year in enumerate(YEARS):
        report.detail(f"{year} ==> GET Open-Meteo historical, {len(names)} places")
        soil = client.daily(
            [places[n] for n in names],
            date(year, 1, 1),
            date(year, 7, 31),
            ["soil_temperature_0_to_7cm_mean"],
            model="era5_land",
        )
        air = client.daily(
            [places[n] for n in names],
            date(year, 1, 1),
            date(year, 7, 31),
            ["temperature_2m_min", "temperature_2m_max"],
        )
        for n, s, a in zip(names, soil, air, strict=True):
            out[n][str(year)] = {
                key: [np.nan if v is None else v for v in block[key]][:DAYS]
                for block, key in (
                    (s, "soil_temperature_0_to_7cm_mean"),
                    (a, "temperature_2m_min"),
                    (a, "temperature_2m_max"),
                )
            }
        report.progress("years", k + 1, len(YEARS))
    CACHE.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps(out))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    with report.activate():
        rows = list(csv.DictReader(DATES.open()))
        places = {r["location"]: (float(r["lat"]), float(r["lng"])) for r in rows} | {n: v[0] for n, v in OTHER.items()}
        data = fetched(report, places)

        def series(n: str, key: str) -> np.ndarray:
            return np.array([data[n][str(y)][key] for y in YEARS], float)

        def degree_days(n: str, kind: str) -> np.ndarray:
            t = (
                series(n, "soil_temperature_0_to_7cm_mean")
                if kind == "soil"
                else (series(n, "temperature_2m_min") + series(n, "temperature_2m_max")) / 2
            )
            return np.cumsum(np.nanmean(np.maximum(t, 0.0), axis=0))

        def last_freeze(n: str, limit_c: float) -> float:
            tmin = series(n, "temperature_2m_min")[:, :181]  # through June
            return float(
                np.median([(np.nonzero(row <= limit_c)[0].max() + 1) if (row <= limit_c).any() else 0 for row in tmin])
            )

        rules = {}
        for kind in ("soil", "air"):
            curves = {n: degree_days(n, kind) for n in places}
            need = {
                t: float(
                    np.median([curves[r["location"]][doy(r["planting_date"]) - 1] for r in rows if r["planting"] == t])
                )
                for t in TIERS
            }
            rules[f"{kind} degree days above 0 °C from January 1"] = {
                n: [float(np.argmax(curves[n] >= need[t]) + 1) if curves[n][-1] >= need[t] else np.nan for t in TIERS]
                for n in places
            }
        for f, limit in ((28, -2.2), (32, 0.0)):
            freeze = {n: last_freeze(n, limit) for n in places}
            offset = {
                t: float(
                    np.median([doy(r["planting_date"]) - freeze[r["location"]] for r in rows if r["planting"] == t])
                )
                for t in TIERS
            }
            rules[f"last {f} °F spring freeze + days ({', '.join(f'{v:+.0f}' for v in offset.values())})"] = {
                n: [freeze[n] + offset[t] for t in TIERS] for n in places
            }
        report.step(f"potatoplanting.OFFSETS (fitted on the 30-year normal at the grid's cells): {OFFSETS}")
        for name, found in rules.items():
            report.step(name)
            residuals = []
            for n, (_, nass) in OTHER.items():
                est = found[n]
                if nass is None:
                    report.step(f"  {n}: {', '.join(md(v) for v in est)}; no NASS dates")
                    continue
                middle = (doy(f"2025-{nass[1]}") + doy(f"2025-{nass[2]}")) / 2
                residuals.append(est[1] - middle)
                report.step(
                    f"  {n}: {', '.join(md(v) for v in est)}; NASS most active {nass[1]} to {nass[2]} (mid {md(middle)}), mid {est[1] - middle:+.0f} d"
                )
            r = np.array(residuals)
            report.step(
                f"  mid against NASS's middle: mean {r.mean():+.0f} d, spread across the states (SD) {r.std():.1f} d"
            )
    report.finish("checked")


if __name__ == "__main__":
    main()
