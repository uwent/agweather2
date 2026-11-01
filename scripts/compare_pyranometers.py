"""Daily shortwave against Wisconet's pyranometers (PLAN.md Phase 2 H): v2 (HRRR) and the old API (SSEC satellite
insolation) at each station's cell, by month. Settles v2 against SSEC's gap in winter (v2/SSEC 1.40 in early 2025).

Wisconet's API is throttled, so each station-year is fetched once, slowly, and cached in tmp/wisconet/. The old
API's insolation grids come from `compare_legacy.py`'s cache (tmp/legacy-cache).

    uv run python scripts/compare_pyranometers.py --start 2025-01-01 --end 2026-10-27

`--quiet` prints only warnings, failures and the summary.
"""

import argparse
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_legacy import OLD_API, bounds, read_daily

from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.clients.wisconet import Wisconet
from agdata.grid import NDFD, service_window
from agdata.progress import Reporter

CACHE = Path("tmp/wisconet")
FIELD = "daily_solar_radiation_mj_tot"  # field id 157, MJ/m² over the station's local day
OPEN_METEO_MODELS = ("ncep_nbm_conus", "ecmwf_ifs", "best_match")
PLAUSIBLE_MJ = (0.0, 36.0)  # a day's total above 0 and under the clear-sky maximum in Wisconsin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-pyranometers.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    window = service_window(args.box)

    wisconet = Wisconet(cache_dir=CACHE)
    stations = [s for s in wisconet.stations() if inside(s, window)]
    if not stations:
        report.fail("stations", f"no Wisconet stations inside the {args.box} box")
        sys.exit(1)
    report.step(f"{len(stations)} stations in the box; {len(days)} days, {first} to {last}; writing {args.out}")
    observed = np.full((len(days), len(stations)), np.nan)
    for k, station in enumerate(stations):
        for year in range(first.year, last.year + 1):
            try:
                series = wisconet.daily(station["station_id"], FIELD, year)
            except Exception as error:  # the station-year stays missing; a rerun retries it
                report.fail(f"station {station['station_id']} {year}", error)
                continue
            for day, value in series.items():
                if first <= day <= last:
                    observed[(day - first).days, k] = value
        report.progress("stations", k + 1, len(stations))
    observed[(observed <= PLAUSIBLE_MJ[0]) | (observed > PLAUSIBLE_MJ[1])] = np.nan

    report.step("reading v2's daily shortwave")
    v2_grid = read_daily(Path(args.data), "shortwave_radiation_sum", days)
    v2 = np.full_like(observed, np.nan)
    ssec = np.full_like(observed, np.nan)
    for k, station in enumerate(stations):
        cell = NDFD.cell_of(station["latitude"], station["longitude"])
        assert cell is not None  # `inside` kept only stations on the grid
        y, x = window.local(*cell)
        v2[:, k] = v2_grid[:, y, x]
    for n, day in enumerate(days):
        report.progress("old API insolation", n + 1, len(days))
        try:
            grid = OLD_API.insolation_mj_m2(day, bounds(window))
        except Exception as error:  # the SSEC side of this day stays missing
            report.fail(f"old API {day}", error)
            continue
        for k, station in enumerate(stations):
            value = grid.get(f"[{round(station['latitude'], 1):.1f}, {round(station['longitude'], 1):.1f}]")
            ssec[n, k] = np.nan if value is None else value

    open_meteo = open_meteo_days(stations, first, last, len(days), report)
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text(build_report(args, days, stations, observed, v2, ssec, open_meteo))
    report.step(f"wrote {args.out}")
    if not report.finish(f"{len(stations)} stations, {len(days)} days"):
        sys.exit(1)


def open_meteo_days(stations: list[dict], first: date, last: date, n: int, report: Reporter) -> dict[str, np.ndarray]:
    """Open-Meteo's historical-forecast daily shortwave at each station (Central days), per model, a year a request.
    WISP 3 takes its ET0 from Open-Meteo, NBM first then best_match (`../wisp3` PLAN.md)."""
    client = OpenMeteoPoints(cache_dir=CACHE, api_key=os.environ.get("OPEN_METEO_API_KEY") or None)
    locations = [(s["latitude"], s["longitude"]) for s in stations]
    out = {}
    for m, model in enumerate(OPEN_METEO_MODELS, 1):
        report.progress("Open-Meteo models", m, len(OPEN_METEO_MODELS))
        values = np.full((n, len(stations)), np.nan)
        for year in range(first.year, last.year + 1):
            a, b = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
            report.step(f"Open-Meteo {model} {year}: {len(locations)} locations")
            for k, block in enumerate(client.daily(locations, a, b, ["shortwave_radiation_sum"], model=model)):
                series = [np.nan if v is None else v for v in block["shortwave_radiation_sum"]]
                values[(a - first).days : (a - first).days + len(series), k] = series
        out[model] = values
    return out


def inside(station: dict, window) -> bool:
    cell = NDFD.cell_of(station["latitude"], station["longitude"])
    return cell is not None and window.contains(*cell)


def stats(model: np.ndarray, observed: np.ndarray) -> tuple[int, float, float, float, float]:
    ok = np.isfinite(model) & np.isfinite(observed)
    m, o = model[ok], observed[ok]
    if m.size < 3:
        return int(m.size), np.nan, np.nan, np.nan, np.nan
    return (
        int(m.size),
        float((m - o).mean()),
        float(np.abs(m - o).mean()),
        float(m.sum() / o.sum()),
        float(np.corrcoef(m, o)[0, 1]),
    )


def row(label: str, model: np.ndarray, observed: np.ndarray) -> str:
    n, bias, mae, ratio, r = stats(model, observed)
    return f"| {label} | {n} | {bias:+.2f} | {mae:.2f} | {ratio:.2f} | {r:.3f} |"


def build_report(args, days, stations, observed, v2, ssec, open_meteo) -> str:
    lines = [
        "# Shortwave against Wisconet's pyranometers",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_pyranometers.py` (PLAN.md Phase 2 H). Daily "
        f"totals (MJ/m²), {days[0]} to {days[-1]}, at {len(stations)} Wisconet stations in the `{args.box}` box: v2 "
        "(HRRR's hourly means) at the station's cell and the old API's SSEC satellite insolation at the nearest 0.1° "
        f"point, against the station's `{FIELD}`. Station days outside {PLAUSIBLE_MJ[0]:g}–{PLAUSIBLE_MJ[1]:g} MJ/m² "
        "are left out. Bias and MAE in MJ/m²; ratio is of the totals over the same days.",
        "",
        "## Which day a Wisconet stamp closes",
        "",
        "Correlation of v2 with the stations, their days shifted (0 is the reading used: the day before the stamp).",
        "",
        "| Shift (days) | r |",
        "|---|---|",
    ]
    for shift in (-1, 0, 1):
        shifted = np.roll(observed, shift, axis=0)
        if shift:
            shifted[: max(shift, 0)] = np.nan
            shifted[len(days) + min(shift, 0) :] = np.nan
        lines.append(f"| {shift:+d} | {stats(v2, shifted)[4]:.3f} |")
    head = ["| Source | days | bias | MAE | ratio | r |", "|---|---|---|---|---|---|"]
    lines += ["", "## Overall", "", *head, row("v2 (HRRR)", v2, observed), row("old API (SSEC)", ssec, observed)]
    lines += [row(f"Open-Meteo {model}", values, observed) for model, values in open_meteo.items()]
    lines += [
        "",
        "Open-Meteo is its historical-forecast API at each station's location (its own cell), on Central days. WISP 3 "
        "takes ET0 from Open-Meteo, NBM first, then best_match.",
    ]

    months = np.array([d.year * 100 + d.month for d in days])
    lines += [
        "",
        "## By month",
        "",
        "| Month | days | v2 bias | v2 MAE | v2 ratio | SSEC bias | SSEC MAE | SSEC ratio | "
        + " | ".join(f"{m} ratio" for m in open_meteo)
        + " |",
        "|---|---|---|---|---|---|---|---|" + "---|" * len(open_meteo),
    ]
    for month in sorted(set(months)):
        sel = months == month
        n, b2, m2, r2, _ = stats(v2[sel], observed[sel])
        _, bs, ms, rs, _ = stats(ssec[sel], observed[sel])
        lines.append(
            f"| {month // 100}-{month % 100:02d} | {n} | {b2:+.2f} | {m2:.2f} | {r2:.2f} | "
            f"{bs:+.2f} | {ms:.2f} | {rs:.2f} | "
            + " | ".join(f"{stats(values[sel], observed[sel])[3]:.2f}" for values in open_meteo.values())
            + " |"
        )

    lines += [
        "",
        "## By station",
        "",
        "| Station | days | v2 ratio | v2 r | SSEC ratio | SSEC r |",
        "|---|---|---|---|---|---|",
    ]
    for k, station in enumerate(stations):
        n, _, _, r2, c2 = stats(v2[:, k], observed[:, k])
        _, _, _, rs, cs = stats(ssec[:, k], observed[:, k])
        if n:
            lines.append(
                f"| {station['station_name']} ({station['station_id']}) | {n} | "
                f"{r2:.2f} | {c2:.3f} | {rs:.2f} | {cs:.3f} |"
            )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
