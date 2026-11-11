"""A small archive and NBM runs over a 2 x 3 window near Madison in Central time, for tests here and in the app
(agdata's conftest and the API's fixture archive). Not used outside tests."""

from datetime import UTC, date, datetime, timedelta
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


def archive(
    data_dir, start: datetime, end: datetime, warm: float = 15.0, hole: tuple[datetime, datetime] | None = None
) -> None:
    """Archive hours start..end (inclusive) at `warm` °C ± 6 (missing through `hole`, inclusive), rolled up with
    running totals from the next day."""
    times = [start + k * HOUR for k in range((end - start) // HOUR + 1)]
    values = weather(times, warm=warm)
    values["surface_pressure"] = np.full((len(times), *WINDOW.shape), 98.0)
    values["relative_humidity"] = np.full((len(times), *WINDOW.shape), 75.0)
    values["et0"] = np.full((len(times), *WINDOW.shape), 0.1)
    if hole is not None:
        gone = [n for n, t in enumerate(times) if hole[0] <= t <= hole[1]]
        for v in values.values():
            v[gone] = np.nan
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


def central(monkeypatch: "pytest.MonkeyPatch | None" = None) -> SimpleNamespace:
    """WINDOW and the helpers (every cell's days are grid days, CST: D74; `monkeypatch` is no longer needed)."""
    return SimpleNamespace(window=WINDOW, archive=archive, nbm_run=nbm_run, read=read, weather=weather)


# Potato volunteer's winters (`winters`): hours below 27 °F a day at every depth, by the year the winter starts
WINTER_RATES = {2023: 1.0, 2024: 2.0, 2025: 3.0}
WINTER_LAST = date(2025, 12, 15)  # the archive's last day: 2025-26 is open
SOIL = ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm")


def winters(root, last: date = WINTER_LAST):
    """An archive of potato volunteer's winters over WINDOW from 2023 through `last`: hourly soil at −5 °C for
    `WINTER_RATES` hours a day (from 10Z, 4 am in Central time, so each local day has them all) and +2 °C the rest,
    ERA5-Land's (permanent) through April 1 of the last year and IFS's (provisional) after; daily stores with just
    the counts, the ingredients built from them, and temperature sources saying the archive is observed through
    12Z the day after `last`. Returns `root`."""
    from datetime import UTC

    from agdata import modelmaps
    from agmodels.registry import model

    def rate(day: date) -> int:
        return int(WINTER_RATES.get(day.year if day.month >= 7 else day.year - 1, 0))

    end = datetime(last.year, last.month, last.day, tzinfo=UTC) + timedelta(hours=37)  # through 12Z the next day
    spring = datetime(last.year, 4, 2, tzinfo=UTC)
    for year in range(2023, last.year + 1):
        first = date(year, 1, 1)
        days = [first + timedelta(days=k) for k in range((min(last, date(year, 12, 31)) - first).days + 1)]
        store = daily.open_or_create_daily(root, year, WINDOW)
        counts = np.array([float(rate(d)) for d in days])[:, None, None] * np.ones((1, *WINDOW.shape))
        values = {f"hours_soil_{d}_below_27f": counts for d in ("4cm", "10cm", "8in")}
        values |= {f"{name}_min": np.where(counts > 0, -5.0, 2.0) for name in SOIL}
        store.write(first, values, source="test")

        start = datetime(year, 1, 1, tzinfo=UTC)
        times = [start + k * HOUR for k in range(int((min(end, datetime(year + 1, 1, 1, tzinfo=UTC)) - start) / HOUR))]
        cold = np.array([10 <= t.hour < 10 + rate(t.date()) for t in times])
        soil = np.where(cold, -5.0, 2.0)[:, None, None] * np.ones((1, *WINDOW.shape))
        hourly = GridStore.create(root, HOURLY, year, WINDOW, [VARIABLES[n] for n in ("air_temperature", *SOIL)])
        for name in SOIL:
            hourly.write(start, {name: soil}, source="era5land")
            if year == last.year:
                k = int((spring - start) / HOUR)
                hourly.set_sources(name, spring, ["ifs"] * (len(times) - k))
        if year == last.year:
            hourly.set_sources("air_temperature", start, ["test"] * len(times))
    spec = model("potato-volunteer").SPEC
    keys = [modelmaps.key(spec.id, i) for i in spec.ingredients]
    modelmaps.update(root, WINDOW, date(2023, 1, 1), last, keys=keys)
    return root


CELLS_START = datetime(2024, 12, 28, tzinfo=UTC)
CELLS_CYCLE = datetime(2025, 1, 3, 12, tzinfo=UTC)
CELLS_NOW = CELLS_CYCLE + 2 * HOUR


def _noisy(values: dict[str, np.ndarray], rng: np.random.Generator) -> None:
    shape = values["air_temperature"].shape
    values["air_temperature"] += rng.normal(0, 2.0, shape)
    values["dew_point"] = values["air_temperature"] - 1 - np.abs(rng.normal(0, 3.0, shape))
    values["precipitation"] = np.where(rng.random(shape) < 0.2, rng.exponential(1.0, shape), 0.0)


def differing_cells(path):
    """An archive whose cells differ (noise per cell, hours missing in cell (901, 1402) and a block that empties a
    day), across a year's end (CELLS_START to CELLS_CYCLE + 2 h), then an NBM run at CELLS_CYCLE without
    soil."""
    rng = np.random.default_rng(7)
    end = CELLS_CYCLE + 2 * HOUR
    times = [CELLS_START + k * HOUR for k in range((end - CELLS_START) // HOUR + 1)]
    values = weather(times, warm=2.0)
    _noisy(values, rng)
    shape = values["air_temperature"].shape
    values |= {
        "surface_pressure": np.full(shape, 98.0),
        "relative_humidity": np.full(shape, 75.0),
        "et0": np.full(shape, 0.05),
    }
    gaps = rng.random(shape[0]) < 0.1  # hours missing in one cell only, and a block that empties a day
    gaps[60:76] = True
    for v in values.values():
        v[gaps, 1, 2] = np.nan
    for year in (2024, 2025):
        store = GridStore.create(path, HOURLY, year, WINDOW, VARIABLES.values())
        k = [n for n, t in enumerate(times) if t.year == year]
        store.write(times[k[0]], {name: v[k[0] : k[-1] + 1] for name, v in values.items()}, source="urma")
    update_days(path, WINDOW, (CELLS_START + timedelta(days=1)).date(), (end - timedelta(days=1)).date())
    run = nbm_run(CELLS_CYCLE, warm=6.0)
    _noisy(run.values, rng)
    from agdata import forecast

    forecast.publish(path, forecast.write_run(path, WINDOW, run, pressure_kpa=98.0))
    return path
