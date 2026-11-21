"""Crucifer flea beetle: Kinoshita et al. 1979's sums on the model's degree days (part H, H3).

On the archive's daily min and max at Arlington, Hancock and Rhinelander, 2016–2025:

- the ratio of the model's degree days (modified average, 50/86 °F) to Kinoshita et al.'s (single sine above 51.8 °F,
  no upper) from May 15 to August 15, which converts their 820.6 °F·d from egg to adult;
- from the day the model's total from January 1 reaches the spring adults' peak (200), the days and model degree days
  until 61 °C·d (110 °F·d) above 17 °C (62.6 °F, single sine) have accumulated: their threshold for egg laying.

    uv run python scripts/check_crucifer_flea_beetle.py
"""

from pathlib import Path

import numpy as np

from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY, GridStore
from agmodels.degree_days import degree_days_modified, degree_days_sine

PLACES = {"Arlington": (43.30, -89.35), "Hancock": (44.12, -89.53), "Rhinelander": (45.64, -89.41)}
DATA = Path(__file__).resolve().parents[1] / "data"
TEMPS = [DAILY_VARIABLES["air_temperature_min"], DAILY_VARIABLES["air_temperature_max"]]
MAY_15, AUG_15 = 134, 227  # day-of-year indices (0-based; leap years a day off, which doesn't matter here)

for place, (lat, lon) in PLACES.items():
    cell = NDFD.cell_of(lat, lon)
    assert cell is not None
    ratios, lags_days, lags_dd = [], [], []
    for year in range(2016, 2026):
        store = GridStore.open(DATA, DAILY, year, TEMPS)
        lo, hi = (store.read_point(n, *cell) * 1.8 + 32 for n in ("air_temperature_min", "air_temperature_max"))
        model = degree_days_modified(lo, hi, base=50, upper=86)
        kinoshita = degree_days_sine(lo, hi, base=51.8, upper=None)
        ratios.append(np.nansum(model[MAY_15:AUG_15]) / np.nansum(kinoshita[MAY_15:AUG_15]))
        total = np.nancumsum(model)
        a = int(np.argmax(total >= 200))
        laying = np.nancumsum(degree_days_sine(lo, hi, base=62.6, upper=None)[a:])
        b = a + int(np.argmax(laying >= 110))
        lags_days.append(b - a)
        lags_dd.append(total[b] - total[a])
    print(
        f"{place}: ratio {np.mean(ratios):.3f} (years {min(ratios):.3f}–{max(ratios):.3f}); 820.6 → {820.6 * np.mean(ratios):.0f}."
        f" Egg-laying threshold from the spring peak: median {np.median(lags_days):.0f} days, {np.median(lags_dd):.1f} degree days"
        f" ({min(lags_dd):.0f}–{max(lags_dd):.0f})"
    )
