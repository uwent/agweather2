"""The app tests' archive: agdata's 2 x 3 test window (`agdata.testing`) with hours from 2025-07-01 through an
observed 15Z on July 10, rolled up to days and running totals, and an NBM run from 13Z that day. `app/conftest.py`
builds it once per session (`archive_dir`); `archive` points DATA_DIR and SERVICE_BOX at it and sets the API's clock
to NOW for a test."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agdata import forecast, testing
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
    return path


PAST_YEARS = (2023, 2024)
HOLE_2023 = (datetime(2023, 7, 28, tzinfo=UTC), datetime(2023, 8, 7, 23, tzinfo=UTC))  # 11 days: not bridged


def build_with_past_years(path: Path) -> Path:
    """The archive as `build` makes it, with July and August of two earlier years for the projection (D63): 2023 at
    12 °C ± 6 with an 11-day hole, 2024 at 18 °C ± 6."""
    build(path)
    with pytest.MonkeyPatch.context() as monkeypatch:
        fx = testing.central(monkeypatch)
        fx.archive(
            path, datetime(2023, 7, 1, tzinfo=UTC), datetime(2023, 8, 31, 23, tzinfo=UTC), warm=12, hole=HOLE_2023
        )
        fx.archive(path, datetime(2024, 7, 1, tzinfo=UTC), datetime(2024, 8, 31, 23, tzinfo=UTC), warm=18)
    return path
