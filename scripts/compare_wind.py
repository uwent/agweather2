"""Daily mean wind against anemometers (PLAN.md Phase 6 D3 (a), D84): the archive's (URMA, 10 m) and gridMET's
(NLDAS-2, 10 m) at Wisconet's stations and at the airport stations IEM summarizes, by month and by station.
Decides whether gridMET's 30 years of wind and ET0 are adjusted to the archive (gridMET reads 1/0.64 of the
archive's wind over Wisconsin, D2).

- Wisconet: `daily_wind_speed_mph_avg` (the day's scalar mean) from anemometers on a 3 m mast (every wind field is
  `windspd_ms_3m_*`), brought to 10 m by FAO-56's log profile (eq. 47), the same profile the archive uses to go
  from 10 m to 2 m: u10 = u3 × ln(67.8·3 − 5.42)⁻¹ / ln(67.8·10 − 5.42)⁻¹ = 1.23 × u3. Since 2023–2024.
- Airports: IEM's daily summaries of the ASOS and AWOS reports (`WI_ASOS`, `avg_sknt`, the mean of the day's
  reports in knots, local calendar days), anemometers at ~10 m. URMA assimilates these stations, so they aren't
  independent of the archive. 78 of Wisconet's 81 stations have MADIS ids, so URMA may see them too (mesonet winds
  are often on its reject lists); neither network is a fully independent check.
- gridMET: the kept files in data/gridmet/vs/ (`manage.py climatology`), bilinear to the station; 2016–2025.

    uv run python scripts/compare_wind.py --start 2016-01-01 --end 2026-10-31

Responses are cached in tmp/wisconet/ and tmp/iem/. `--quiet` prints only warnings, failures and the summary.
"""

import argparse
import math
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from compare_gridmet import read_gridmet

from agdata.catalog import DAILY_VARIABLES
from agdata.clients.http import JsonClient
from agdata.clients.wisconet import Wisconet
from agdata.grid import NDFD, service_window
from agdata.progress import Reporter
from agdata.store import DAILY, GridStore

WISCONET_FIELD = "daily_wind_speed_mph_avg"  # field 129, the station's local day
MPH = 0.44704  # m/s
KNOT = 0.514444  # m/s
TO_10M = math.log(67.8 * 10 - 5.42) / math.log(67.8 * 3 - 5.42)  # FAO-56 eq. 47, 3 m → 10 m
PLAUSIBLE = (0.0, 30.0)  # a day's mean wind, m/s
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-wind.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if first > last:
        parser.error("--start must not be after --end")
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    window = service_window(args.box)
    data = Path(args.data)

    networks = {}
    report.step("Wisconet stations")
    wisconet = Wisconet(cache_dir="tmp/wisconet")
    stations = [
        {
            "id": s["station_id"],
            "name": s.get("station_name") or s["station_id"],
            "lat": s["latitude"],
            "lon": s["longitude"],
        }
        for s in wisconet.stations()
    ]
    stations = [s for s in stations if inside(s, window)]
    observed = np.full((len(days), len(stations)), np.nan)
    for k, s in enumerate(stations):
        for year in range(max(first.year, 2023), last.year + 1):
            try:
                series = wisconet.daily(s["id"], WISCONET_FIELD, year)
            except Exception as error:  # the station-year stays missing; a rerun retries it
                report.fail(f"Wisconet {s['id']} {year}", error)
                continue
            for day, value in series.items():
                if first <= day <= last:
                    observed[(day - first).days, k] = value * MPH * TO_10M
        report.progress("Wisconet stations", k + 1, len(stations))
    networks["Wisconet"] = (stations, plausible(observed))

    report.step("airport stations (IEM)")
    iem = JsonClient("https://mesonet.agron.iastate.edu", cache_dir="tmp/iem", pause_s=0.5)
    iem.session.headers["User-Agent"] = "agweather-validation"
    listing = iem.get("geojson/network/WI_ASOS.geojson", cache_key="WI_ASOS.geojson")
    airports = [
        {
            "id": f["properties"]["sid"],
            "name": f["properties"]["sname"],
            "lat": f["geometry"]["coordinates"][1],
            "lon": f["geometry"]["coordinates"][0],
        }
        for f in listing["features"]
    ]
    airports = [s for s in airports if inside(s, window)]
    observed = np.full((len(days), len(airports)), np.nan)
    today = datetime.now(UTC).date()
    for k, s in enumerate(airports):
        for year in range(first.year, last.year + 1):
            key = f"{s['id']}_{year}{f'_{today}' if year >= today.year else ''}.json"
            try:
                rows = iem.get(
                    "api/1/daily.json", params={"station": s["id"], "network": "WI_ASOS", "year": year}, cache_key=key
                )["data"]
            except Exception as error:
                report.fail(f"IEM {s['id']} {year}", error)
                continue
            for row in rows:
                day = date.fromisoformat(row["date"])
                if first <= day <= last and row.get("avg_sknt") is not None:
                    observed[(day - first).days, k] = row["avg_sknt"] * KNOT
        report.progress("airport stations", k + 1, len(airports))
    networks["Airports (ASOS/AWOS)"] = (airports, plausible(observed))

    everyone = [s for stations, _ in networks.values() for s in stations]
    cells = [NDFD.cell_of(s["lat"], s["lon"]) for s in everyone]
    report.step(f"the archive's daily mean wind at {len(cells)} stations' cells")
    archive = np.full((len(days), len(everyone)), np.nan)
    variable = DAILY_VARIABLES["wind_speed_mean"]
    for year in range(first.year, last.year + 1):
        try:
            store = GridStore.open(data, DAILY, year, [variable])
        except (FileNotFoundError, KeyError) as error:
            report.warn(f"archive {year}: {error}")
            continue
        a, b = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        t0, t1 = (a - date(year, 1, 1)).days, (b - date(year, 1, 1)).days + 1
        archive[(a - first).days : (b - first).days + 1] = store.read_cells(
            "wind_speed_mean", [c for c in cells if c is not None], start=t0, stop=t1
        )
        report.progress("archive years", year - first.year + 1, last.year - first.year + 1)

    report.step("gridMET's daily mean wind at the stations")
    gridmet = np.full_like(archive, np.nan)
    for year in range(first.year, last.year + 1):
        path = data / "gridmet" / "vs" / f"{year}.nc"
        if not path.exists():
            continue
        dates, values, lats, lons = read_gridmet(path, "vs")
        at = bilinear(values, lats, lons, [(s["lat"], s["lon"]) for s in everyone])
        for n, day in enumerate(dates):
            if first <= day <= last:
                gridmet[(day - first).days] = at[n]
        report.progress("gridMET years", year - first.year + 1, last.year - first.year + 1)

    sections = []
    k = 0
    for label, (stations, observed) in networks.items():
        cols = slice(k, k + len(stations))
        k += len(stations)
        sections.append(section(label, days, stations, observed, archive[:, cols], gridmet[:, cols]))
    report.step(f"writing {args.out} (overwriting)")
    Path(args.out).write_text(build_report(args, days, networks, sections))
    if not report.finish(f"{len(everyone)} stations, {len(days)} days"):
        sys.exit(1)


def inside(station: dict, window) -> bool:
    cell = NDFD.cell_of(station["lat"], station["lon"])
    return cell is not None and window.contains(*cell)


def plausible(values: np.ndarray) -> np.ndarray:
    return np.where((values >= PLAUSIBLE[0]) & (values <= PLAUSIBLE[1]), values, np.nan)


def bilinear(values: np.ndarray, lats: np.ndarray, lons: np.ndarray, points: list[tuple[float, float]]) -> np.ndarray:
    """(days, points) from (days, lat, lon) on a regular grid (latitudes either way)."""
    out = np.full((values.shape[0], len(points)), np.nan)
    for k, (lat, lon) in enumerate(points):
        fy = (
            np.interp(lat, lats, np.arange(len(lats)))
            if lats[0] < lats[-1]
            else np.interp(lat, lats[::-1], np.arange(len(lats))[::-1])
        )
        fx = np.interp(lon, lons, np.arange(len(lons)))
        y0, x0 = int(np.floor(fy)), int(np.floor(fx))
        wy, wx = fy - y0, fx - x0
        y1, x1 = min(y0 + 1, len(lats) - 1), min(x0 + 1, len(lons) - 1)
        out[:, k] = (
            values[:, y0, x0] * (1 - wy) * (1 - wx)
            + values[:, y0, x1] * (1 - wy) * wx
            + values[:, y1, x0] * wy * (1 - wx)
            + values[:, y1, x1] * wy * wx
        )
    return out


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
    return f"| {label} | {n:,} | {bias:+.2f} | {mae:.2f} | {ratio:.2f} | {r:.3f} |"


def section(label, days, stations, observed, archive, gridmet) -> list[str]:
    both = np.isfinite(gridmet)  # the days and stations gridMET covers, for a like-for-like row
    lines = [
        f"## {label}",
        "",
        f"{len(stations)} stations. Bias and MAE in m/s at 10 m; ratio is of the totals over the same station-days.",
        "",
        "| Source | station-days | bias | MAE | ratio | r |",
        "| --- | --- | --- | --- | --- | --- |",
        row("Archive (URMA)", archive, observed),
        row("Archive, gridMET's days only", np.where(both, archive, np.nan), observed),
        row("gridMET", gridmet, observed),
        "",
        "### By month",
        "",
        "| Month | archive ratio | archive r | gridMET ratio | gridMET r | station mean (m/s) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    months = np.array([d.month for d in days])
    for m in range(1, 13):
        sel = months == m
        _, _, _, ra, ca = stats(archive[sel], observed[sel])
        _, _, _, rg, cg = stats(gridmet[sel], observed[sel])
        mean = np.nanmean(observed[sel]) if np.isfinite(observed[sel]).any() else np.nan
        lines.append(f"| {MONTHS[m - 1]} | {ra:.2f} | {ca:.3f} | {rg:.2f} | {cg:.3f} | {mean:.2f} |")
    per = []
    for k, s in enumerate(stations):
        n, _, _, ra, _ = stats(archive[:, k], observed[:, k])
        ng, _, _, rg, _ = stats(gridmet[:, k], observed[:, k])
        if n >= 180:
            per.append((ra, f"| {s['name']} ({s['id']}) | {n:,} | {ra:.2f} | {rg:.2f} | {ng:,} |"))
    ratios = np.array([p[0] for p in per])
    spread = (
        f" Across stations, the archive's ratio runs {np.percentile(ratios, 10):.2f} (P10), "
        f"{np.percentile(ratios, 50):.2f} (median), {np.percentile(ratios, 90):.2f} (P90)."
        if ratios.size
        else ""
    )
    lines += [
        "",
        "### By station",
        "",
        f"Each station's ratio over its own days (stations with at least 180), sorted by the archive's.{spread}",
        "",
        "| Station | days | archive ratio | gridMET ratio | gridMET days |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [line for _, line in sorted(per)]
    return [*lines, ""]


def build_report(args, days, networks, sections) -> str:
    lines = [
        "# Wind against anemometers",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_wind.py` (PLAN.md Phase 6 D3 (a), D84). Daily "
        f"mean wind speed, {days[0]} to {days[-1]}, at the stations in the `{args.box}` box: the archive (URMA's "
        "hourly 10 m analysis, the mean of the CST day's hours) at the station's cell and gridMET (NLDAS-2, 10 m) "
        "bilinear to the station, against the station's mean of the day. Wisconet's 3 m anemometers are brought to "
        f"10 m by FAO-56's log profile (× {TO_10M:.3f}); airport anemometers are at about 10 m. URMA assimilates the "
        "airport stations, and Wisconet's reach MADIS (78 of 81 have MADIS ids), so the archive may have seen "
        "either. Days are each network's own (Wisconet's and "
        "IEM's local days; the archive's CST days; gridMET's day runs into our next morning, D2), which matters "
        "little for a day's mean wind.",
        "",
    ]
    for section_lines in sections:
        lines += section_lines
    return "\n".join(lines)


if __name__ == "__main__":
    main()
