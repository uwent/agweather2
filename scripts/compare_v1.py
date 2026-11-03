"""v1's point callers against v2 (PLAN.md Phase 5 C): DATCP's degree-day report, ET and precip at points.

uv run python scripts/compare_v1.py --start 2026-01-01 --end 2026-10-31 [--out docs/validation-v1.md]

At DATCP's 23 points (from the old server's logs), over the window:

- **Degree days:** DATCP's eight settings, each point's v1 total (`/api/degree_days`, one request per point and
  setting, as DATCP sends them) against v2's `/degree-days/table` (one request for all of them), and each day's
  v1 min and max temperature against v2's, which explain most of the difference.
- **ET:** v1's `/api/evapotranspirations` (its own method, Diak et al. 1998, and `method=adjusted`) against v2's
  FAO-56 grass reference ET0 (`/weather/totals`' `et0_sum`).
- **Precip:** v1's `/api/precips` against v2's `precipitation_sum`.

v1 is a reference, not the truth (D54): the report says where and how much they differ. v2 is called in process (no
server needed) on the archive in `DATA_DIR`; v1's responses are cached in tmp/v1-cache (it's a production server:
requests go one at a time). `--quiet` prints only warnings, failures and the summary.
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ENV", "development")

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402

from agdata.clients.agweather_v1 import AgWeatherV1  # noqa: E402
from agdata.progress import Reporter  # noqa: E402

# DATCP's points and settings, as the old server's log has them (unchanged December 2024 and October 2026)
DATCP_POINTS = [
    (42.5, -89.0), (42.5, -90.7), (42.6, -87.9), (43.0, -88.2), (43.0, -88.6), (43.1, -88.0), (43.1, -89.5),
    (43.2, -90.2), (43.3, -88.4), (43.4, -88.7), (43.8, -91.2), (44.1, -89.5), (44.1, -89.8), (44.3, -88.4),
    (44.4, -89.9), (44.5, -88.1), (44.8, -91.5), (45.0, -89.6), (45.1, -90.4), (45.2, -88.0), (45.5, -92.0),
    (45.6, -88.9), (46.5, -90.1),
]  # fmt: skip
DATCP_SETTINGS = [  # (v2 name, v1 method, base, upper)
    ("average_43", "average", 43, None),
    ("average_50", "average", 50, None),
    ("average_52", "average", 52, None),
    ("modified_38_75", "modified", 38, 75),
    ("modified_40", "modified", 40, None),
    ("modified_50_86", "modified", 50, 86),
    ("sine_39_84", "sine", 39, 84),
    ("sine_48_86", "sine", 48, 86),
]
MM_PER_IN = 25.4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--out", default="docs/validation-v1.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last:
        parser.error("--start must not be after --end")
    old = AgWeatherV1(cache_dir=REPO / "tmp/v1-cache")
    v2 = Client(HTTP_HOST="localhost")
    window = {"start_date": str(first), "end_date": str(last)}
    points = ";".join(f"{lat},{lng}" for lat, lng in DATCP_POINTS)
    report.step(f"{len(DATCP_POINTS)} DATCP points, {first} to {last}")

    # Degree days: v1 one request per point and setting, v2 one for all
    table = v2.get(
        "/api/v2/degree-days/table",
        {"points": points, "dd": ",".join(s[0] for s in DATCP_SETTINGS), "start": first, "end": last},
    ).json()
    if "errors" in table:
        report.fail("v2 degree-day table", str(table["errors"]))
        report.finish()
        return 1
    v2_dd = {
        (p, s): dd
        for p, s, dd in zip(table["data"]["point"], table["data"]["setting"], table["data"]["dd"], strict=True)
    }
    v1_dd: dict[tuple[int, str], float] = {}
    v1_days: dict[int, list[dict]] = {}
    total = len(DATCP_POINTS) * len(DATCP_SETTINGS)
    for k, (lat, lng) in enumerate(DATCP_POINTS):
        for n, (name, method, base, upper) in enumerate(DATCP_SETTINGS):
            params = {"lat": lat, "lng": lng, "method": method, "base": base, **window}
            if upper is not None:
                params["upper"] = upper
            try:
                answer = old.point("degree_days", **params)
            except Exception as error:  # the server is production: a failed request is reported, not fatal
                report.fail(f"v1 degree days at {lat},{lng} {name}", error)
                continue
            v1_dd[k, name] = answer["info"]["total"]
            v1_days.setdefault(k, answer["data"])
            report.progress("v1 degree days", k * len(DATCP_SETTINGS) + n + 1, total)

    daily = v2.get(
        "/api/v2/weather/daily",
        {"points": points, "start": first, "end": last, "vars": "air_temperature_min,air_temperature_max"},
    ).json()["data"]
    temperature = _temperature_differences(daily, v1_days)

    # ET and precip totals
    totals = v2.get(
        "/api/v2/weather/totals",
        {"points": points, "start": first, "end": last, "vars": "et0_sum,precipitation_sum", "units": "metric"},
    ).json()["data"]
    v1_et, v1_et_adjusted, v1_rain = {}, {}, {}
    for k, (lat, lng) in enumerate(DATCP_POINTS):
        try:
            v1_et[k] = old.point("evapotranspirations", lat=lat, lng=lng, **window)["info"]["total"] * MM_PER_IN
            adjusted = old.point("evapotranspirations", lat=lat, lng=lng, method="adjusted", **window)
            v1_et_adjusted[k] = adjusted["info"]["total"] * MM_PER_IN
            v1_rain[k] = old.point("precips", lat=lat, lng=lng, units="mm", **window)["info"]["total"]
        except Exception as error:
            report.fail(f"v1 ET or precip at {lat},{lng}", error)
        report.progress("v1 ET and precip", k + 1, len(DATCP_POINTS))

    text = _report(first, last, v1_dd, v2_dd, temperature, totals, v1_et, v1_et_adjusted, v1_rain, table["meta"])
    Path(args.out).write_text(text)
    report.step(f"wrote {args.out}")
    return 0 if report.finish(f"compared {len(v1_dd)} degree-day totals") else 1


def _temperature_differences(daily: dict, v1_days: dict[int, list[dict]]) -> dict[str, np.ndarray]:
    """v2 − v1 daily min and max (°F) over every point and day both have."""
    v2 = {
        (p, d): (lo, hi)
        for p, d, lo, hi in zip(
            daily["point"], daily["date"], daily["air_temperature_min"], daily["air_temperature_max"], strict=True
        )
    }
    lows, highs = [], []
    for k, days in v1_days.items():
        for day in days:
            lo, hi = v2.get((k, day["date"]), (None, None))
            if lo is not None and day.get("min_temp") is not None:
                lows.append(lo - day["min_temp"])
            if hi is not None and day.get("max_temp") is not None:
                highs.append(hi - day["max_temp"])
    return {"min": np.array(lows), "max": np.array(highs)}


def _report(first, last, v1_dd, v2_dd, temperature, totals, v1_et, v1_et_adjusted, v1_rain, meta) -> str:
    lines = [
        "# v1's point callers against v2",
        "",
        f"Generated by `scripts/compare_v1.py --start {first} --end {last}` (PLAN.md Phase 5 C) at DATCP's 23 points.",
        "v1 is a reference, not the truth (D54): this says where and how much the two differ, for the migration",
        "guides (Phase 8). v2's sources over the window: " + ", ".join(meta["sources"]) + ".",
        "",
        "## Degree days (DATCP's report)",
        "",
        "Totals from the start of the window, °F·d. v2 − v1 over the 23 points:",
        "",
        "| setting | v1 mean | v2 mean | mean difference | range of differences | mean difference, % |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, *_ in DATCP_SETTINGS:
        pairs = [(v1_dd[k, name], v2_dd[k, name]) for k in range(len(DATCP_POINTS)) if (k, name) in v1_dd]
        if not pairs:
            continue
        a, b = np.array(pairs).T
        diff = b - a
        lines.append(
            f"| {name} | {a.mean():.0f} | {b.mean():.0f} | {diff.mean():+.0f} | {diff.min():+.0f} to "
            f"{diff.max():+.0f} | {100 * diff.mean() / a.mean():+.1f} |"
        )
    lines += [
        "",
        "Daily temperatures behind them, v2 − v1 (°F), every point and day:",
        "",
        "| | mean | MAE | 5th–95th percentile |",
        "| --- | --- | --- | --- |",
    ]
    for label, values in (("minimum", temperature["min"]), ("maximum", temperature["max"])):
        if values.size:
            lo, hi = np.percentile(values, [5, 95])
            lines.append(f"| {label} | {values.mean():+.2f} | {np.abs(values).mean():.2f} | {lo:+.1f} to {hi:+.1f} |")
    lines += [
        "",
        "## ET and precipitation",
        "",
        "Totals over the window, mm, averaged over the points (v2's ET is FAO-56 grass reference ET0; v1's is its own",
        "method, Diak et al. 1998, and `method=adjusted` its other emissivity):",
        "",
        "| | v1 | v1 adjusted | v2 | v2 / v1 |",
        "| --- | --- | --- | --- | --- |",
    ]
    points = range(len(DATCP_POINTS))
    et0 = np.array([totals["et0_sum"][k] for k in points if k in v1_et])
    et1 = np.array([v1_et[k] for k in points if k in v1_et])
    et1a = np.array([v1_et_adjusted[k] for k in points if k in v1_et_adjusted])
    rain2 = np.array([totals["precipitation_sum"][k] for k in points if k in v1_rain])
    rain1 = np.array([v1_rain[k] for k in points if k in v1_rain])
    if et1.size:
        lines.append(
            f"| ET | {et1.mean():.0f} | {et1a.mean():.0f} | {et0.mean():.0f} | {et0.mean() / et1.mean():.2f} |"
        )
    if rain1.size:
        lines.append(
            f"| precipitation | {rain1.mean():.0f} | | {rain2.mean():.0f} | {rain2.mean() / rain1.mean():.2f} |"
        )
    missing = sum(totals.get("precipitation_sum_missing_days", []))
    lines += ["", f"v2's missing precipitation days over all points: {missing}.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
