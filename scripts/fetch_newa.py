"""NEWA's station hours for the apple models' validation (docs/models-plan.md part B5).

NEWA (Cornell's Network for Environment and Weather Applications) serves its station list from
`newa.rcc-acis.workers.dev/v0/stations` and each station's hours from NRCC's `hrly.nrcc.cornell.edu/stnHrly`:
temperature (°F), RH (%), precipitation (in), leaf wetness (minutes of the hour), dew point, wind and solar, each
hour ending on the station's local clock, with a flag per value (blank observed, C calculated, I interpolated,
U filled from URMA, F forecast). Neither is documented, so requests are kept few: one per station-season,
January 1 to October 31, cached as received in tmp/newa/hours/<id>_<year>.json and never fetched again (the
current year's season is fetched again with --refresh).

    uv run python scripts/fetch_newa.py --years 2024 2025 2026
    uv run python scripts/fetch_newa.py --years 2025 --stations "wi_gay newa" "wi_bri newa"

By default, every Wisconsin station of NEWA's own network ("newa") with a leaf wetness sensor that was running in
the year. `--quiet` prints only warnings, failures and the summary.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

from agdata.clients.http import JsonClient
from agdata.progress import Reporter

CACHE = Path("tmp/newa")
STATIONS_URL = "https://newa.rcc-acis.workers.dev/v0"
HOURS_URL = "https://hrly.nrcc.cornell.edu"
USER_AGENT = "agweather-validation/1.0"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="+", required=True)
    parser.add_argument(
        "--stations", nargs="*", help="NEWA station ids (default: Wisconsin's NEWA stations with leaf wetness)"
    )
    parser.add_argument("--state", default="WI")
    parser.add_argument("--refresh", action="store_true", help="fetch the current year's seasons again")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    listing = JsonClient(STATIONS_URL, cache_dir=CACHE, session=session).get("stations", cache_key="stations.json")
    stations = chosen(listing=listing, ids=args.stations, state=args.state)
    if not stations:
        report.fail("stations", f"no stations match (state {args.state}, ids {args.stations})")
        sys.exit(1)
    jobs = [(s, year) for year in args.years for s in stations if running(station=s, year=year)]
    report.step(
        f"NEWA hours: {len(jobs)} station-seasons ({len(stations)} stations, {', '.join(map(str, args.years))}) into {CACHE / 'hours'}"
    )
    hours = JsonClient(HOURS_URL, pause_s=1.0, session=session)
    this_year = datetime.now(UTC).year
    fetched = kept = 0
    for n, (station, year) in enumerate(jobs, start=1):
        path = CACHE / "hours" / f"{station['id'].replace(' ', '_')}_{year}.json"
        if path.exists() and not (args.refresh and year == this_year):
            kept += 1
            report.progress("seasons", n, len(jobs))
            continue
        end = f"{year}103123" if year < this_year else "now"
        body = {
            "sid": station["id"],
            "sdate": f"{year}010100",
            "edate": end,
            "extraelems": station.get("extraelems", ""),
        }
        report.detail(f"{station['id']} {year} ==> POST stnHrly")
        try:
            data = hours.post("stnHrly", body)
        except Exception as error:  # one station's failure shouldn't stop the rest
            report.fail(f"{station['id']} {year}", error)
            continue
        if not data.get("hrlyData"):
            report.warn(f"{station['id']} {year}: no hours returned")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        fetched += 1
        report.progress("seasons", n, len(jobs))
    ok = report.finish(f"{fetched} fetched, {kept} already kept")
    sys.exit(0 if ok else 1)


def chosen(listing: list[dict], ids: list[str] | None, state: str) -> list[dict]:
    if ids:
        return [s for s in listing if s["id"] in ids]
    return [
        s for s in listing if s.get("state") == state and s["id"].endswith(" newa") and "lwet" in s.get("elems", {})
    ]


def running(station: dict, year: int) -> bool:
    """Whether the station could have hours that year: started by then (inactive stations may have stopped later, so
    they're asked anyway and come back empty)."""
    return int(station.get("startYear") or 0) <= year


if __name__ == "__main__":
    main()
