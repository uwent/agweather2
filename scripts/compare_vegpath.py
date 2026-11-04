"""Veg Path's v1 query against v2 (PLAN.md Phase 5 C and D): v1's `/api/pest_forecasts/vegpath` at the 7 points
Veg Path's site asks for, against v2's `/weather/daily` and `/models/run` (early blight P-days, late blight DSVs).

uv run python scripts/compare_vegpath.py --end 2026-09-30 [--out docs/validation-vegpath.md] [--quiet]

v1 answers a window from May 1 (or a month back, if earlier) to `--end`: daily min, max and mean temperature (°F) and
RH, precipitation (in), insolation (kWh/m²), ET (in), and each day's late blight DSV and P-days with their running
totals from the window's first day. v2 is called in process on the archive in `DATA_DIR`, and its models twice: as
they run (gridded RH ≥ 88% counted as a station's 90%, D50) and with the threshold put back at 90%, so the report
shows how much of the DSV difference D50 accounts for. Other known differences: v1's day is the calendar day's
hours, v2's late blight day runs from 8 pm (the Crop Risk Tool's window); v1 reads RTMA, v2 URMA.

v1 is a reference, not the truth (D54). Its responses are cached in tmp/v1-cache (one request at a time: it's a
production server).
"""

import argparse
import os
import sys
from datetime import date, timedelta
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
from agmodels import features  # noqa: E402

# Veg Path's points, as the old server's log has them (October 2026), with the newsletter's place names
POINTS = {
    "Spring Green": (43.2, -90.1),
    "Arlington": (43.3, -89.3),
    "Grand Marsh": (43.9, -89.7),
    "Hancock": (44.1, -89.5),
    "Plover": (44.4, -89.6),
    "Antigo": (45.1, -89.1),
    "Rhinelander": (45.7, -89.2),
}
WEATHER = {  # v1 field: (v2 daily variable, factor from v2's us units to v1's)
    "MinTempF": ("air_temperature_min", 1.0),
    "MaxTempF": ("air_temperature_max", 1.0),
    "AvgTempF": ("air_temperature_mean", 1.0),
    "MinRH": ("relative_humidity_min", 1.0),
    "MaxRH": ("relative_humidity_max", 1.0),
    "AvgRH": ("relative_humidity_mean", 1.0),
    "PrecipIn": ("precipitation_sum", 1.0),
    "EvapotranspirationIn": ("et0_sum", 1.0),
    "InsolationKWh": ("shortwave_radiation_sum", 1 / 3.6),  # MJ/m² (v2 shows it so in both systems) to kWh/m²
}
MODELS = "early-blight-pdays,late-blight-dsv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", required=True, help="last day, inclusive (v1's window starts May 1)")
    parser.add_argument("--out", default="docs/validation-vegpath.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        last = date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--end must be a YYYY-MM-DD date: {error}")
    first = min(last - timedelta(days=30), date(last.year, 5, 1)) if last.month >= 5 else last - timedelta(days=30)
    old = AgWeatherV1(cache_dir=REPO / "tmp/v1-cache")
    v2 = Client(HTTP_HOST="localhost")
    report.step(f"{len(POINTS)} Veg Path points, {first} to {last}")

    v1: dict[str, list[dict]] = {}
    for k, (place, (lat, lng)) in enumerate(POINTS.items()):
        try:
            v1[place] = old.point("pest_forecasts/vegpath", lat=lat, long=lng, date=str(last))  # type: ignore[assignment]
        except Exception as error:  # production server: a failed request is reported, not fatal
            report.fail(f"v1 vegpath at {place}", error)
        report.progress("v1 vegpath", k + 1, len(POINTS))

    points = ";".join(f"{lat},{lng}" for lat, lng in POINTS.values())
    names = ",".join(v for v, _ in WEATHER.values())
    daily = v2.get("/api/v2/weather/daily", {"points": points, "start": first, "end": last, "vars": names}).json()
    if "errors" in daily:
        report.fail("v2 weather", str(daily["errors"]))
        report.finish()
        return 1
    runs = {}
    for threshold in (features.STATION_RH_90_AS_GRIDDED, 90.0):
        features.STATION_RH_90_AS_GRIDDED = threshold
        for place, (lat, lng) in POINTS.items():
            body = v2.get(
                "/api/v2/models/run", {"lat": lat, "lng": lng, "models": MODELS, "start": first, "end": last}
            ).json()
            if "errors" in body:
                report.fail(f"v2 models at {place}", str(body["errors"]))
                continue
            runs[place, threshold] = body["data"]
        report.step(f"v2 models with gridded RH ≥ {threshold:g}% as a station's 90%")
    features.STATION_RH_90_AS_GRIDDED = 88.0

    text = _report(first, last, v1, daily["data"], runs)
    Path(args.out).write_text(text)
    report.step(f"wrote {args.out}")
    return 0 if report.finish(f"{len(v1)} of {len(POINTS)} points compared") else 1


def _v1_series(rows: list[dict], field: str, dates: list[str]) -> np.ndarray:
    by_date = {r["Date"]: r.get(field) for r in rows}
    return np.array([np.nan if by_date.get(d) is None else float(by_date[d]) for d in dates])


def _report(first: date, last: date, v1: dict, daily: dict, runs: dict) -> str:
    places = list(POINTS)
    point_of = np.array(daily["point"])
    dates_all = np.array(daily["date"])
    out = [
        "# Veg Path's v1 query against v2",
        "",
        f"Generated by `scripts/compare_vegpath.py --end {last}`: v1's `/api/pest_forecasts/vegpath` at the 7 points "
        f"Veg Path's site asks for, {first} to {last}, against v2's `/weather/daily` and `/models/run`. v1 is a "
        "reference, not the truth (D54): this says where and how much they differ. v2's DSVs are shown as they run "
        "(gridded RH ≥ 88% counted as a station's 90%, D50) and with the threshold at 90%.",
        "",
        "## Season totals",
        "",
        "From the window's first day, as v1's running totals count.",
        "",
        "| Place | DSV v1 | DSV v2 | DSV v2 at 90% | P-days v1 | P-days v2 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    diffs: dict[str, list[np.ndarray]] = {field: [] for field in WEATHER}
    dsv_days: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for k, place in enumerate(places):
        if place not in v1 or (place, 88.0) not in runs or (place, 90.0) not in runs:
            out.append(f"| {place} | (missing) | | | | |")
            continue
        mine = point_of == k
        dates = list(dates_all[mine])
        for field, (name, factor) in WEATHER.items():
            v2_values = np.array([np.nan if v is None else v for v in np.array(daily[name], dtype=object)[mine]], float)
            diffs[field].append(v2_values * factor - _v1_series(v1[place], field, dates))
        blight88 = runs[place, 88.0]["late-blight-dsv"]["data"]
        blight90 = runs[place, 90.0]["late-blight-dsv"]["data"]
        early = runs[place, 88.0]["early-blight-pdays"]["data"]
        model_dates = blight88["date"]
        v1_dsv, v1_pdays = _v1_series(v1[place], "DSV", model_dates), _v1_series(v1[place], "PDay", model_dates)
        dsv88 = np.array([np.nan if v is None else v for v in blight88["dsv"]], float)
        dsv90 = np.array([np.nan if v is None else v for v in blight90["dsv"]], float)
        pdays = np.array([np.nan if v is None else v for v in early["pdays"]], float)
        dsv_days.append((v1_dsv, dsv88, dsv90))
        out.append(
            f"| {place} | {np.nansum(v1_dsv):.0f} | {np.nansum(dsv88):.0f} | {np.nansum(dsv90):.0f} | "
            f"{np.nansum(v1_pdays):.0f} | {np.nansum(pdays):.0f} |"
        )
    out += ["", "## Daily DSVs", "", "Over every point and day with both.", ""]
    if dsv_days:
        v1d = np.concatenate([a for a, _, _ in dsv_days])
        for label, k in (("v2", 1), ("v2 at 90%", 2)):
            v2d = np.concatenate([t[k] for t in dsv_days])
            ok = np.isfinite(v1d) & np.isfinite(v2d)
            same = np.mean(v1d[ok] == v2d[ok])
            higher, lower = np.mean(v2d[ok] > v1d[ok]), np.mean(v2d[ok] < v1d[ok])
            out.append(
                f"- {label}: the same DSV on {same:.0%} of {ok.sum()} days, higher on {higher:.0%}, lower on "
                f"{lower:.0%}; mean difference {np.mean(v2d[ok] - v1d[ok]):+.2f} a day"
            )
    out += ["", "## Daily weather", "", "v2 − v1 over every point and day with both (v2 in us units).", ""]
    out += [
        "| v1 field | v2 variable | days | mean difference | mean absolute difference |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for field, (name, _) in WEATHER.items():
        d = np.concatenate(diffs[field]) if diffs[field] else np.array([])
        d = d[np.isfinite(d)]
        if d.size:
            out.append(f"| {field} | `{name}` | {d.size} | {d.mean():+.3f} | {np.abs(d).mean():.3f} |")
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
