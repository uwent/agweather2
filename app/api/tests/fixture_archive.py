"""The app tests' archive: agdata's 2 x 3 test window (`agdata.testing`) with hours from 2025-07-01 through an
observed 15Z on July 10, rolled up to days and running totals, and an NBM run from 13Z that day. `app/conftest.py`
builds it once per session (`archive_dir`); `archive` points DATA_DIR and SERVICE_BOX at it and sets the API's clock
to NOW for a test."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from agdata import croptiers, forecast, testing
from agdata.grid import NDFD

CYCLE = datetime(2025, 7, 10, 13, tzinfo=UTC)
OBSERVED_UNTIL = CYCLE + timedelta(hours=2)  # 15Z: 10 am CDT
NOW = CYCLE + timedelta(hours=3)
FIRST_HOUR = datetime(2025, 7, 1, tzinfo=UTC)
CELL = (900, 1401)
POINT = tuple(round(float(v), 4) for v in NDFD.latlon(*CELL))  # the cell's center
BOX = "42.84,-91.69,42.866,-91.627"  # around the window's cells


def build(path: Path) -> Path:
    with pytest.MonkeyPatch.context() as monkeypatch:
        fx = testing.central(monkeypatch)
        fx.archive(path, FIRST_HOUR, OBSERVED_UNTIL)
        run = forecast.write_run(path, fx.window, fx.nbm_run(CYCLE), pressure_kpa=98.0)
        forecast.publish(path, run)
        croptiers.refresh(path, fx.window, NOW.date())  # the crops' stages per planting tier, as the hourly job
    return path


PAST_YEARS = (2023, 2024)
HOLE_2023 = (datetime(2023, 7, 28, tzinfo=UTC), datetime(2023, 8, 7, 23, tzinfo=UTC))  # 11 days: not bridged


def add_past_years(path: Path) -> Path:
    """To an archive `build` made, July and August of two earlier years for the projection (D63): 2023 at 12 °C ± 6
    with an 11-day hole, 2024 at 18 °C ± 6."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        fx = testing.central(monkeypatch)
        fx.archive(
            path, datetime(2023, 7, 1, tzinfo=UTC), datetime(2023, 8, 31, 23, tzinfo=UTC), warm=12, hole=HOLE_2023
        )
        fx.archive(path, datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 8, 31, 23, tzinfo=UTC), warm=18)
    return path


CLIMATE_YEARS = (2020, 2021, 2022, 2023, 2024)  # `last5` at NOW (2025)


def climate_values(year: int) -> dict[str, np.ndarray]:
    """A climate year with known answers: a maximum of 20 °C + 1 °C a year from 2020 (so the normal is 22 °C, and
    modified 50/86 degree days 9 + 0.9 a year: 10.8 °F·d a day on average), a minimum of 10 °C (50 °F) but −5 °C on
    January 1–10 and from December 20 (freezes), 1 mm of rain and 2 mm of ET0 a day."""
    n = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    tmin = np.full(n, 10.0)
    tmin[:10] = -5.0
    tmin[n - 12 :] = -5.0
    return {
        "air_temperature_max": np.full(n, 20.0 + (year - 2020)),
        "air_temperature_min": tmin,
        "precipitation_sum": np.full(n, 1.0),
        "et0_sum": np.full(n, 2.0),
    }


def add_climate_years(path: Path) -> Path:
    """To an archive `build` made, gridMET's derived years for `last5` over the window (`CLIMATE_YEARS`), and their
    normal maps (`agdata.normals`) as `last5` and, from the same years, `last10` (which keeps deciles)."""
    from agdata import normals

    for year in CLIMATE_YEARS:
        testing.climate_year(path, testing.WINDOW, year, climate_values(year))
    for period in ("last5", "last10"):
        normals.build(path, period, list(CLIMATE_YEARS), set(), testing.WINDOW, days_per_chunk=366)
    return path
