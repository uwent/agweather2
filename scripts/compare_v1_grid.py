"""v1's daily weather grid against v2's `/grids` on the same 0.1° points (PLAN.md Phase 5 E, the R grid caller).

uv run python scripts/compare_v1_grid.py --start 2026-04-01 --end 2026-10-27 [--every 7] [--out FILE]

(FILE defaults to docs/validation-v1-grid.md.)

v1's `/api/weather/grid?date=` (Ben's alfalfa Shiny app, about once a day) returns each 0.1° point's daily values.
v2 answers the same question with one general request per variable: `/grids/{variable}?date=&grid=latlon&res=0.1&
method=mean`, the mean of the 2.5 km cells within ±0.05° of each point (v1 averaged the cells whose lat/lon rounds
to the point, the same boxes). This checks that the request serves the caller and records how the values differ, for
the migration guide (Phase 8). v1 is a reference, not the truth (D54). Differences expected: v1 reads RTMA, v2 URMA;
v1's day is the Central-time hours 00–23 (with daylight saving), v2's midnight to midnight CST all year (D74);
v2 counts RH ≥ 88% as "over 90" (D50).

v2 is called in process on the archive in `DATA_DIR`; v1's grids come from tmp/legacy-cache (fetched once, one at a
time, if missing: it's a production server). `--quiet` prints only warnings, failures and the summary.
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

# v1's field → v2's layer (both in °F, % or hours)
FIELDS = {
    "min_temp": "air_temperature_min",
    "max_temp": "air_temperature_max",
    "avg_temp": "air_temperature_mean",
    "dew_point": "dew_point_mean",
    "min_rh": "relative_humidity_min",
    "max_rh": "relative_humidity_max",
    "avg_rh": "relative_humidity_mean",
    "hours_rh_over_90": "hours_rh_over_90",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--every", type=int, default=7, help="compare every nth day (default 7)")
    parser.add_argument("--out", default="docs/validation-v1-grid.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    try:
        first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    except ValueError as error:
        parser.error(f"--start and --end must be YYYY-MM-DD dates: {error}")
    if first > last or args.every < 1:
        parser.error("--start must not be after --end, and --every must be at least 1")
    old = AgWeatherV1(cache_dir=REPO / "tmp/legacy-cache")
    v2 = Client(HTTP_HOST="localhost")
    days = [first + timedelta(days=k) for k in range(0, (last - first).days + 1, args.every)]
    report.step(f"{len(days)} days from {first} to {last}, every {args.every}")
    differences: dict[str, list[np.ndarray]] = {field: [] for field in FIELDS}
    points_compared = []
    for n, day in enumerate(days):
        try:
            v1 = old.weather(day)
        except Exception as error:  # production server: a failed day is reported, not fatal
            report.fail(f"v1 grid {day}", error)
            continue
        for field, layer in FIELDS.items():
            answer = v2.get(
                f"/api/v2/grids/{layer}", {"date": day, "grid": "latlon", "res": 0.1, "method": "mean"}
            ).json()
            if "errors" in answer:
                report.fail(f"v2 {layer} {day}", str(answer["errors"]))
                continue
            data = answer["data"]
            ours = {
                f"[{lat:.1f}, {lng:.1f}]": value
                for lat, lng, value in zip(data["lat"], data["lng"], data[layer], strict=True)
            }
            pairs = [
                (ours[key], values[field])
                for key, values in v1.items()
                if key in ours and ours[key] is not None and values.get(field) is not None
            ]
            if pairs:
                a = np.array(pairs, dtype=float)
                differences[field].append(a[:, 0] - a[:, 1])
                if field == "max_temp":
                    points_compared.append(len(pairs))
        report.progress("days", n + 1, len(days))
    text = _report(first, last, args.every, differences, points_compared)
    Path(args.out).write_text(text)
    report.step(f"wrote {args.out}")
    return 0 if report.finish(f"compared {len(points_compared)} days") else 1


def _report(first: date, last: date, every: int, differences: dict, points: list[int]) -> str:
    rows = []
    for field, layer in FIELDS.items():
        if not differences[field]:
            continue
        d = np.concatenate(differences[field])
        rows.append(
            f"| {field} | `{layer}` | {d.size:,} | {d.mean():+.2f} | {np.abs(d).mean():.2f} | "
            f"{np.percentile(d, 5):+.1f} | {np.percentile(d, 95):+.1f} |"
        )
    mean_points = round(float(np.mean(points))) if points else 0
    return "\n".join(
        [
            "# v1's weather grid against v2's `/grids`",
            "",
            f"Generated by `scripts/compare_v1_grid.py --start {first} --end {last} --every {every}`: every {every}th "
            f"day, {len(points)} days, ~{mean_points:,} shared 0.1° points a day. v1 is `/api/weather/grid?date=` "
            "(the alfalfa Shiny app's request); v2 is one "
            "`/api/v2/grids/{layer}?date=&grid=latlon&res=0.1&method=mean` per variable. Differences are v2 − v1 "
            "(°F, %, hours); v1 is a reference, not the truth (D54).",
            "",
            "| v1 field | v2 layer | pairs | mean | MAE | P5 | P95 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "Expected sources of difference: v1 reads RTMA, v2 URMA; v1's day is the Central-time hours 00–23, "
            "following daylight saving, v2's midnight to midnight CST all year (D74), so from March to November "
            "v2's day ends an hour later (maps have no `day_basis=local`; at DATCP's points, asking v2 for v1's "
            "days brings the minimum's MAE back to about 0.5 °F, `validation-v1.md`); v2's hours over 90% count "
            "RH ≥ 88% (D50), the threshold that matches in-field sensors. v1's `avg_temp_rh_over_90`, "
            "`vapor_pressure`, `frost` and `freezing` have no v2 layer: the first is the disease models' (v2 keeps "
            "it for the day from 6 pm), the others follow from the temperatures and dew point.",
            "",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
