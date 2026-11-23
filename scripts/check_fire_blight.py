"""Fire blight (agmodels `fire-blight`) against NEWA on Wisconsin's orchard stations (models plan B3, step 4).

NEWA's results come from scripts/newa_reference.py on the station's own hours; ours run through the point rollup and
the runner on the station's own hours (the method) and on the archive's hours at the station's cell (the map), as
scripts/check_apple_scab.py does. Compared during NEWA's bloom (first blossom at 230 DD43 to petal fall at 578 or June
15): first blossom, Cougarblight's four-day total (ours counts hours from 50 °F, NEWA's from 60; NEWA's risk level
by the default history), MaryBlyt's EIP, and its Infection days.

    uv run python scripts/check_fire_blight.py [--out docs/validation/models/fire-blight/newa.md]
"""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from check_apple_scab import GAUGE_MIN_RATIO, HOUR, grid_hours, station_hours
from newa_reference import CACHE, fire_blight, load_hours, make_days

from agdata.catalog import GAP_FILL, VARIABLES
from agdata.grid import NDFD
from agdata.point import daily_at_point
from agdata.store import HOURLY, GridStore
from agdata.timezones import GRID_ZONE
from agmodels.models import fire_blight as fb
from agmodels.registry import model
from agmodels.runner import required_inputs, run


def ours(hours, year: int, latitude: float, last: date):
    first = date(year, 1, 1)
    names = required_inputs(model("fire-blight"))
    daily = daily_at_point(datetime(year, 1, 1, tzinfo=UTC), hours, GRID_ZONE, first, last, names=names)
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    return run("fire-blight", dates=dates, daily={n: daily[n] for n in names}, latitude=latitude, gap_fill=GAP_FILL)


def newa_bloom(rows: list[dict], year: int) -> tuple[int, int] | None:
    first = next((r["doy"] for r in rows if r["first_bloom"]), None)
    if first is None:
        return None
    june_15 = date(year, 6, 15).timetuple().tm_yday
    last = next((r["doy"] for r in rows if r["dd43"] >= 578 or r["doy"] >= june_15), june_15)
    return first, last


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/validation/models/fire-blight/newa.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    stores: dict[int, GridStore] = {}
    lines = [
        "# Fire blight: ours against NEWA's on Wisconsin's orchard stations",
        "",
        "Written by `scripts/check_fire_blight.py`. NEWA: its rules on the station's hours (`scripts/newa_reference.py`). Ours: the station's own hours, and the archive's at the station's cell. NEWA's bloom days only. Cougarblight: the four-day total's median difference (ours − NEWA's) and the share of days on the same level (blight nearby last year). EIP: the median absolute difference. Infection: MaryBlyt's Infection days, NEWA's / ours matched within a day / ours not in NEWA's.",
        "",
        "| Station | Year | First blossom NEWA / station / grid | CB diff, same level (station; grid) | EIP abs diff (station; grid) | Infections (station; grid) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    tally = {"station": [0, 0, 0, 0, 0], "grid": [0, 0, 0, 0, 0]}  # same level, days, NEWA infections, matched, extra
    eips: dict[str, list[float]] = {"station": [], "grid": []}
    for path in sorted((CACHE / "hours").glob("*.json")):
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        if year >= 2026:
            continue
        station = stations[sid]
        cell = NDFD.cell_of(station["lat"], station["lon"])
        if cell is None:
            continue
        rows = fire_blight(make_days(load_hours(path)))
        bloom = newa_bloom(rows, year)
        if bloom is None:
            continue
        if year not in stores:
            stores[year] = GridStore.open(
                Path(args.data), HOURLY, year, [VARIABLES[v] for v in ("air_temperature", "dew_point", "precipitation")]
            )
        s_hours, g_hours = station_hours(path, year), grid_hours(stores[year], cell)
        spring = slice(
            int((datetime(year, 4, 1, tzinfo=UTC) - datetime(year, 1, 1, tzinfo=UTC)) / HOUR),
            int((datetime(year, 7, 1, tzinfo=UTC) - datetime(year, 1, 1, tzinfo=UTC)) / HOUR),
        )
        g_rain = np.nansum(g_hours["precipitation"][spring])
        gauge_ok = (np.nansum(s_hours["precipitation"][spring]) / g_rain if g_rain > 25 else 1.0) >= GAUGE_MIN_RATIO
        last = date(year, 7, 15)
        cells = {}
        firsts = {}
        for kind, hours in (("station", s_hours), ("grid", g_hours)):
            r = ours(hours, year, station["lat"], last)
            o = r.outputs
            on = np.flatnonzero(o["bloom"] == 1)
            firsts[kind] = r.dates[int(on[0])] if on.size else None
            diffs, same, eip, newa_inf, ours_inf = [], 0, [], [], []
            for row in rows:
                k = row["doy"] - 1
                if not bloom[0] <= row["doy"] <= bloom[1] or k >= len(r.dates):
                    continue
                cb = o["cougarblight"][k]
                if np.isfinite(cb):
                    diffs.append(cb - row["four_day"])
                    same += int(fb.level(cb) == fb.level(row["four_day"]))
                if np.isfinite(o["eip"][k]):
                    eip.append(abs(o["eip"][k] - row["eip"]))
                if row["risk"] == "infection":
                    newa_inf.append(k)
                if o["maryblyt"][k] == 3:
                    ours_inf.append(k)
            matched = sum(1 for k in newa_inf if any(abs(k - j) <= 1 for j in ours_inf))
            extra = sum(1 for j in ours_inf if not any(abs(k - j) <= 1 for k in newa_inf))
            cells[kind] = (
                np.median(diffs) if diffs else np.nan,
                same / max(len(diffs), 1),
                np.median(eip) if eip else np.nan,
                len(newa_inf),
                matched,
                extra,
            )
            if gauge_ok:
                t = tally[kind]
                t[0] += same
                t[1] += len(diffs)
                t[2] += len(newa_inf)
                t[3] += matched
                t[4] += extra
                eips[kind] += eip

        def fmt(d):
            return "–" if d is None else f"{d:%b %-d}"

        newa_first = date(year, 1, 1) + timedelta(days=bloom[0] - 1)
        s, g = cells["station"], cells["grid"]
        lines.append(
            f"| {station['name']}{'' if gauge_ok else ' (gauge)'} | {year} | {fmt(newa_first)} / {fmt(firsts['station'])} / {fmt(firsts['grid'])} | {s[0]:+.0f}, {s[1]:.0%}; {g[0]:+.0f}, {g[1]:.0%} | {s[2]:.0f}; {g[2]:.0f} | {s[3]} / {s[4]} / {s[5]}; {g[4]} / {g[5]} |"
        )
        print(lines[-1], flush=True)
    lines += ["", "## Totals (working gauges)", ""]
    for kind, (same, days, n_inf, matched, extra) in tally.items():
        lines.append(
            f"- {kind} hours: Cougarblight on NEWA's level {same} of {days} bloom days ({same / max(days, 1):.0%}); EIP median absolute difference {np.median(eips[kind]):.0f}; NEWA's {n_inf} Infection days, {matched} matched within a day, {extra} of ours not in NEWA's"
        )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-3:]))


if __name__ == "__main__":
    main()
