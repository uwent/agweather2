"""Phase 2 H: v2's archive against the old AgWeather API, with v2 reduced the way the old API reduces RTMA.

uv run python scripts/compare_legacy.py --start 2025-01-01 --end 2025-03-29 [--out docs/validation-archive.md]

The old API (`../ag-weather`) averages, each hour, every 2.5 km cell whose lat/lon rounds to a 0.1° point, and
makes a day from the Central-time hours at 00:00 … 23:00 (for precip, the hours ending then). This reduces v2's
hourly store the same way, over points whose cells are all in Central time, so what remains is the source (URMA
in v2, RTMA in the old API) and QC. Old API responses are cached in tmp/legacy-cache (it's a production server:
requests go one at a time).
"""

import argparse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from agdata.catalog import VARIABLES
from agdata.clients.acis import Acis
from agdata.clients.agweather_v1 import AgWeatherV1, Bounds
from agdata.clients.openmeteo_daily import OpenMeteoDaily
from agdata.daily import cell_timezones, open_or_create_daily
from agdata.grid import NDFD, service_window
from agdata.store import HOURLY, GridStore
from agmodels.degree_days import degree_days_sine

CENTRAL = ZoneInfo("America/Chicago")
CACHE = Path("tmp/legacy-cache")
OLD_API = AgWeatherV1(cache_dir=CACHE)
PAIRS = [(50, 86), (39.2, 86)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="last day, inclusive")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="docs/validation-archive.md")
    args = parser.parse_args()
    first, last = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    data_dir = Path(args.data)
    window = service_window(args.box)

    points, labels = central_points(data_dir, window)
    print(f"{len(points)} old-API points with all their cells in Central time; {len(days)} days")
    period_start = datetime(first.year, first.month, first.day, tzinfo=CENTRAL).astimezone(UTC)
    period_stop = datetime(last.year, last.month, last.day, 23, tzinfo=CENTRAL).astimezone(UTC) + timedelta(hours=1)
    hourly = HourlyStores(data_dir, window, period_start, period_stop)
    v2 = {k: np.full((len(days), len(points)), np.nan) for k in ("tmin", "tmax", "tavg", "precip")}
    old = {k: np.full((len(days), len(points)), np.nan) for k in v2}
    for d, day in enumerate(days):
        hours = [datetime(day.year, day.month, day.day, h, tzinfo=CENTRAL).astimezone(UTC) for h in range(24)]
        temp = point_means(hourly.read("air_temperature", hours, window), labels, len(points)) * 1.8 + 32
        rain = point_means(hourly.read("precipitation", hours, window), labels, len(points))
        v2["tmin"][d], v2["tmax"][d], v2["tavg"][d] = temp.min(0), temp.max(0), temp.mean(0)
        v2["precip"][d] = rain.sum(0)
        weather = OLD_API.weather(day, bounds(window))
        precip = OLD_API.precipitation_mm(day, bounds(window))
        for p, key in enumerate(points):
            w = weather.get(key)
            if w:
                old["tmin"][d, p], old["tmax"][d, p], old["tavg"][d, p] = w["min_temp"], w["max_temp"], w["avg_temp"]
            if key in precip:
                old["precip"][d, p] = precip[key]
        if day.day == 1 or day == last:
            print(f"{day}: done", flush=True)

    report = write_report(args, days, points, v2, old)
    report += station_report(data_dir, window, days)
    report += point_report(data_dir, window, days)
    Path(args.out).write_text(report)
    print(f"wrote {args.out}")


def central_points(data_dir: Path, window) -> tuple[list[str], np.ndarray]:
    """The old API's 0.1° points whose cells are all Central time, and each cell's point index (-1: none)."""
    zones, zone_index = cell_timezones(open_or_create_daily(data_dir, 2025, window))
    central = np.isin(zone_index, [k for k, z in enumerate(zones) if z in ("America/Chicago", "America/Menominee")])
    lat, lon = NDFD.window_latlon(window)
    keys = np.array(
        [f"[{la:.1f}, {lo:.1f}]" for la, lo in zip(np.round(lat, 1).ravel(), np.round(lon, 1).ravel(), strict=True)]
    )
    keys = keys.reshape(window.shape)
    # Points at the window's edge have cells outside it, so they're left out
    edge = set(keys[0]) | set(keys[-1]) | set(keys[:, 0]) | set(keys[:, -1])
    not_central = set(keys[~central])
    points = sorted(set(keys.ravel()) - edge - not_central)
    index = {k: n for n, k in enumerate(points)}
    labels = np.vectorize(lambda k: index.get(k, -1))(keys)
    return points, labels


def point_means(hours: np.ndarray, labels: np.ndarray, n: int) -> np.ndarray:
    """Each hour's mean over each point's cells (NaN cells left out), (hours, points)."""
    flat = labels.ravel()
    keep = flat >= 0
    out = np.full((hours.shape[0], n), np.nan)
    for h, field in enumerate(hours):
        values = field.ravel()[keep]
        ok = np.isfinite(values)
        sums = np.bincount(flat[keep][ok], weights=values[ok], minlength=n)
        counts = np.bincount(flat[keep][ok], minlength=n)
        with np.errstate(invalid="ignore"):
            out[h] = sums / counts
    return out


class HourlyStores:
    """A variable's hours over the whole period, read once (reading hour by hour decompresses every chunk again)."""

    def __init__(self, data_dir: Path, window, start: datetime, stop: datetime):
        self.data_dir, self.window, self.start, self.stop = data_dir, window, start, stop
        self.loaded: dict[str, np.ndarray] = {}

    def read(self, name: str, hours: list[datetime], window) -> np.ndarray:
        if name not in self.loaded:
            n = (self.stop - self.start) // timedelta(hours=1)
            out = np.full((n, *self.window.shape), np.nan, dtype=np.float32)
            for year in range(self.start.year, self.stop.year + 1):
                store = GridStore.open(self.data_dir, HOURLY, year, VARIABLES.values())
                begin = max(self.start, datetime(year, 1, 1, tzinfo=UTC))
                end = min(self.stop, datetime(year + 1, 1, 1, tzinfo=UTC))
                if begin >= end:
                    continue
                t0 = store.index_of(begin)
                out[(begin - self.start) // timedelta(hours=1) : (end - self.start) // timedelta(hours=1)] = (
                    store.read_steps(name, t0, t0 + (end - begin) // timedelta(hours=1))
                )
            self.loaded[name] = out
        return self.loaded[name][[(t - self.start) // timedelta(hours=1) for t in hours]]


def bounds(window) -> Bounds:
    lat, lon = NDFD.window_latlon(window)
    return (float(lat.min()), float(lat.max()), float(lon.min()), float(lon.max()))


def stats(a: np.ndarray, b: np.ndarray) -> str:
    ok = np.isfinite(a) & np.isfinite(b)
    diff = a[ok] - b[ok]
    r = np.corrcoef(a[ok], b[ok])[0, 1] if ok.sum() > 2 else np.nan
    return f"{diff.mean():+.2f} | {np.abs(diff).mean():.2f} | {np.sqrt((diff**2).mean()):.2f} | {r:.3f} | {ok.sum():,}"


def write_report(args, days, points, v2, old) -> str:
    months = sorted({(d.year, d.month) for d in days})
    lines = [
        "# Validation: v2's archive against the old API",
        "",
        f"Generated by `scripts/compare_legacy.py --start {args.start} --end {args.end}` "
        f"on {datetime.now(UTC):%Y-%m-%d} "
        f"(PLAN.md Phase 2 H). {len(points):,} of the old API's 0.1° points in the `{args.box}` box (those with all "
        "their cells in Central time), each day. v2 is reduced the way the old API reduces RTMA: each hour's mean "
        "over the 2.5 km cells rounding to the point, and a day of the Central-time hours at 00:00–23:00 (precip: "
        "the hours ending then, an hour earlier than v2's own days). So the differences are the source (v2: URMA; "
        "old: RTMA) and QC. Differences are v2 − old.",
        "",
        "## Daily values",
        "",
        "| Variable | Bias | MAE | RMSE | r | Point-days |",
        "|---|---|---|---|---|---|",
    ]
    for key, label in [
        ("tmin", "Min temperature, °F"),
        ("tmax", "Max temperature, °F"),
        ("tavg", "Mean temperature, °F"),
        ("precip", "Precipitation, mm"),
    ]:
        lines.append(f"| {label} | {stats(v2[key], old[key])} |")
    lines += [
        "",
        "## By month",
        "",
        "| Month | Min °F bias | Max °F bias | Precip v2 / old | Wet days agree |",
        "|---|---|---|---|---|",
    ]
    for y, m in months:
        rows = [n for n, d in enumerate(days) if (d.year, d.month) == (y, m)]
        tmin = np.nanmean(v2["tmin"][rows] - old["tmin"][rows])
        tmax = np.nanmean(v2["tmax"][rows] - old["tmax"][rows])
        ratio = np.nansum(v2["precip"][rows]) / np.nansum(old["precip"][rows])
        wet_v2, wet_old = v2["precip"][rows] >= 0.25, old["precip"][rows] >= 0.25
        agree = (wet_v2 == wet_old).mean()
        lines.append(f"| {y}-{m:02d} | {tmin:+.2f} | {tmax:+.2f} | {ratio:.2f} | {agree:.0%} |")
    lines += [
        "",
        "## Degree days over the period (single sine, °F·d, from each source's daily min and max)",
        "",
        "| Pair | v2 mean | Old mean | Bias | MAE |",
        "|---|---|---|---|---|",
    ]
    for base, upper in PAIRS:
        a = np.nansum(degree_days_sine(v2["tmin"], v2["tmax"], base, upper), axis=0)
        b = np.nansum(degree_days_sine(old["tmin"], old["tmax"], base, upper), axis=0)
        lines.append(
            f"| {base:g}/{upper:g} | {a.mean():.1f} | {b.mean():.1f} | {(a - b).mean():+.1f} "
            f"| {np.abs(a - b).mean():.1f} |"
        )
    bias = np.nanmean(v2["tmin"] - old["tmin"], axis=0)
    worst = np.argsort(-np.abs(bias))[:10]
    lines += [
        "",
        "## Points with the largest mean min-temperature difference",
        "",
        "| Point (lat, lon) | Min °F bias | Max °F bias | Precip v2 / old |",
        "|---|---|---|---|",
    ]
    for p in worst:
        tmax = np.nanmean(v2["tmax"][:, p] - old["tmax"][:, p])
        ratio = np.nansum(v2["precip"][:, p]) / max(np.nansum(old["precip"][:, p]), 1e-9)
        lines.append(f"| {points[p]} | {bias[p]:+.2f} | {tmax:+.2f} | {ratio:.2f} |")
    return "\n".join(lines) + "\n"


def acis_daily_precip(window, first: date, last: date) -> list[dict]:
    """Daily precip (mm; trace = 0, missing = NaN) at every ACIS station in the window's box, cached."""
    south, north, west, east = bounds(window)
    return Acis(cache_dir=CACHE).precipitation_mm((west, south, east, north), first, last)


def read_daily(data_dir: Path, name: str, days: list[date]) -> np.ndarray:
    """A daily variable over consecutive days (day, y, x), across the years' stores."""
    from agdata.catalog import DAILY_VARIABLES
    from agdata.store import DAILY

    parts = []
    for year in sorted({d.year for d in days}):
        in_year = [d for d in days if d.year == year]
        store = GridStore.open(data_dir, DAILY, year, DAILY_VARIABLES.values())
        t0 = store.index_of(in_year[0])
        parts.append(store.read_steps(name, t0, t0 + len(in_year)))
    return np.concatenate(parts)


def station_report(data_dir: Path, window, days: list[date]) -> str:
    """Monthly precip at ACIS stations: v2 (the station's cell, its local days) and the old API (the 0.1° point)."""
    v2_days = read_daily(data_dir, "precipitation_sum", days)
    old_days = [OLD_API.precipitation_mm(day, bounds(window)) for day in days]
    rows = []
    for station in acis_daily_precip(window, days[0], days[-1]):
        if not station["ll"]:
            continue
        lon, lat = station["ll"]
        cell = NDFD.cell_of(lat, lon)
        if cell is None or not window.contains(*cell):
            continue
        y, x = window.local(*cell)
        key = f"[{round(lat, 1):.1f}, {round(lon, 1):.1f}]"
        rows.append((station, v2_days[:, y, x], np.array([d.get(key, np.nan) for d in old_days])))
    lines = [
        "",
        "## Monthly precipitation at ACIS stations",
        "",
        "Station months with every day reported (traces as 0), against v2 at the station's cell (its local days) and "
        "the old API at the station's 0.1° point. Cooperative observers mostly read their gauges in the morning, "
        "so single days don't line up, but months do (apart from the month's last morning). Gauges catch 10–30% "
        "less snow than falls, more in wind, so winter months read low at the station.",
        "",
        "| Month | Stations | Station mean, mm | v2 mean | v2 bias | v2 MAE | Old mean | Old bias | Old MAE |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for y, m in sorted({(d.year, d.month) for d in days}):
        idx = [n for n, d in enumerate(days) if (d.year, d.month) == (y, m)]
        obs, new, prev = [], [], []
        for station, v2_series, old_series in rows:
            values = station["mm"][idx]
            if np.isnan(values).any() or np.isnan(v2_series[idx]).any() or np.isnan(old_series[idx]).any():
                continue
            obs.append(values.sum())
            new.append(v2_series[idx].sum())
            prev.append(old_series[idx].sum())
        o, n_, p_ = np.array(obs), np.array(new), np.array(prev)
        if not len(o):
            continue  # no station reported every day (a month still in progress)
        lines.append(
            f"| {y}-{m:02d} | {len(o)} | {o.mean():.1f} | {n_.mean():.1f} | {(n_.mean() / o.mean() - 1):+.0%} "
            f"| {np.abs(n_ - o).mean():.1f} | {p_.mean():.1f} | {(p_.mean() / o.mean() - 1):+.0%} "
            f"| {np.abs(p_ - o).mean():.1f} |"
        )
    return "\n".join(lines) + "\n"


# WISP 3's comparison points (Wisconsin irrigated areas, app/services/weather/comparison.rb)
WISP_POINTS = [
    ("Hancock", 44.12, -89.53), ("Plainfield", 44.21, -89.49), ("Coloma", 44.03, -89.52),
    ("Almond", 44.26, -89.41), ("Bancroft", 44.31, -89.51), ("Plover", 44.45, -89.54),
    ("Wautoma", 44.07, -89.29), ("Grand Marsh", 43.89, -89.71), ("Arena", 43.17, -89.91),
    ("Spring Green", 43.18, -90.07), ("Antigo", 45.14, -89.15), ("Janesville", 42.68, -89.02),
]  # fmt: skip


def open_meteo_daily(lat: float, lon: float, first: date, last: date) -> dict:
    """Open-Meteo's historical-forecast daily ET0 (mm) and shortwave (MJ/m²) on Central days, cached a year at a
    time (a request for two years can time out)."""
    client = OpenMeteoDaily(cache_dir=CACHE)
    daily: dict[str, list] = {}
    for year in range(first.year, last.year + 1):
        a, b = max(first, date(year, 1, 1)), min(last, date(year, 12, 31))
        block = client.daily([(lat, lon)], a, b, ["et0_fao_evapotranspiration", "shortwave_radiation_sum"])[0]
        for key, values in block.items():
            daily.setdefault(key, []).extend(values)
    return daily


def point_report(data_dir: Path, window, days: list[date]) -> str:
    """Daily ET0 and shortwave at WISP 3's points: v2 against Open-Meteo and the old API (ET; SSEC insolation)."""
    v2_et0 = read_daily(data_dir, "et0_sum", days)
    v2_sw = read_daily(data_dir, "shortwave_radiation_sum", days)
    old_et = [OLD_API.evapotranspiration_mm(day, bounds(window)) for day in days]
    old_sw = [OLD_API.insolation_mj_m2(day, bounds(window)) for day in days]
    pairs: dict[str, tuple[list, list]] = {k: ([], []) for k in ("et0_om", "et0_old", "sw_om", "sw_old")}
    for _name, lat, lon in WISP_POINTS:
        cell = NDFD.cell_of(lat, lon)
        assert cell is not None
        y, x = window.local(*cell)
        key = f"[{round(lat, 1):.1f}, {round(lon, 1):.1f}]"
        om = open_meteo_daily(lat, lon, days[0], days[-1])
        for n in range(len(days)):
            for name, v2, other in [
                ("et0_om", v2_et0[n, y, x], om["et0_fao_evapotranspiration"][n]),
                ("et0_old", v2_et0[n, y, x], old_et[n].get(key)),
                ("sw_om", v2_sw[n, y, x], om["shortwave_radiation_sum"][n]),
                ("sw_old", v2_sw[n, y, x], old_sw[n].get(key)),
            ]:
                pairs[name][0].append(v2)
                pairs[name][1].append(np.nan if other is None else other)
    lines = [
        "",
        "## ET0 and shortwave at WISP 3's points",
        "",
        f"{len(WISP_POINTS)} Wisconsin irrigated-area points (WISP 3's comparison set), daily: v2 at the point's cell "
        "against Open-Meteo's historical-forecast API (FAO-56 ET0, the method v2 follows) and the old API at the "
        "0.1° point (its own ET; SSEC satellite insolation). Bias and MAE in mm or MJ/m²; ratio is of the totals.",
        "",
        "| Variable | Against | Bias | MAE | RMSE | r | Days | v2 / other |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label, other in [
        ("et0_om", "ET0, mm", "Open-Meteo"),
        ("et0_old", "ET0, mm", "old API"),
        ("sw_om", "Shortwave, MJ/m²", "Open-Meteo"),
        ("sw_old", "Shortwave, MJ/m²", "old API (SSEC)"),
    ]:
        a, b = (np.array(v, dtype=float) for v in pairs[key])
        ok = np.isfinite(a) & np.isfinite(b)
        lines.append(f"| {label} | {other} | {stats(a, b)} | {a[ok].sum() / b[ok].sum():.2f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
