"""Mint flea beetle (part H, H5): the model's first adults (USPest's 1,475 single-sine degree days above 41 °F in air
from January 1) against Commercial Vegetable Production in Wisconsin's 1,100 degree days above 40 °F in soil 6 inches
deep, at Arlington, Hancock and Rhinelander on the archive, 2016–2025; and what USPest's 103 °F upper threshold would
change.

Soil at 6 in (15 cm) is interpolated between the hourly 10 and 30 cm soil temperatures (ERA5-Land's layers); a day's
soil degree days are the average of its hourly minimum and maximum above 40 °F (`soil_avg`), or its mean degree hours
(`soil_hours`). Needs the archive in data/.

    uv run python scripts/check_mint_flea_beetle.py
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.grid import NDFD
from agdata.progress import Reporter
from agdata.store import DAILY, HOURLY, GridStore
from agmodels.degree_days import degree_days_sine

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
YEARS = range(2016, 2026)


def fahrenheit(c: np.ndarray) -> np.ndarray:
    return c * 9 / 5 + 32


def first(total: np.ndarray, reach: float) -> int | None:
    k = np.flatnonzero(total >= reach)
    return int(k[0]) if len(k) else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mint flea beetle: air degree days against A3422's soil degree days.")
    parser.add_argument("--data", default="data")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = Reporter(quiet=args.quiet)
    data = Path(args.data)
    temps = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
    soil = [VARIABLES["soil_temperature_10cm"], VARIABLES["soil_temperature_30cm"]]
    print("| Place | Year | Air 1,475 DD41 | Soil 1,100 DD40 at 6 in (avg) | (degree hours) | Soil − air, days | 103 °F cap, DD |")  # fmt: skip
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for name, (lat, lon) in PLACES.items():
        report.step(f"{name}, {YEARS[0]}–{YEARS[-1]}")
        cell = NDFD.cell_of(lat, lon)
        assert cell is not None
        for n, year in enumerate(YEARS):
            report.progress(name, n, len(YEARS))
            daily = GridStore.open(data, DAILY, year, temps)
            lo, hi = (fahrenheit(daily.read_point(v, *cell)) for v in ("air_temperature_min", "air_temperature_max"))
            air = np.nancumsum(degree_days_sine(lo, hi, base=41, upper=None))
            capped = np.nancumsum(degree_days_sine(lo, hi, base=41, upper=103))
            hourly = GridStore.open(data, HOURLY, year, soil)
            s10, s30 = (fahrenheit(hourly.read_point(v, *cell)) for v in ("soil_temperature_10cm", "soil_temperature_30cm"))  # fmt: skip
            s15 = s10 + 0.25 * (s30 - s10)
            days = s15[: len(s15) // 24 * 24].reshape(-1, 24)
            if np.isnan(days).all(axis=1).any():
                report.warn(f"{name} {year}: {int(np.isnan(days).all(axis=1).sum())} days without soil temperatures")
            soil_avg = np.nancumsum(np.maximum((np.nanmin(days, 1) + np.nanmax(days, 1)) / 2 - 40, 0))
            soil_hours = np.nancumsum(np.nanmean(np.maximum(days - 40, 0), 1))
            ka, ks, kh = first(air, 1475), first(soil_avg, 1100), first(soil_hours, 1100)
            on = lambda k: (date(year, 1, 1) + timedelta(days=k)).strftime("%B %-d") if k is not None else "–"  # noqa: B023, E731
            gap = f"{ks - ka:+d}" if ks is not None and ka is not None else "–"
            line = f"| {name} | {year} | {on(ka)} | {on(ks)} | {on(kh)} | {gap} | {air[-1] - capped[-1]:.1f} |"
            print(line, flush=True)
            report.detail(line)
    if not report.finish("the soil and air dates"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
