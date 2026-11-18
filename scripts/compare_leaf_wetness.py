"""Leaf wetness estimated from weather against NEWA's orchard sensors (docs/models-plan.md part B5).

Apple scab and fire blight need wet hours, which the grid has no sensor for. At Wisconsin's NEWA orchard
stations (hours fetched by scripts/fetch_newa.py into tmp/newa/hours/), each candidate estimate is run on two sets
of inputs: the station's own hours (which isolates the method) and the archive's hours at the station's cell (what
the maps will use). The truth is the station's sensor: an hour is wet when it read wet for at least 30 minutes
(Kim et al. 2002; Batzer et al. 2008). Only hours the station observed (NEWA's flag blank for temperature, RH,
precipitation and leaf wetness) are scored.

Candidates (each also counts an hour with at least 0.01 in of rain as wet, and is run without that rule too):
- RH at or above a threshold (80–95 %);
- dew point depression with an onset and a dry-off limit (wet from depression ≤ onset until it rises above dry-off;
  Gillespie et al. 1993);
- CART/SLD (Gleason et al. 1994), with the 10 m wind scaled to the height it was fitted at (factors 0.415–1.0;
  Kim et al. 2002 brought it to 0.3 m), √T taken as √max(T, 0) below freezing.

Scores: hours (share right, hit rate, false alarm ratio), wet hours a day (bias, mean absolute error; dew-only
days and rain days apart), and events: apple scab infection events by NEWA's rules (an event starts at an hour
both wet and raining, continues while wet or raining, events under 24 h apart merge, infection when the wet hours
reach NEWA's Revised Mills table at the event's mean temperature) and fire blight wetting days (2 wet hours or
more, Smith and Pusey 2011), as Cohen's kappa over station-days against the same rules on the sensor.

    uv run python scripts/compare_leaf_wetness.py --years 2024 2025 2026

`--quiet` prints only warnings, failures and the summary.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import VARIABLES
from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.store import HOURLY, GridStore

CACHE = Path("tmp/newa")
HOUR = timedelta(hours=1)
CST = timedelta(hours=-6)
WET_MINUTES = 30
# A station whose gauge caught less than this share of the archive's April–June rain is left out: a failed or blocked
# tipping bucket reads zero with an "observed" flag (Gays Mills 2025 recorded 0.26 in against the archive's 14)
GAUGE_MIN_RATIO = 0.4
RAIN_MM = 0.254  # 0.01 in
MPH = 0.44704
FIELDS = ["prcp", "temp", "rhum", "dwpt", "lwet", "wspd", "wdir", "srad"]  # NEWA's flag characters, in order
# NEWA's Revised Mills table (°F of the event's mean, rounded → wet hours for infection), read from NEWA 3.0's
# apple scab page (newa.cornell.edu), which follows MacHardy and Gadoury (1989).
MILLS_F = {
    34: 41,
    35: 41,
    36: 35,
    37: 30,
    38: 30,
    39: 28,
    40: 28,
    41: 21,
    42: 21,
    43: 18,
    44: 18,
    45: 15,
    46: 13,
    47: 13,
    48: 12,
    49: 12,
    50: 11,
    51: 11,
    52: 9,
    53: 9,
    54: 8,
    55: 8,
    56: 8,
    57: 7,
    58: 7,
    59: 7,
    60: 7,
}
MILLS_F |= dict.fromkeys(range(61, 77), 6) | {77: 8, 78: 8, 79: 11}
SEASONS = {"April–June": (4, 5, 6), "July–September": (7, 8, 9)}


@dataclass(kw_only=True)
class Inputs:
    t: np.ndarray  # °C
    td: np.ndarray  # °C
    rh: np.ndarray  # %
    wind: np.ndarray  # m/s as measured
    rain: np.ndarray  # mm


@dataclass(kw_only=True)
class Season:
    station: str
    year: int
    hours: np.ndarray  # UTC hour endings
    truth: np.ndarray  # 1.0 wet, 0.0 dry, NaN not observed
    station_inputs: Inputs
    grid_inputs: Inputs
    observed: np.ndarray  # the station observed T, RH, rain and wetness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="+", required=True)
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation/weather/leaf-wetness.md")
    parser.add_argument("--quiet", action="store_true", help="print only warnings, failures and the summary")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    stations = {s["id"]: s for s in json.loads((CACHE / "stations.json").read_text())}
    files = sorted(f for year in args.years for f in (CACHE / "hours").glob(f"*_{year}.json"))
    if not files:
        report.fail("hours", f"no station hours for {args.years} in {CACHE / 'hours'}: run scripts/fetch_newa.py first")
        sys.exit(1)
    report.step(f"leaf wetness: {len(files)} station-seasons; writing {args.out}")
    seasons: list[Season] = []
    gauge_failures: list[str] = []
    stores: dict[int, GridStore] = {}
    for n, path in enumerate(files, start=1):
        name, year_text = path.stem.rsplit("_", 1)
        sid, year = " ".join(name.rsplit("_", 1)), int(year_text)
        try:
            season = load(path=path, station=stations[sid], year=year, stores=stores, data=Path(args.data))
        except Exception as error:  # one station-season's failure shouldn't stop the rest
            report.fail(f"{sid} {year}", error)
            continue
        if season is None:
            report.detail(f"{sid} {year}: no observed hours with a wetness reading")
        elif (gauge := gauge_ratio(season)) is not None and gauge < GAUGE_MIN_RATIO:
            report.warn(
                f"{sid} {year}: left out, its rain gauge caught {gauge:.0%} of the archive's rain at its cell in April–June (a failed or blocked gauge)"
            )
            gauge_failures.append(f"{sid} {year} ({gauge:.0%})")
        else:
            report.detail(f"{sid} {year}: {int(np.isfinite(season.truth).sum())} observed hours")
            seasons.append(season)
        report.progress("station-seasons", n, len(files))
    report.step(f"scoring {len(candidates())} estimates on {len(seasons)} station-seasons")
    text = build_report(seasons=seasons, years=args.years, report=report)
    if gauge_failures:
        text += f"\nLeft out for a failed rain gauge (observed April–June rain under {GAUGE_MIN_RATIO:.0%} of the archive's at the cell): {', '.join(gauge_failures)}. The truth's scab events need the station's rain, so a gauge reading near zero would hide them.\n"
    Path(args.out).write_text(text)
    report.step(f"wrote {args.out}")
    sys.exit(0 if report.finish(f"{len(seasons)} station-seasons") else 1)


def gauge_ratio(season: Season) -> float | None:
    """The station's observed April–June rain as a share of the archive's at its cell over the same hours, or None
    when the archive had under an inch (too little to judge)."""
    months = np.array([h.month in (4, 5, 6) for h in season.hours])
    hours = months & season.observed & np.isfinite(season.station_inputs.rain) & np.isfinite(season.grid_inputs.rain)
    grid = season.grid_inputs.rain[hours].sum()
    return None if grid < 25.4 else float(season.station_inputs.rain[hours].sum() / grid)


def load(path: Path, station: dict, year: int, stores: dict[int, GridStore], data: Path) -> Season | None:
    raw = json.loads(path.read_text())
    rows = raw.get("hrlyData") or []
    if not rows:
        return None
    fields = raw["hrlyFields"]
    col = {name: fields.index(name) for name in ("date", "flags", *FIELDS)}
    start = datetime(year, 1, 1, tzinfo=UTC)
    n = int((datetime(year + 1, 1, 1, tzinfo=UTC) - start) / HOUR)
    values = {name: np.full(n, np.nan) for name in ("prcp", "temp", "rhum", "dwpt", "lwet", "wspd")}
    observed = np.zeros(n, dtype=bool)
    for row in rows:
        when = datetime.fromisoformat(row[col["date"]]).astimezone(UTC)
        k = int((when - start) / HOUR)
        if not 0 <= k < n:
            continue
        flags = row[col["flags"]].ljust(len(FIELDS))
        for name in values:
            text = row[col[name]]
            if text not in ("M", ""):
                values[name][k] = float(text)
        observed[k] = all(flags[FIELDS.index(name)] == " " for name in ("prcp", "temp", "rhum", "lwet"))
    lwet = values["lwet"]
    truth = np.where(np.isfinite(lwet) & observed, (lwet >= WET_MINUTES).astype(float), np.nan)
    if not np.isfinite(truth).any():
        return None
    t = (values["temp"] - 32) / 1.8
    station_inputs = Inputs(
        t=t,
        td=(values["dwpt"] - 32) / 1.8,
        rh=np.minimum(values["rhum"], 100),
        wind=values["wspd"] * MPH,
        rain=values["prcp"] * 25.4,
    )
    cell = NDFD.cell_of(station["lat"], station["lon"])
    if cell is None:
        raise ValueError(f"{station['id']} is outside the grid")
    if year not in stores:
        names = ["air_temperature", "dew_point", "relative_humidity", "wind_speed", "precipitation"]
        stores[year] = GridStore.open(data, HOURLY, year, [VARIABLES[v] for v in names])
    store = stores[year]
    j, i = cell  # step k of the year's store is the hour ending k hours after January 1 00:00 UTC, as here

    def grid(name: str) -> np.ndarray:
        out = np.full(n, np.nan)
        series = store.read_point(name, j, i, 0, min(n, store.length))
        out[: len(series)] = series
        return out

    grid_inputs = Inputs(
        t=grid("air_temperature"),
        td=grid("dew_point"),
        rh=np.minimum(grid("relative_humidity"), 100),
        wind=grid("wind_speed"),
        rain=grid("precipitation"),
    )
    hours = np.array([start + k * HOUR for k in range(n)])
    return Season(
        station=station["id"],
        year=year,
        hours=hours,
        truth=truth,
        station_inputs=station_inputs,
        grid_inputs=grid_inputs,
        observed=observed,
    )


# The estimates


def rh_at_least(threshold: float) -> Callable[[Inputs], np.ndarray]:
    return lambda x: np.where(np.isfinite(x.rh), x.rh >= threshold, np.nan)


def dew_point_depression(onset: float, dry: float) -> Callable[[Inputs], np.ndarray]:
    """Wet from the hour the depression falls to `onset` or below until it rises above `dry` (°C)."""

    def estimate(x: Inputs) -> np.ndarray:
        d = x.t - x.td
        out = np.full(len(d), np.nan)
        wet = False
        for k, value in enumerate(d):
            if not np.isfinite(value):
                wet = False
                continue
            wet = value <= dry if wet else value <= onset
            out[k] = wet
        return out

    return estimate


def cart(wind_factor: float) -> Callable[[Inputs], np.ndarray]:
    """CART/SLD (Gleason et al. 1994, Plant Dis. 78:1011, Fig. 2), °C, %, m/s; wind scaled by `wind_factor`."""

    def estimate(x: Inputs) -> np.ndarray:
        t, rh, w = x.t, x.rh, x.wind * wind_factor
        d = t - x.td
        root = np.sqrt(np.maximum(t, 0))
        calm = 1.6064 * root + 0.0036 * t**2 + 0.1531 * rh - 0.4599 * w * d - 0.0035 * t * rh > 14.4674
        windy = 0.7921 * root + 0.0046 * rh**2 - 2.3889 * w - 0.0390 * t * w + 1.0613 * w * d > 37.0
        wet = np.where(d >= 3.7, False, np.where(w < 2.5, calm, np.where(rh < 87.8, False, windy)))
        known = np.isfinite(t) & np.isfinite(rh) & np.isfinite(w) & np.isfinite(d)
        return np.where(known, wet, np.nan)

    return estimate


def with_rain(estimate: Callable[[Inputs], np.ndarray]) -> Callable[[Inputs], np.ndarray]:
    def combined(x: Inputs) -> np.ndarray:
        wet = estimate(x)
        return np.where(x.rain >= RAIN_MM, 1.0, wet)

    return combined


def candidates() -> dict[str, Callable[[Inputs], np.ndarray]]:
    base: dict[str, Callable[[Inputs], np.ndarray]] = {}
    for threshold in range(80, 96):
        base[f"RH ≥ {threshold}"] = rh_at_least(threshold)
    for onset, dry in [
        (1.8, 2.2),
        (2.0, 3.8),
        (2.0, 4.3),
        (1.0, 2.0),
        (1.5, 3.0),
        (2.5, 4.0),
        (3.0, 4.5),
        (3.0, 5.0),
        (3.5, 5.0),
        (4.0, 5.5),
    ]:
        base[f"DPD {onset}/{dry}"] = dew_point_depression(onset, dry)
    for factor in (0.415, 0.6, 0.8, 1.0):
        base[f"CART × {factor}"] = cart(factor)
    out = {}
    for name, estimate in base.items():
        out[f"{name} + rain"] = with_rain(estimate)
        out[name] = estimate
    return out


# Events (NEWA's rules)


def scab_event_days(wet: np.ndarray, rain: np.ndarray, t: np.ndarray, day: np.ndarray) -> set[int]:
    """The days on which a scab infection event starts, by NEWA's rules (rain ≥ 0.01 in counts as raining)."""
    raining = rain >= RAIN_MM
    events: list[list[float]] = []  # [start, end, hours, sum of °F]
    k, n = 0, len(wet)
    while k < n:
        if wet[k] == 1 and raining[k]:
            begin, hours, total = k, 0, 0.0
            while k < n and (wet[k] == 1 or raining[k]):
                if np.isfinite(t[k]):
                    hours += 1
                    total += t[k] * 1.8 + 32
                k += 1
            if events and begin - events[-1][1] < 24:
                events[-1][1] = k
                events[-1][2] += hours
                events[-1][3] += total
            else:
                events.append([begin, k, hours, total])
        else:
            k += 1
    found = set()
    for begin, _, hours, total in events:
        if hours == 0:
            continue
        mean = round(total / hours)
        if 34 <= mean <= 79 and hours >= MILLS_F[mean]:
            found.add(int(day[int(begin)]))
    return found


def wetting_days(wet: np.ndarray, day: np.ndarray, days: np.ndarray) -> set[int]:
    counts = (
        np.bincount(day[wet == 1], minlength=int(days.max()) + 1) if (wet == 1).any() else np.zeros(int(days.max()) + 1)
    )
    return {int(d) for d in days if counts[d] >= 2}


def kappa(a: set[int], b: set[int], days: np.ndarray) -> tuple[float, int, int, int]:
    """Cohen's kappa over `days`, and (both, truth only, estimate only)."""
    universe = {int(d) for d in days}
    a, b = a & universe, b & universe
    n = len(universe)
    both, only_a, only_b = len(a & b), len(a - b), len(b - a)
    neither = n - both - only_a - only_b
    po = (both + neither) / n
    pe = ((both + only_a) * (both + only_b) + (neither + only_b) * (neither + only_a)) / n**2
    return ((po - pe) / (1 - pe) if pe < 1 else float("nan")), both, only_a, only_b


# The report


@dataclass(kw_only=True)
class Score:
    hours: int = 0
    right: int = 0
    hits: int = 0
    wet: int = 0
    called: int = 0
    day_errors: list[float] | None = None
    day_errors_dew: list[float] | None = None
    day_errors_rain: list[float] | None = None
    scab: tuple[set[int], set[int], list[int]] | None = None


def build_report(seasons: list[Season], years: list[int], report: Reporter) -> str:
    methods = candidates()
    lines = ["# Leaf wetness estimated from weather, against NEWA's orchard sensors", ""]
    lines += [
        f"Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/compare_leaf_wetness.py` (docs/models-plan.md part B5), on the hours of {min(years)}–{max(years)}. Apple scab and fire blight need the hours a leaf is wet, which the archive has no sensor for, so the models estimate wetness from humidity, dew point, wind and rain. This compares {len(methods)} candidate estimates with the leaf wetness sensors at the Wisconsin orchard stations of NEWA (the Network for Environment and Weather Applications, Cornell University; hourly station data from newa.cornell.edu), to choose the estimate the models use and to measure its errors.",
        "",
        "The truth is each NEWA station's leaf wetness sensor (an hour wet at 30 minutes or more); only hours the station observed are scored. Each estimate runs on the station's own hours and on the archive's hours at the station's cell. Event scores are Cohen's kappa over station-days: apple scab infection events by NEWA's rules (both sides use the station's rain and temperature on station inputs, the archive's on grid inputs; the truth always uses the sensor with the station's rain and temperature) and fire blight wetting days (2 wet hours or more).",
        "",
        f"{len(seasons)} station-seasons: {', '.join(sorted({s.station.split()[0] for s in seasons}))}.",
        "",
    ]
    for label, months in SEASONS.items():
        for source in ("station", "grid"):
            report.step(f"{label}, {source} inputs")
            rows = []
            for name, estimate in methods.items():
                rows.append((name, *score(seasons=seasons, estimate=estimate, months=months, source=source)))
            rows.sort(key=lambda r: -r[8] if np.isfinite(r[8]) else 0)  # by the scab events κ
            lines += [f"## {label}, {source} inputs", "", "<!-- prettier-ignore -->"]
            lines += [
                "| Estimate | Hours right | Hit rate | False alarms | Wet h/day bias | MAE h/day | MAE dew days | MAE rain days | Scab events κ (both / sensor only / estimate only) | Wetting days κ |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
            for name, right, pod, far, bias, mae, mae_dew, mae_rain, scab, scab_counts, wetting in rows:
                both, only_t, only_e = scab_counts
                lines.append(
                    f"| {name} | {right:.3f} | {pod:.3f} | {far:.3f} | {bias:+.2f} | {mae:.2f} | {mae_dew:.2f} | {mae_rain:.2f} | {scab:.3f} ({both} / {only_t} / {only_e}) | {wetting:.3f} |"
                )
            lines.append("")
    return "\n".join(lines)


def score(seasons: list[Season], estimate: Callable[[Inputs], np.ndarray], months: tuple[int, ...], source: str):
    right = hits = wet_true = called = hours = 0
    errors, errors_dew, errors_rain = [], [], []
    scab_truth: set[int] = set()
    scab_est: set[int] = set()
    wet_truth: set[int] = set()
    wet_est: set[int] = set()
    all_days: list[int] = []
    for s_index, s in enumerate(seasons):
        x = s.station_inputs if source == "station" else s.grid_inputs
        est = estimate(x)
        local = s.hours + CST
        month = np.array([h.month for h in local])
        in_season = np.isin(month, months)
        day = np.array([h.timetuple().tm_yday for h in local]) + 1000 * s_index  # CST days, unique per season
        ok = in_season & np.isfinite(s.truth) & np.isfinite(est)
        truth, guess = s.truth[ok] == 1, est[ok] == 1
        hours += int(ok.sum())
        right += int((truth == guess).sum())
        hits += int((truth & guess).sum())
        wet_true += int(truth.sum())
        called += int(guess.sum())
        # days with at least 20 scored hours
        days_ok = day[ok]
        station_rain = np.where(np.isfinite(s.station_inputs.rain), s.station_inputs.rain, 0)
        good_days = []
        for d in np.unique(days_ok):
            m = days_ok == d
            if m.sum() < 20:
                continue
            good_days.append(int(d))
            e = float(guess[m].sum() - truth[m].sum())
            errors.append(e)
            rained = station_rain[day == d].sum() >= RAIN_MM
            (errors_rain if rained else errors_dew).append(e)
        all_days += good_days
        # events, on the season's hours (gaps in the sensor end events on both sides)
        sensor = np.where(s.observed, s.truth, np.nan)
        scab_truth |= scab_event_days(
            wet=np.nan_to_num(sensor, nan=0),
            rain=np.nan_to_num(s.station_inputs.rain, nan=0),
            t=s.station_inputs.t,
            day=day,
        )
        scab_est |= scab_event_days(
            wet=np.nan_to_num(np.where(np.isfinite(sensor), est, np.nan), nan=0),
            rain=np.nan_to_num(x.rain, nan=0),
            t=x.t,
            day=day,
        )
        wet_truth |= wetting_days(
            wet=np.nan_to_num(np.where(ok, s.truth, np.nan), nan=0), day=day, days=np.array(good_days or [0])
        )
        wet_est |= wetting_days(
            wet=np.nan_to_num(np.where(ok, est, np.nan), nan=0), day=day, days=np.array(good_days or [0])
        )
    days = np.array(all_days)
    k_scab, both, only_t, only_e = kappa(scab_truth, scab_est, days)
    k_wet = kappa(wet_truth, wet_est, days)[0]
    e = np.array(errors)
    return (
        right / hours,
        hits / max(wet_true, 1),
        1 - hits / max(called, 1),
        float(e.mean()),
        float(np.abs(e).mean()),
        float(np.abs(errors_dew).mean()) if errors_dew else float("nan"),
        float(np.abs(errors_rain).mean()) if errors_rain else float("nan"),
        k_scab,
        (both, only_t, only_e),
        k_wet,
    )


if __name__ == "__main__":
    main()
