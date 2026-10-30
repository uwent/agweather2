"""Daily shortwave against Wisconet's pyranometers (PLAN.md Phase 2 H): v2 (HRRR) and the old API (SSEC satellite
insolation) at each station's cell, by month. Settles v2 against SSEC's gap in winter (v2/SSEC 1.40 in early 2025).

Wisconet's API is throttled, so each station-year is fetched once, slowly, and cached in tmp/wisconet/. The old
API's insolation grids come from `compare_legacy.py`'s cache (tmp/legacy-cache).

    uv run python scripts/compare_pyranometers.py --start 2025-01-01 --end 2026-10-27
"""

import argparse
import json
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).parent))
from compare_legacy import legacy, read_daily

from agdata.grid import NDFD, service_window

API = "https://api.wisconet.wisc.edu/api/v1"
CACHE = Path("tmp/wisconet")
FIELD = "daily_solar_radiation_mj_tot"  # field id 157, MJ/m² over the station's local day
FIELD_ID = 157
CENTRAL = ZoneInfo("America/Chicago")
PAUSE_S = 3.0  # between Wisconet requests
PLAUSIBLE_MJ = (0.0, 36.0)  # a day's total above 0 and under the clear-sky maximum in Wisconsin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-pyranometers.md")
    args = parser.parse_args()
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    window = service_window(args.box)

    stations = [s for s in fetch_stations() if inside(s, window)]
    print(f"{len(stations)} stations in the box; {len(days)} days", flush=True)
    observed = np.full((len(days), len(stations)), np.nan)
    for k, station in enumerate(stations):
        for year in range(first.year, last.year + 1):
            for day, value in station_days(station["station_id"], year).items():
                if first <= day <= last:
                    observed[(day - first).days, k] = value
    observed[(observed <= PLAUSIBLE_MJ[0]) | (observed > PLAUSIBLE_MJ[1])] = np.nan

    v2_grid = read_daily(Path(args.data), "shortwave_radiation_sum", days)
    v2 = np.full_like(observed, np.nan)
    ssec = np.full_like(observed, np.nan)
    for k, station in enumerate(stations):
        cell = NDFD.cell_of(station["latitude"], station["longitude"])
        assert cell is not None  # `inside` kept only stations on the grid
        y, x = window.local(*cell)
        v2[:, k] = v2_grid[:, y, x]
    for n, day in enumerate(days):
        grid = legacy(f"insolations/grid?date={day}", "", window)
        for k, station in enumerate(stations):
            value = grid.get(f"[{round(station['latitude'], 1):.1f}, {round(station['longitude'], 1):.1f}]")
            ssec[n, k] = np.nan if value is None else value

    Path(args.out).write_text(report(args, days, stations, observed, v2, ssec))
    print(f"wrote {args.out}")


def fetch_stations() -> list[dict]:
    path = CACHE / "stations.json"
    if not path.exists():
        response = requests.get(f"{API}/stations/", timeout=60)
        response.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text)
    return json.loads(path.read_text())


def inside(station: dict, window) -> bool:
    cell = NDFD.cell_of(station["latitude"], station["longitude"])
    return cell is not None and window.contains(*cell)


def station_days(station_id: str, year: int) -> dict[date, float]:
    """A station's daily totals for a year, by local date. Wisconet stamps a day's total at the local midnight that
    closes it (06Z in CST, 05Z in CDT), so the day is the one before the stamp's local date."""
    path = CACHE / f"{station_id}_{year}_{FIELD}.json"
    if not path.exists():
        start = datetime(year, 1, 1, tzinfo=CENTRAL) + timedelta(hours=1)
        end = datetime(year + 1, 1, 1, tzinfo=CENTRAL) + timedelta(hours=1)
        params = {"start_time": int(start.timestamp()), "end_time": int(end.timestamp()), "fields": FIELD}
        for attempt in range(4):
            response = requests.get(f"{API}/stations/{station_id}/measures", params=params, timeout=120)
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(30 * (attempt + 1))
                continue
            response.raise_for_status()
            break
        else:
            raise RuntimeError(f"{station_id} {year}: HTTP {response.status_code}")
        path.write_text(response.text)
        time.sleep(PAUSE_S)
        print(f"  fetched {station_id} {year}", flush=True)
    out: dict[date, float] = {}
    for row in json.loads(path.read_text()).get("data", []):
        stamp = datetime.fromtimestamp(row["collection_time"], UTC).astimezone(CENTRAL)
        for field_id, value in row["measures"]:
            if field_id == FIELD_ID and value is not None:
                out[(stamp - timedelta(hours=1)).date()] = float(value)
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
    return f"| {label} | {n} | {bias:+.2f} | {mae:.2f} | {ratio:.2f} | {r:.3f} |"


def report(args, days, stations, observed, v2, ssec) -> str:
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

    months = np.array([d.year * 100 + d.month for d in days])
    lines += [
        "",
        "## By month",
        "",
        "| Month | days | v2 bias | v2 MAE | v2 ratio | SSEC bias | SSEC MAE | SSEC ratio |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for month in sorted(set(months)):
        sel = months == month
        n, b2, m2, r2, _ = stats(v2[sel], observed[sel])
        _, bs, ms, rs, _ = stats(ssec[sel], observed[sel])
        lines.append(
            f"| {month // 100}-{month % 100:02d} | {n} | {b2:+.2f} | {m2:.2f} | {r2:.2f} | "
            f"{bs:+.2f} | {ms:.2f} | {rs:.2f} |"
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
