"""A small archive and NBM runs over a 2 x 3 window near Madison in Central time, for tests here and in the app
(agdata's conftest and the API's fixture archive). Not used outside tests."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from agdata import daily
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.cumulative import update_days
from agdata.grid import Window
from agdata.sources.nbm import HORIZON_HOURS, HourlyRun
from agdata.store import DAILY, HOURLY, GridStore

if TYPE_CHECKING:
    import pytest

WINDOW = Window(j0=900, j1=902, i0=1400, i1=1403)  # 2 x 3 cells near Madison
HOUR = timedelta(hours=1)


def weather(times: list[datetime], warm: float) -> dict[str, np.ndarray]:
    h = np.array([t.hour for t in times], dtype=float)[:, None, None]
    shape = (len(times), *WINDOW.shape)
    temperature = np.broadcast_to(warm + 6 * np.sin(2 * np.pi * (h - 15) / 24), shape)
    return {
        "air_temperature": temperature.copy(),
        "dew_point": temperature - 4,
        "wind_speed": np.full(shape, 3.0),
        "wind_gust": np.full(shape, 6.0),
        "wind_direction": np.full(shape, 200.0),
        "cloud_cover": np.full(shape, 40.0),
        "shortwave_radiation": np.broadcast_to(np.clip(600 * np.sin(np.pi * (h - 11) / 14), 0, None), shape).copy(),
        "precipitation": np.full(shape, 0.1),
    }


def archive(data_dir, start: datetime, end: datetime) -> None:
    """Archive hours start..end (inclusive) at 15 °C ± 6, rolled up with running totals from the next day."""
    times = [start + k * HOUR for k in range((end - start) // HOUR + 1)]
    values = weather(times, warm=15)
    values["surface_pressure"] = np.full((len(times), *WINDOW.shape), 98.0)
    values["relative_humidity"] = np.full((len(times), *WINDOW.shape), 75.0)
    values["et0"] = np.full((len(times), *WINDOW.shape), 0.1)
    for year in range(start.year, end.year + 1):
        store = GridStore.create(data_dir, HOURLY, year, WINDOW, VARIABLES.values())
        k = [n for n, t in enumerate(times) if t.year == year]
        store.write(times[k[0]], {name: v[k[0] : k[-1] + 1] for name, v in values.items()}, source="urma")
    update_days(data_dir, WINDOW, (start + timedelta(days=1)).date(), (end - timedelta(days=1)).date())


def nbm_run(cycle: datetime, warm: float = 25.0) -> HourlyRun:
    """A run at `warm` °C ± 6 every hour."""
    times = [cycle + (n + 1) * HOUR for n in range(HORIZON_HOURS)]
    values = weather(times, warm=warm)
    return HourlyRun(
        cycle=cycle, values=values, filled={name: np.zeros(v.shape, dtype=bool) for name, v in values.items()}
    )


def read(path, layout, name: str, day: date) -> np.ndarray:
    variables = DAILY_VARIABLES if layout is DAILY else CUMULATIVE_VARIABLES
    store = GridStore.open(path, layout, day.year, variables.values(), add_missing=True)
    return store.read_steps(name, store.index_of(day), store.index_of(day) + 1)[0]


def central(monkeypatch: "pytest.MonkeyPatch") -> SimpleNamespace:
    """Every cell of WINDOW in Central time (no timezone lookup), and the helpers."""
    index = np.zeros(WINDOW.shape, dtype=np.uint8)
    monkeypatch.setattr(daily, "window_timezones", lambda window: (["America/Chicago"], index))
    return SimpleNamespace(window=WINDOW, archive=archive, nbm_run=nbm_run, read=read, weather=weather)
