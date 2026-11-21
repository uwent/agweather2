"""Alfalfa weevil (agmodels `alfalfa-weevil`) on real weather (docs/models-plan.md part H4).

1. Harcourt 1981's dated peaks: eight stages in four years (Table II, Bay of Quinte, Ontario, 1977–1980) and peak hatch
   at Guelph (Table I), on Open-Meteo's historical daily max and min for each area (ERA5; fetched once into --cache).
   Each stage's peak date by Harcourt's own method (single sine above 9 °C from April 1, his °C·d) and by NEWA's
   (simple average above 48 °F from January 1, NEWA's table), against the observed date.
2. NEWA on the same weather: NEWA's degree days (simple average 48 °F, unrounded, a day without hours as 0) on the
   hours of the Wisconsin NEWA stations (tmp/newa/hours/, scripts/fetch_newa.py) against ours on the same days and on
   the archive at each station's cell: the days NEWA's egg hatch (280), cocooning (600) and adult emergence (815)
   are reached, against our curves' half-way points. The Crop Risk Tool's old table (single sine 48.2/86 °F: egg
   hatch 300, pupae 595, adults 815) too.
3. Typical dates at Arlington, Hancock and Rhinelander on the 1996–2025 normals: the normal running total (each year's
   own, averaged, as /api/v2/climate/normals computes it) reaching each event.

    uv run python scripts/check_alfalfa_weevil.py [--cache DIR] [--out docs/validation/models/alfalfa-weevil/weather.md]
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import CACHE, load_hours, make_days

from agdata import climatology
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_average, degree_days_sine
from agmodels.insects.alfalfa_weevil import INSECT
from agmodels.phenology import curves, dd_grid

STAGES = ("Hatch", "Instar 1", "Instar 2", "Instar 3", "Instar 4", "Cocooning", "Pupa", "Adult emergence")
HARCOURT_C = (155, 176, 218, 260, 306, 335, 403, 454)  # peaks, °C·d above 9 °C from April 1 (Table II)
NEWA_F = (280, 315, 395, 470, 550, 600, 725, 815)  # NEWA's table, °F·d above 48 °F from January 1
# Harcourt 1981, Table II: observed peak dates, Bay of Quinte (Smithfield Experimental Farm's weather)
QUINTE = {
    1977: "05-23 05-25 05-29 06-05 06-11 06-14 06-21 06-27",
    1978: "05-30 06-01 06-06 06-12 06-18 06-21 06-27 07-03",
    1979: "05-29 06-01 06-07 06-11 06-16 06-19 06-28 07-05",
    1980: "05-27 05-30 06-05 06-12 06-20 06-23 06-30 07-05",
}
GUELPH_HATCH = {1977: "05-18", 1978: "05-31", 1979: "06-02", 1980: "05-27"}  # Table I, observed peak hatch
PLACES = {"Bay of Quinte": (44.11, -77.57), "Guelph": (43.54, -80.22)}  # Smithfield; the University Arboretum
SITES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
NORMAL_YEARS = range(1996, 2026)
CRT_STEPS = {"egg hatch": 300, "pupae": 595, "adults": 815}  # the Crop Risk Tool's table, sine 48.2/86 °F


def open_meteo(place: str, cache: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Days, daily min and max (°C) for 1977–1980 at a place, from Open-Meteo's historical API (cached)."""
    path = cache / f"open-meteo-{place.lower().replace(' ', '-')}-1977-1980.json"
    if not path.exists():
        lat, lon = PLACES[place]
        query = urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": "1977-01-01",
                "end_date": "1980-12-31",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "America/Toronto",
            }
        )
        with urllib.request.urlopen(f"https://archive-api.open-meteo.com/v1/archive?{query}", timeout=60) as r:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.read())
    daily = json.loads(path.read_text())["daily"]
    days = np.array([date.fromisoformat(t) for t in daily["time"]])
    lo = np.array([np.nan if v is None else v for v in daily["temperature_2m_min"]], dtype=float)
    hi = np.array([np.nan if v is None else v for v in daily["temperature_2m_max"]], dtype=float)
    return days, lo, hi


def reached(days, total: np.ndarray, threshold: float) -> date | None:
    k = int(np.argmax(total >= threshold))
    return days[k] if total[k] >= threshold else None


def reached_index(total: np.ndarray, threshold: float) -> int | None:
    k = int(np.argmax(total >= threshold))
    return k if total[k] >= threshold else None


def harcourt_part(cache: Path, lines: list[str], report: Reporter) -> None:
    report.step("Harcourt 1981's dated peaks on Open-Meteo's weather for the Bay of Quinte and Guelph, 1977–1980")
    lines += [
        "## 1. Harcourt 1981's dated peaks, on Open-Meteo's historical weather",
        "",
        "Days from the observed peak (Table II, Bay of Quinte; Table I, Guelph's peak hatch) to the day each method's total reaches the stage's peak: Harcourt's own (single sine above 9 °C from April 1, his °C·d), and NEWA's (simple average above 48 °F from January 1, NEWA's table; ours is the same rule, and our curves pass half of egg hatch, cocooning and adult emergence at NEWA's totals). Weather: Open-Meteo's historical daily max and min (ERA5) at the Smithfield farm and Guelph, not the stations Harcourt used. Harcourt's own predicted dates, on his stations, are in his Table II, within 2 days of the observed.",
        "",
        "| Year | Stage | Observed | Harcourt's method | NEWA's |",
        "| --- | --- | --- | --- | --- |",
    ]
    errors: dict[str, list[int]] = {"harcourt": [], "newa": []}
    sites = [("Bay of Quinte", y, QUINTE[y].split()) for y in QUINTE] + [
        ("Guelph", y, [GUELPH_HATCH[y]]) for y in GUELPH_HATCH
    ]
    for place, year, observed in sites:
        days, lo, hi = open_meteo(place, cache)
        mine = np.array([d.year == year for d in days])
        days, lo, hi = days[mine], lo[mine], hi[mine]
        sine = np.where(days >= date(year, 4, 1), degree_days_sine(lo, hi, 9.0), 0.0)
        harcourt = np.cumsum(np.nan_to_num(sine))
        newa = np.cumsum(np.nan_to_num(degree_days_average(lo * 1.8 + 32, hi * 1.8 + 32, 48.0)))
        for k, text in enumerate(observed):
            seen = date(year, int(text[:2]), int(text[3:]))
            a, b = reached(days, harcourt, HARCOURT_C[k]), reached(days, newa, NEWA_F[k])
            assert a is not None and b is not None
            errors["harcourt"].append((a - seen).days)
            errors["newa"].append((b - seen).days)
            stage = STAGES[k] if place == "Bay of Quinte" else "Hatch (Guelph)"
            lines.append(f"| {year} | {stage} | {seen:%b %-d} | {(a - seen).days:+d} | {(b - seen).days:+d} |")
    lines += ["", "Days late (+) or early (−), all 36 dated peaks:", ""]
    for name, label in (("harcourt", "Harcourt's method"), ("newa", "NEWA's rule (ours)")):
        v = np.array(errors[name])
        lines.append(
            f"- {label}: median {np.median(v):+.0f}, mean {v.mean():+.1f}, mean absolute {np.abs(v).mean():.1f}, from {v.min():+d} to {v.max():+d}"
        )
    report.detail(lines[-2])
    report.detail(lines[-1])


def our_events(lo_f: np.ndarray, hi_f: np.ndarray) -> np.ndarray:
    """Our running total (simple average 48 °F from January 1; a missing day adds nothing)."""
    return np.cumsum(np.nan_to_num(degree_days_average(lo_f, hi_f, 48.0)))


EVENTS = {"egg hatch": 280, "cocooning": 600, "adults": 815}


def newa_part(data: Path, lines: list[str], report: Reporter) -> None:
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    stores: dict[int, GridStore] = {}
    paths = [p for p in sorted((CACHE / "hours").glob("*.json")) if int(p.stem.rsplit("_", 1)[1]) < 2026]
    report.step(f"NEWA's rule against ours on {len(paths)} station-seasons' hours and the archive")
    lines += [
        "",
        "## 2. NEWA's model against ours, on the station's hours and the archive's",
        "",
        "Days each total reaches NEWA's egg hatch (280), cocooning (600) and adult emergence (815): NEWA's (its days and degree days) / ours on the same station days / ours on the archive at the station's cell; and the Crop Risk Tool's old table (single sine 48.2/86 °F: egg hatch 300, pupae 595, adults 815) on the station days. Our curves pass half of hatch, of larvae cocooned and of adults emerged at NEWA's totals.",
        "",
        "| Station | Year | Egg hatch NEWA / station / grid / old | Cocooning NEWA / station / grid / old | Adults NEWA / station / grid / old |",
        "| --- | --- | --- | --- | --- |",
    ]
    diffs: dict[str, dict[str, list[int]]] = {e: {"station": [], "grid": [], "old": []} for e in EVENTS}
    for path in paths:
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        days = make_days(load_hours(path))
        if len(days) < 290:
            continue
        station = stations[sid]
        lo = np.array([d.mint for d in days])
        hi = np.array([d.maxt for d in days])
        ok = np.isfinite(lo) & np.isfinite(hi)
        newa = np.cumsum(np.where(ok, np.maximum((lo + hi) / 2 - 48, 0.0), 0.0))  # NEWA: a day without hours adds 0
        ours = our_events(np.where(ok, lo, np.nan), np.where(ok, hi, np.nan))
        old = np.cumsum(np.nan_to_num(degree_days_sine(np.where(ok, lo, np.nan), np.where(ok, hi, np.nan), 48.2, 86)))
        cell = NDFD.cell_of(station["lat"], station["lon"])
        grid = None
        if cell is not None:
            if year not in stores:
                stores[year] = GridStore.open(data, DAILY, year, temps)
            g_lo, g_hi = (stores[year].read_point(n, *cell) for n in ("air_temperature_min", "air_temperature_max"))
            grid = our_events(np.asarray(g_lo) * 1.8 + 32, np.asarray(g_hi) * 1.8 + 32)
        cells = []
        for event, threshold in EVENTS.items():
            n = reached_index(newa, threshold)
            s = reached_index(ours, threshold)
            g = reached_index(grid, threshold) if grid is not None else None
            o = reached_index(old, CRT_STEPS["pupae" if event == "cocooning" else event])
            cells.append(" / ".join(_day(year, k) for k in (n, s, g, o)))
            for key, value in (("station", s), ("grid", g), ("old", o)):
                if n is not None and value is not None:
                    diffs[event][key].append(value - n)
        lines.append(f"| {station['name']} | {year} | " + " | ".join(cells) + " |")
        report.detail(lines[-1])
    lines += ["", "Ours − NEWA's, days (median, 10th–90th percentile, range, n):", ""]
    labels = {
        "station": "ours on the station's days",
        "grid": "ours on the archive",
        "old": "the Crop Risk Tool's old table",
    }
    for event, by in diffs.items():
        for key, values in by.items():
            if values:
                v = np.array(values)
                lines.append(
                    f"- {event.capitalize()}, {labels[key]}: {np.median(v):+.0f} ({np.percentile(v, 10):+.0f} to {np.percentile(v, 90):+.0f}; {v.min():+d} to {v.max():+d}), n = {len(v)}"
                )


def _day(year: int, k: int | None) -> str:
    return "–" if k is None else f"{date(year, 1, 1) + timedelta(days=k):%b %-d}"


def normal_totals(lat: float, lon: float, data: Path, method) -> np.ndarray:
    """The normal running total from January 1 on the 366 slots: each year's own, averaged over the years."""
    cell = NDFD.cell_of(lat, lon)
    assert cell is not None
    years = list(NORMAL_YEARS)
    found = climatology.read_point(data, *cell, years, ["air_temperature_min", "air_temperature_max"])
    daily = []
    for k, year in enumerate(years):
        lo, hi = climatology.degree_day_temperatures(
            found["air_temperature_min"][k], found["air_temperature_max"][k], year
        )
        usable = np.isfinite(lo) & np.isfinite(hi)
        daily.append(np.where(usable, method(np.where(usable, lo, 0.0), np.where(usable, hi, 0.0)), np.nan))
    # As the API: a year missing too many days (gridMET's maximum for 2011–2013 is left out) doesn't count
    return climatology.running(np.stack(daily), years).mean


def normals_part(data: Path, lines: list[str], report: Reporter) -> None:
    report.step(f"typical dates on the {NORMAL_YEARS[0]}–{NORMAL_YEARS[-1]} normals at {', '.join(SITES)}")
    tables = curves(INSECT)
    x = dd_grid()

    def at(name: str, fraction: float) -> float:
        return round(float(np.interp(fraction, tables[name], x)))

    window = x[tables["window_scout_stem_tips_for_larval_feeding"] > 0]
    events = {
        "10 % of eggs hatched": at("generations_egg_hatch", 0.1),
        "Half the eggs hatched, and the scouting window opens (NEWA 280)": at("generations_egg_hatch", 0.5),
        "Most larvae feeding (the risk's peak)": float(x[np.argmax(tables["activity_larval_feeding"])]),
        "Scouting window closes": float(window[-1]),
        "Half the larvae cocooned (NEWA 600)": at("generations_larval_feeding", 0.5),
        "Half the adults out (NEWA 815)": at("generations_pupae_in_cocoons", 0.5),
        "UW–Madison's heaviest feeding begins": 600.0,
    }
    lines += [
        "",
        f"## 3. Typical dates on the {NORMAL_YEARS[0]}–{NORMAL_YEARS[-1]} normals",
        "",
        "The day the normal running total (each year's own total from January 1, averaged over the 30 years, as `/api/v2/climate/normals` computes it) reaches each event, at the archive's cell. Ours: simple average 48 °F. Old: the Crop Risk Tool's table on single sine 48.2/86 °F.",
        "",
        "| Event | Degree days | " + " | ".join(SITES) + " |",
        "| --- | --- | " + " | ".join("---" for _ in SITES) + " |",
    ]
    ours = {site: normal_totals(*SITES[site], data, lambda lo, hi: degree_days_average(lo, hi, 48.0)) for site in SITES}
    old = {site: normal_totals(*SITES[site], data, lambda lo, hi: degree_days_sine(lo, hi, 48.2, 86)) for site in SITES}

    def when(total: np.ndarray, threshold: float) -> str:
        k = int(np.argmax(total >= threshold))
        found = climatology.slot_date(k, 2001 if k != 59 else 2000)
        return "–" if total[k] < threshold or found is None else f"{found:%b %-d}"

    for label, threshold in events.items():
        lines.append(f"| {label} | {threshold:,.0f} | " + " | ".join(when(ours[s], threshold) for s in SITES) + " |")
    lines.append("| UW–Madison's heaviest feeding ends | 800 | " + " | ".join(when(ours[s], 800) for s in SITES) + " |")
    for label, threshold in CRT_STEPS.items():
        lines.append(
            f"| Old: {label} | {threshold:,} (sine) | " + " | ".join(when(old[s], threshold) for s in SITES) + " |"
        )
    for line in lines[-12:]:
        report.detail(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/alfalfa-weevil/weather.md")
    parser.add_argument("--data", default="data")
    parser.add_argument("--cache", default="tmp/alfalfa-weevil", help="where Open-Meteo's answers are kept")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    lines = [
        "# Alfalfa weevil: Harcourt's dated peaks, NEWA on the same weather, and typical dates in Wisconsin",
        "",
        "Written by `scripts/check_alfalfa_weevil.py`. Ours: simple average degree days above 48 °F from January 1, egg hatch half done at 280, larvae cocooning half done at 600, adults half out at 815 (NEWA's table). Station days are NEWA's on the local clock; the archive's are CST.",
        "",
    ]
    harcourt_part(Path(args.cache), lines, report)
    newa_part(Path(args.data), lines, report)
    normals_part(Path(args.data), lines, report)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    report.step(f"wrote {args.out}")
    if not report.finish("Harcourt's peaks, NEWA's stations and the normals"):
        sys.exit(1)


if __name__ == "__main__":
    main()
