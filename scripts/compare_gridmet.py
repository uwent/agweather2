"""gridMET against the archive, 2.5 km cell by cell (PLAN.md Phase 6 D2; D82).

uv run --with scipy python scripts/compare_gridmet.py --start 2016 --end 2025 [--out docs/validation-climate.md]

gridMET (Abatzoglou 2013, doi:10.1002/joc.3413) is the 30-year normals' source (D82); our archive is URMA/RTMA with
HRRR and ERA5-Land, rolled up to midnight-to-midnight CST days. Before the 30 years are stored (D3), this measures
how the two differ over the years they share, so a "departure from normal" doesn't show the sources' difference as
weather. Reads data/gridmet/<var>/<year>.nc (scripts/download_gridmet.py; netCDF-3, hence SciPy) and the daily
stores in DATA_DIR, regrids gridMET to our cells bilinearly (enough to compare; D3 uses D80's B-spline), and reports:

- by month, the mean difference (archive − gridMET) over every cell and day both have, and the spread of the cells'
  own mean differences (10th–90th percentile); for precipitation, the ratio of totals and of rain days (≥ 0.01 in);
- the day-to-day agreement and its timing: the correlation of each source's day-to-day changes at a lag of −1, 0 and
  +1 day (a day's shift in gridMET's days against ours would peak away from 0);
- at DATCP's 23 points and Madison's two cells, the mean differences and each source's median last spring and first
  fall frost (32 °F) over the years, as the normals (D1) would give them.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "agdata" / "src"))

from scipy.io import netcdf_file  # noqa: E402

from agdata import climatology as clim  # noqa: E402
from agdata.catalog import DAILY_VARIABLES  # noqa: E402
from agdata.grid import NDFD, Window  # noqa: E402
from agdata.progress import Reporter  # noqa: E402
from agdata.store import DAILY, GridStore  # noqa: E402

DATCP_POINTS = [
    (42.5, -89.0), (42.5, -90.7), (42.6, -87.9), (43.0, -88.2), (43.0, -88.6), (43.1, -88.0), (43.1, -89.5),
    (43.2, -90.2), (43.3, -88.4), (43.4, -88.7), (43.8, -91.2), (44.1, -89.5), (44.1, -89.8), (44.3, -88.4),
    (44.4, -89.9), (44.5, -88.1), (44.8, -91.5), (45.0, -89.6), (45.1, -90.4), (45.2, -88.0), (45.5, -92.0),
    (45.6, -89.4), (46.6, -90.9),
]  # fmt: skip
EXTRA_POINTS = {"Madison isthmus": (43.07, -89.40), "Madison farms": (43.17, -89.50)}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RAIN_MM = 0.254
SAMPLE = 7  # every 7th row and column for the day-to-day correlations


def kelvin(v):
    return v - 273.15


def per_m2_day(v):
    return v * 0.0864  # W/m² as a day's mean → MJ/m²


# (label, archive variable, gridMET variable, gridMET → archive's unit, unit shown, how compared)
PAIRS = [
    ("Maximum temperature", "air_temperature_max", "tmmx", kelvin, "°F", "diff"),
    ("Minimum temperature", "air_temperature_min", "tmmn", kelvin, "°F", "diff"),
    ("Precipitation", "precipitation_sum", "pr", None, "in", "rain"),
    ("Reference ET (grass)", "et0_sum", "pet", None, "in", "ratio"),
    ("Shortwave radiation", "shortwave_radiation_sum", "srad", per_m2_day, "MJ/m²", "ratio"),
    ("Wind speed (10 m)", "wind_speed_mean", "vs", None, "mph", "ratio"),
    ("Maximum relative humidity", "relative_humidity_max", "rmax", None, "%", "diff"),
    ("Minimum relative humidity", "relative_humidity_min", "rmin", None, "%", "diff"),
]
SHOWN = {"°F": 1.8, "in": 1 / 25.4, "mph": 2.23694, "MJ/m²": 1.0, "%": 1.0}  # a difference's factor from stored


def read_gridmet(path: Path, var: str):
    """(dates, values (days, lat, lon) in gridMET's unit with NaN for fill, lats, lons)."""
    with netcdf_file(path, mmap=False) as f:
        data = next(v for v in f.variables.values() if v.data.ndim == 3)
        attrs = data._attributes
        raw = data.data.astype(np.float64)
        fill = attrs.get("_FillValue", 32767)
        values = np.where(data.data == fill, np.nan, raw * attrs.get("scale_factor", 1.0) + attrs.get("add_offset", 0))
        days = [date(1900, 1, 1) + timedelta(days=int(d)) for d in f.variables["day"].data]
        lats = np.array(f.variables["lat"].data, dtype=np.float64)
        lons = np.array(f.variables["lon"].data, dtype=np.float64)
    return days, values, lats, lons


class Regrid:
    """Bilinear weights from a regular latitude-longitude grid to a window's cell centers."""

    def __init__(self, lats: np.ndarray, lons: np.ndarray, window: Window):
        clat, clon = NDFD.window_latlon(window)
        fy = (lats[0] - clat) / (lats[0] - lats[1])  # gridMET's latitudes run north to south
        fx = (clon - lons[0]) / (lons[1] - lons[0])
        self.y0 = np.clip(np.floor(fy).astype(int), 0, len(lats) - 2)
        self.x0 = np.clip(np.floor(fx).astype(int), 0, len(lons) - 2)
        self.wy, self.wx = fy - self.y0, fx - self.x0

    def __call__(self, values: np.ndarray) -> np.ndarray:
        y0, x0, wy, wx = self.y0, self.x0, self.wy, self.wx
        a, b = values[:, y0, x0], values[:, y0, x0 + 1]
        c, d = values[:, y0 + 1, x0], values[:, y0 + 1, x0 + 1]
        return (1 - wy) * ((1 - wx) * a + wx * b) + wy * ((1 - wx) * c + wx * d)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--data", default=str(REPO / "data"))
    parser.add_argument("--out", default=str(REPO / "docs" / "validation-climate.md"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    data = Path(args.data)
    years = list(range(args.start, args.end + 1))
    report.step(f"gridMET against the archive, {years[0]}–{years[-1]}")

    sums = {p[1]: np.zeros(12) for p in PAIRS}  # by month: Σ(archive − gridMET) or Σ archive / Σ gridMET
    other = {p[1]: np.zeros(12) for p in PAIRS}
    counts = {p[1]: np.zeros(12) for p in PAIRS}
    cell_sum: dict[str, np.ndarray] = {}
    cell_n: dict[str, np.ndarray] = {}
    rain_days = {"archive": np.zeros(12), "gridmet": np.zeros(12)}
    lag_series: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        "air_temperature_max": [],
        "air_temperature_min": [],
        "precipitation_sum": [],
    }
    points = {f"DATCP {k + 1} ({lat}, {lng})": (lat, lng) for k, (lat, lng) in enumerate(DATCP_POINTS)}
    points |= {f"{name} ({lat}, {lng})": (lat, lng) for name, (lat, lng) in EXTRA_POINTS.items()}
    at_points: dict[str, dict[str, list]] = {name: {"years": []} for name in points}
    regrid = None
    window = None

    for y, year in enumerate(years):
        store = GridStore.open(data, DAILY, year, [DAILY_VARIABLES[p[1]] for p in PAIRS])
        window = store.window
        cells = {name: NDFD.cell_of(lat, lng) for name, (lat, lng) in points.items()}
        local = {name: window.local(*c) for name, c in cells.items() if c is not None and window.contains(*c)}
        for label, ours, theirs, convert, _, how in PAIRS:
            path = data / "gridmet" / theirs / f"{year}.nc"
            if not path.exists():
                report.fail(f"{theirs} {year}", f"{path} is missing; run scripts/download_gridmet.py")
                continue
            days, raw, lats, lons = read_gridmet(path, theirs)
            if regrid is None:
                regrid = Regrid(lats, lons, window)
            gm = regrid(raw)
            if convert is not None:
                gm = convert(gm)
            arch = store.read_steps(ours, 0, len(days)).astype(np.float64)
            both = np.isfinite(gm) & np.isfinite(arch)
            months = np.array([d.month - 1 for d in days])
            if ours not in cell_sum:
                cell_sum[ours] = np.zeros((12, *window.shape))
                cell_n[ours] = np.zeros((12, *window.shape))
            for m in range(12):
                sel = months == m
                b = both[sel]
                if how == "diff":
                    diff = np.where(b, arch[sel] - gm[sel], 0.0)
                    sums[ours][m] += diff.sum()
                    cell_sum[ours][m] += diff.sum(axis=0)
                else:
                    sums[ours][m] += np.where(b, arch[sel], 0.0).sum()
                    other[ours][m] += np.where(b, gm[sel], 0.0).sum()
                    cell_sum[ours][m] += np.where(b, arch[sel], 0.0).sum(axis=0) - np.where(b, gm[sel], 0.0).sum(axis=0)
                counts[ours][m] += b.sum()
                cell_n[ours][m] += b.sum(axis=0)
                if how == "rain":
                    rain_days["archive"][m] += (b & (arch[sel] >= RAIN_MM)).sum()
                    rain_days["gridmet"][m] += (b & (gm[sel] >= RAIN_MM)).sum()
            if ours in lag_series:
                lag_series[ours].append(
                    (
                        arch[:, ::SAMPLE, ::SAMPLE].reshape(len(days), -1),
                        gm[:, ::SAMPLE, ::SAMPLE].reshape(len(days), -1),
                    )
                )
            for name, (j, i) in local.items():
                at_points[name].setdefault(ours, []).append(
                    (clim.layout(arch[:, j, i], year), clim.layout(gm[:, j, i], year))
                )
            report.detail(f"{year} {label}: {int(both.sum()):,} cell-days compared")
        for name in local:
            at_points[name]["years"].append(year)
        report.progress("years", y + 1, len(years))

    lines = _report(years, sums, other, counts, cell_sum, cell_n, rain_days, lag_series, at_points)
    Path(args.out).write_text("\n".join(lines) + "\n")
    report.detail(f"wrote {args.out}")
    return 0 if report.finish(f"compared {len(years)} years") else 1


def _lags(pairs: list[tuple[np.ndarray, np.ndarray]], changes: bool) -> dict[int, float]:
    arch = np.concatenate([a for a, _ in pairs])
    gm = np.concatenate([g for _, g in pairs])
    if changes:
        arch, gm = np.diff(arch, axis=0), np.diff(gm, axis=0)
    found = {}
    for lag in (-1, 0, 1):  # gridMET's day d + lag against our day d
        a = arch[max(0, -lag) : len(arch) - max(0, lag)]
        g = gm[max(0, lag) : len(gm) - max(0, -lag)]
        rs = []
        for c in range(a.shape[1]):
            ok = np.isfinite(a[:, c]) & np.isfinite(g[:, c])
            if ok.sum() > 100:
                rs.append(np.corrcoef(a[ok, c], g[ok, c])[0, 1])
        found[lag] = float(np.median(rs)) if rs else float("nan")
    return found


def _report(years, sums, other, counts, cell_sum, cell_n, rain_days, lag_series, at_points) -> list[str]:
    out = [
        "# gridMET against the archive",
        "",
        f"Generated by `scripts/compare_gridmet.py --start {years[0]} --end {years[-1]}` (PLAN.md Phase 6 D2). "
        "Every 2.5 km cell of the Wisconsin box and every day both sources have, gridMET regridded bilinearly to "
        "our cells. Differences are archive − gridMET; ratios archive ÷ gridMET.",
        "",
        "## By month, over every cell",
        "",
    ]
    for label, ours, _, _, unit, how in PAIRS:
        out += [f"### {label}", ""]
        f = SHOWN[unit]
        with np.errstate(invalid="ignore", divide="ignore"):
            if how == "diff":
                out += [
                    f"| Month | Mean difference ({unit}) | Cells' mean, P10 to P90 ({unit}) | Cell-days |",
                    "|---|---|---|---|",
                ]
                per_cell = cell_sum[ours] / cell_n[ours]
                for m in range(12):
                    lo, hi = (
                        np.nanpercentile(per_cell[m], [10, 90]) if np.isfinite(per_cell[m]).any() else (np.nan, np.nan)
                    )
                    out.append(
                        f"| {MONTHS[m]} | {sums[ours][m] / counts[ours][m] * f:+.2f} | "
                        f"{lo * f:+.2f} to {hi * f:+.2f} | {int(counts[ours][m]):,} |"
                    )
                total = sums[ours].sum() / counts[ours].sum() * f
                out += [f"| Year | {total:+.2f} | | {int(counts[ours].sum()):,} |", ""]
            else:
                head = "| Month | Ratio of totals | Archive daily mean | gridMET daily mean |"
                if how == "rain":
                    head += " Rain days, archive ÷ gridMET |"
                out += [head, "|---|---|---|---|" + ("---|" if how == "rain" else "")]
                for m in range(12):
                    ours_mean = sums[ours][m] / counts[ours][m] * f
                    theirs_mean = other[ours][m] / counts[ours][m] * f
                    ratio = sums[ours][m] / other[ours][m]
                    row = f"| {MONTHS[m]} | {ratio:.3f} | {ours_mean:.3f} {unit} | {theirs_mean:.3f} {unit} |"
                    if how == "rain":
                        row += f" {rain_days['archive'][m] / rain_days['gridmet'][m]:.3f} |"
                    out.append(row)
                row = f"| Year | {sums[ours].sum() / other[ours].sum():.3f} | | |"
                if how == "rain":
                    row += f" {rain_days['archive'].sum() / rain_days['gridmet'].sum():.3f} |"
                out += [row, ""]
    out += [
        "## Timing",
        "",
        "The median over a sample of cells (every 7th row and column) of the correlation between our day and gridMET's "
        "day shifted by the lag: day-to-day changes for temperature, daily amounts for precipitation. A peak away "
        "from 0 means one source's days are shifted against the other's.",
        "",
        "| Variable | gridMET a day earlier (−1) | Same day (0) | gridMET a day later (+1) |",
        "|---|---|---|---|",
    ]
    for ours, pairs in lag_series.items():
        if pairs:
            r = _lags(pairs, changes=ours != "precipitation_sum")
            out.append(f"| {ours} | {r[-1]:.3f} | {r[0]:.3f} | {r[1]:.3f} |")
    out += [
        "",
        "## At points",
        "",
        "Mean differences over the years, and each source's median last spring and first fall frost (32 °F) as the "
        "normals compute them (`agdata.climatology.freezes`).",
        "",
        "| Point | Max temp (°F) | Min temp (°F) | Precip ratio | Last spring frost, archive / gridMET "
        "| First fall frost, archive / gridMET |",
        "|---|---|---|---|---|---|",
    ]
    for name, found in at_points.items():
        if not found["years"]:
            continue
        cols = []
        for ours in ("air_temperature_max", "air_temperature_min"):
            a = np.stack([x for x, _ in found[ours]])
            g = np.stack([y for _, y in found[ours]])
            cols.append(f"{np.nanmean(a - g) * 1.8:+.2f}")
        a = np.stack([x for x, _ in found["precipitation_sum"]])
        g = np.stack([y for _, y in found["precipitation_sum"]])
        ok = np.isfinite(a) & np.isfinite(g)
        cols.append(f"{a[ok].sum() / g[ok].sum():.3f}")
        frost = []
        for k in (0, 1):
            tmin = np.stack([pair[k] for pair in found["air_temperature_min"]])
            fz = clim.freezes(tmin, 0.0)
            spring, fall = fz.dates(0.5)
            frost.append((_day(spring), _day(fall)))
        cols.append(f"{frost[0][0]} / {frost[1][0]}")
        cols.append(f"{frost[0][1]} / {frost[1][1]}")
        out.append(f"| {name} | " + " | ".join(cols) + " |")
    return out


def _day(s) -> str:
    if not np.isfinite(s):
        return "—"
    d = clim.slot_date(round(float(s)), 2025)
    return f"{d:%b %d}" if d else "Feb 29"


if __name__ == "__main__":
    sys.exit(main())
