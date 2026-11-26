"""A small archive and NBM runs over a 2 x 3 window near Madison in Central time, for tests here and in the app
(agdata's conftest and the API's fixture archive). Not used outside tests."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from agdata import daily
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, FILL, VARIABLES
from agdata.cumulative import update_days
from agdata.grid import Window
from agdata.sources.nbm import HORIZON_HOURS, HourlyRun
from agdata.store import DAILY, HOURLY, GridStore

if TYPE_CHECKING:
    from pathlib import Path

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


def keep_only(data_dir, layout, year: int, names: list[str]) -> None:
    """Drops every variable but `names` from a test store (its arrays and their `_meta`), so code that reads all a
    store holds (a past-years copy reads every daily variable's year, a chunk a day each) reads only these."""
    import shutil

    path = layout.path(data_dir, year)
    for child in path.iterdir():
        if child.is_dir() and child.name != "_meta" and child.name not in names:
            shutil.rmtree(child)
    for child in (path / "_meta").iterdir():
        name, _, kind = child.name.rpartition(".")
        if child.is_dir() and kind in ("source", "written") and name not in names:
            shutil.rmtree(child)


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


def built_once(tmp_path_factory: "pytest.TempPathFactory", name: str, build) -> "Path":
    """A test archive built once for the whole run and shared by pytest-xdist's workers (each worker would otherwise
    build its own session fixture): the first worker to ask builds it under a lock in the run's shared temp folder,
    the rest wait and get the same folder. `build(folder)` fills the empty folder. Treat the result as read only;
    a fixture whose tests write copies it (`shutil.copytree`)."""
    import fcntl
    import os
    import shutil
    from pathlib import Path

    base = Path(tmp_path_factory.getbasetemp())
    shared = base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base
    target, done = shared / f"built-{name}", shared / f"built-{name}.done"
    with open(shared / f"built-{name}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not done.exists():
            if target.exists():  # a worker stopped half way
                shutil.rmtree(target)
            target.mkdir()
            build(target)
            done.touch()
    return target


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


def terrain_store(data_dir, window: Window, water_share: np.ndarray, elevation_m: float | np.ndarray = 260.0) -> None:
    """A terrain store (`agdata.terrain`) over `window` with the given water share (percent, (y, x)) and a DEM at
    `elevation_m` everywhere (or per cell, (y, x)), as `terrain.build` leaves it."""
    import zarr

    from agdata import terrain

    sub = terrain.SUB
    per_cell = np.broadcast_to(np.asarray(elevation_m, dtype=np.float32), window.shape)
    group = zarr.open_group(terrain.path(data_dir), mode="w")
    fine = np.repeat(np.repeat(per_cell, sub, axis=0), sub, axis=1)
    dem = group.create_array("dem", data=np.round(fine / terrain.DEM_SCALE).astype(np.int16), chunks=(sub, sub))
    dem.attrs.update({"scale": terrain.DEM_SCALE, "units": "m", "sub": sub})
    group.create_array("water_share", data=np.asarray(water_share, dtype=np.uint8))
    stats = terrain.cell_stats(fine)
    for name, values in stats.items():
        group.create_array(name, data=values)
    group.attrs.update(
        {"version": terrain.VERSION, "window": terrain._window_attrs(window), "archives": [], "complete": True}
    )


def freeze_normal(data_dir, window: Window, spring_slot: float | np.ndarray, period: str = "last30") -> None:
    """A period's normal maps (`agdata.normals`) over `window` holding only the median last spring freeze at 28 °F,
    as a calendar slot (`climatology.slot`; NaN missing), everywhere or per cell (y, x): what potato's planting dates
    read (`agdata.potatoplanting`). Other statistics read as not stored."""
    import zarr

    from agdata import normals, potatoplanting

    slots = np.broadcast_to(np.asarray(spring_slot, dtype=float), window.shape)
    group = zarr.open_group(normals.path(data_dir, period), mode="w")
    packed = np.where(np.isfinite(slots), np.round(np.nan_to_num(slots)), FILL).astype(np.int16)[None]
    array = group.create_array(potatoplanting.FREEZE, data=packed, fill_value=int(FILL))
    array.attrs.update({"scale": 1.0, "single": True})
    group.attrs.update(
        {
            "period": period,
            "window": {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1},
            "built": datetime.now(UTC).isoformat(timespec="microseconds"),
            "version": normals.VERSION,
            "complete": True,
        }
    )


def climate_year(data_dir, window: Window, year: int, values: dict[str, np.ndarray], fit: str = "1@test") -> None:
    """A derived gridMET year (`agdata.climatestore`) over `window`: `values` per daily variable, (days, y, x) or
    (days,) for every cell, as `climatestore.derive` leaves them (without the files it records)."""
    import zarr
    from zarr.codecs.numcodecs import PCodec

    from agdata import climatestore

    names = list(values)
    n = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    group = zarr.open_group(climatestore.path(data_dir, year), mode="w")
    array = group.create_array(
        "values",
        shape=(len(names), n, *window.shape),
        chunks=(len(names), n, min(16, window.shape[0]), min(16, window.shape[1])),
        dtype="int16",
        fill_value=int(FILL),
        serializer=PCodec(level=1),
    )

    def whole(v) -> np.ndarray:
        v = np.asarray(v, dtype=float)
        return np.broadcast_to(v[:, None, None] if v.ndim == 1 else v, (n, *window.shape))

    array[:] = np.stack([DAILY_VARIABLES[name].encode(np.array(whole(values[name]))) for name in names])
    group.attrs.update(
        {
            "year": year,
            "window": {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1},
            "names": names,
            "version": climatestore.VERSION,
            "fit": fit,
            "adjusted": [],
            "files": {},
            "complete": True,
        }
    )


# Verification (`agdata.verification`): hand-made runs and archive days


def full(value: float) -> np.ndarray:
    """A field of `value` over WINDOW."""
    return np.full(WINDOW.shape, value)


def write_days(root, values: dict[str, dict[date, np.ndarray]]) -> None:
    """Writes each variable's days (name → day → field over WINDOW) into `root`'s daily or ingredients stores, made
    for just those variables (a model ingredient's name, such as 'late-blight-dsv.dsv', goes to the ingredients)."""
    from agdata.store import INGREDIENTS
    from agdata.verification import kept_variable

    by_store: dict[tuple, dict[str, dict[date, np.ndarray]]] = {}
    for name, days in values.items():
        layout = DAILY if name in DAILY_VARIABLES else INGREDIENTS
        for day, field in days.items():
            by_store.setdefault((layout, day.year), {}).setdefault(name, {})[day] = field
    for (layout, year), names in by_store.items():
        variables = [kept_variable(name) for name in names]
        try:
            store = GridStore.open(root, layout, year, variables, add_missing=True)
        except FileNotFoundError:
            store = GridStore.create(root, layout, year, WINDOW, variables)
        for name, days in names.items():
            for day, field in days.items():
                store.write(day, {name: field}, source="derived")


def fake_run(data_dir, cycle: datetime, values: dict[str, dict[date, np.ndarray]], last_observed=None) -> "Path":
    """A forecast run's directory with run.json and daily (and ingredients) stores holding only `values`, as
    `write_days` takes them."""
    import json

    from agdata import forecast

    path = forecast.run_path(data_dir, cycle)
    path.mkdir(parents=True)
    info = {
        "cycle": cycle.isoformat(),
        "last_observed": last_observed and last_observed.isoformat(),
        "failed_leads": [],
    }
    (path / "run.json").write_text(json.dumps(info))
    write_days(path, values)
    return path


def cdl_raster(path, window: Window, classes: np.ndarray, shift_m: float = 0.0, margin: int = 20) -> "Path":
    """A Cropland Data Layer year as NASS's (Albers, 30 m, uint8 classes, LZW, tiled) over `window` and `margin`
    pixels around it, each pixel's class its centre's cell's in `classes` ((y, x) over the window; 0 outside it),
    the cell found exactly (pyproj at every pixel). `shift_m` moves the raster east off the 30 m lattice."""
    from pathlib import Path

    import rasterio
    from rasterio.transform import from_origin

    from agdata import cropland

    r0, r1, c0, c1 = cropland.pixel_window(window, west=0.0, north=0.0)  # a lattice whose corner is (0, 0)
    west, north = (c0 - margin) * cropland.PIXEL + shift_m, -(r0 - margin) * cropland.PIXEL
    height, width = r1 - r0 + 2 * margin, c1 - c0 + 2 * margin
    xs = west + (np.arange(width) + 0.5) * cropland.PIXEL
    ys = north - (np.arange(height) + 0.5) * cropland.PIXEL
    fj, fi = cropland._albers_to_grid()(*np.meshgrid(xs, ys))
    j, i = np.floor(fj + 0.5).astype(int), np.floor(fi + 0.5).astype(int)
    inside = (j >= window.j0) & (j < window.j1) & (i >= window.i0) & (i < window.i1)
    values = np.zeros((height, width), dtype=np.uint8)
    values[inside] = np.asarray(classes, dtype=np.uint8)[j[inside] - window.j0, i[inside] - window.i0]
    path = Path(path)
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1, dtype="uint8", crs=cropland.ALBERS,
        transform=from_origin(west, north, cropland.PIXEL, cropland.PIXEL), compress="lzw", tiled=True,
        blockxsize=64, blockysize=64,
    ) as out:  # fmt: skip
        out.write(values, 1)
    return path


def cdl_zip(data_dir, year: int, raster) -> "Path":
    """A year's zip in `data/cdl/` laid out as NASS's: the raster beside a pyramid, a world file and metadata."""
    import zipfile

    from agdata import cropland

    dest = cropland.zip_path(data_dir, year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(raster, arcname=f"{year}_30m_cdls.tif")
        z.writestr(f"{year}_30m_cdls.tif.ovr", b"pyramid")
        z.writestr(f"{year}_30m_cdls.tfw", "30\n0\n0\n-30\n0\n0\n")
        z.writestr(f"metadata_CDL{year % 100}.htm", "<html></html>")
    return dest
