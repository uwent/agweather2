"""Apple scab (agmodels `apple-scab`) against NEWA on Wisconsin's orchard stations (models-plan B2, step 4).

For each station-season in tmp/newa/hours/ (scripts/fetch_newa.py), NEWA's results come from scripts/newa_reference.py
on the station's own hours (its leaf wetness sensor). Ours run twice through the point rollup and the runner, as the
API runs a point: on the station's own hours (temperature, dew point, rain; wetness estimated, so the difference is
the method) and on the archive's hours at the station's cell (what the map shows). Stations whose gauge caught under
40 % of the archive's April–June rain are left out of the totals (B5).

Compared, from green tip through June: green tip, the day ascospores reach 95 %, the day the season ends, and
infection days. A NEWA infection (a merged wet period) is matched when one of ours falls from its first day to its
last; one of ours unmatched is a false alarm against NEWA.

    uv run python scripts/check_apple_scab.py [--out tmp/newa/validation-apple-scab.md]
"""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from newa_reference import CACHE, LOCAL, load_hours, make_days, scab

from agdata.catalog import GAP_FILL, VARIABLES
from agdata.grid import NDFD
from agdata.point import daily_at_point
from agdata.store import HOURLY, GridStore
from agdata.timezones import GRID_ZONE
from agmodels.runner import required_inputs, run

HOUR = timedelta(hours=1)
GAUGE_MIN_RATIO = 0.4
SEASON_END = (6, 30)


def station_hours(path: Path, year: int) -> dict[str, np.ndarray]:
    """The station's hours as the hourly store holds them: step k ends k hours after January 1 00:00 UTC."""
    raw = json.loads(path.read_text())
    fields = raw["hrlyFields"]
    start = datetime(year, 1, 1, tzinfo=UTC)
    n = int((datetime(year + 1, 1, 1, tzinfo=UTC) - start) / HOUR)
    out = {name: np.full(n, np.nan) for name in ("air_temperature", "dew_point", "precipitation")}
    for row in raw["hrlyData"]:
        value = dict(zip(fields, row, strict=True))
        k = int((datetime.fromisoformat(value["date"]).astimezone(UTC) - start) / HOUR)
        if not 0 <= k < n:
            continue
        for name, field, convert in (
            ("air_temperature", "temp", lambda x: (x - 32) / 1.8),
            ("dew_point", "dwpt", lambda x: (x - 32) / 1.8),
            ("precipitation", "prcp", lambda x: x * 25.4),
        ):
            if value[field] != "M":
                out[name][k] = convert(float(value[field]))
    return out


def grid_hours(store: GridStore, cell: tuple[int, int]) -> dict[str, np.ndarray]:
    return {name: store.read_point(name, *cell) for name in ("air_temperature", "dew_point", "precipitation")}


def ours(hours: dict[str, np.ndarray], year: int, latitude: float, last: date):
    first = date(year, 1, 1)
    names = required_inputs_list()
    daily = daily_at_point(datetime(year, 1, 1, tzinfo=UTC), hours, GRID_ZONE, first, last, names=names)
    dates = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    return run("apple-scab", dates=dates, daily={n: daily[n] for n in names}, latitude=latitude, gap_fill=GAP_FILL)


def required_inputs_list() -> list[str]:
    from agmodels.registry import model

    return required_inputs(model("apple-scab"))


def newa(path: Path, year: int):
    hours = load_hours(path, until=datetime(year, 10, 30, 23, tzinfo=LOCAL))
    days = make_days(hours)
    result = scab(hours, days)
    gt = result["green_tip"]
    if gt is None:
        return None
    first_day = date(year, 1, 1)
    to_date = lambda d: date.fromordinal(first_day.toordinal() + d - 1)  # noqa: E731
    mature = next((m["date"] for m in result["maturity"] if m["maturity"] >= 95), None)
    released = next((m["date"] for m in result["maturity"] if m["all_released"]), None)
    events = []
    for e in result["infections"]:
        a = datetime.fromtimestamp(e.start_ms / 1000, LOCAL).date()
        b = datetime.fromtimestamp(e.end_ms / 1000, LOCAL).date()
        if a <= date(year, *SEASON_END):
            events.append((a, b))
    as_date = lambda s: datetime.strptime(s, "%m/%d/%Y").replace(tzinfo=UTC).date() if s else None  # noqa: E731
    return {"green_tip": to_date(gt.doy), "mature": as_date(mature), "released": as_date(released), "events": events}


def summary_of(result) -> dict | None:
    if result.biofix is None or not result.outputs:
        return None
    o = result.outputs
    dates = result.dates

    def first(mask):
        idx = np.flatnonzero(mask)
        return dates[int(idx[0])] if idx.size else None

    end = date(dates[0].year, *SEASON_END)
    infection = [d for d, x in zip(dates, o["infection"], strict=True) if x == 1 and d <= end and d >= result.biofix]
    return {
        "green_tip": result.biofix,
        "mature": first(o["maturity"] >= 95),
        "released": first(o["season"] == 1),
        "events": infection,
    }


def match(newa_events, our_days):
    """(NEWA's matched, NEWA's missed, ours unmatched)."""
    used = set()
    hit = 0
    for a, b in newa_events:
        found = [d for d in our_days if a - timedelta(days=1) <= d <= b + timedelta(days=1) and d not in used]
        if found:
            hit += 1
            used.add(found[0])
    return hit, len(newa_events) - hit, len([d for d in our_days if d not in used])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tmp/newa/validation-apple-scab.md")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    stores: dict[int, GridStore] = {}
    lines = [
        "# Apple scab: ours against NEWA's on Wisconsin's orchard stations",
        "",
        "Written by `scripts/check_apple_scab.py`. NEWA: its rules on the station's hours and leaf wetness sensor (`scripts/newa_reference.py`). Ours: the station's own hours with wetness estimated (RH ≥ 90 % or rain), and the archive's hours at the station's cell. Green tip through June 30. Days: NEWA's on the local clock, ours on CST.",
        "",
        "| Station | Year | Green tip NEWA / station / grid | 95 % mature | Season over | NEWA infections | Station: hit / missed / extra | Grid: hit / missed / extra |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    totals = {"station": np.zeros(3, int), "grid": np.zeros(3, int)}
    gt_diffs = {"station": [], "grid": []}
    left_out = []
    for path in sorted((CACHE / "hours").glob("*.json")):
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        if year >= 2026:
            continue  # NEWA's season isn't complete in our fetch
        station = stations[sid]
        cell = NDFD.cell_of(station["lat"], station["lon"])
        if cell is None:
            continue
        reference = newa(path, year)
        if reference is None:
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
        ratio = np.nansum(s_hours["precipitation"][spring]) / g_rain if g_rain > 25 else 1.0
        last = date(year, 7, 31)
        runs = {
            "station": summary_of(ours(s_hours, year, station["lat"], last)),
            "grid": summary_of(ours(g_hours, year, station["lat"], last)),
        }
        if runs["station"] is None or runs["grid"] is None:
            continue
        counts = {k: match(reference["events"], r["events"]) for k, r in runs.items()}
        bad = ratio < GAUGE_MIN_RATIO
        if bad:
            left_out.append(f"{sid} {year} ({ratio:.0%})")
        else:
            for k in totals:
                totals[k] += counts[k]
                gt_diffs[k].append((runs[k]["green_tip"] - reference["green_tip"]).days)

        def fmt(d):
            return "–" if d is None else f"{d:%b %-d}"

        lines.append(
            f"| {station['name']}{' (gauge)' if bad else ''} | {year} | {fmt(reference['green_tip'])} / {fmt(runs['station']['green_tip'])} / {fmt(runs['grid']['green_tip'])} | {fmt(reference['mature'])} / {fmt(runs['station']['mature'])} / {fmt(runs['grid']['mature'])} | {fmt(reference['released'])} / {fmt(runs['station']['released'])} / {fmt(runs['grid']['released'])} | {len(reference['events'])} | {' / '.join(map(str, counts['station']))} | {' / '.join(map(str, counts['grid']))} |"
        )
        print(lines[-1], flush=True)
    lines += ["", "## Totals (stations with working gauges)", ""]
    for k, (hit, missed, extra) in totals.items():
        n = hit + missed
        lines.append(
            f"- {k} hours: {hit} of {n} NEWA infections matched ({hit / max(n, 1):.0%}), {extra} of ours not in NEWA's; green tip ours − NEWA's: mean {np.mean(gt_diffs[k]):+.1f} days, range {min(gt_diffs[k]):+d} to {max(gt_diffs[k]):+d}"
        )
    if left_out:
        lines.append(f"- Left out for a failed gauge: {', '.join(left_out)}")
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-4:]))


if __name__ == "__main__":
    main()
