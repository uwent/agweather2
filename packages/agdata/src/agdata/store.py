"""Zarr stores for gridded data: one store per kind (hourly, daily, …) per year (PLAN.md §5.3).

A store covers one `Window` of the NDFD grid for one calendar year (UTC) at one time step. Each variable is
an int16 array (time, y, x) packed by the catalog's scale and offset, plus per-step metadata: which source
filled the step and when it was written, so an RTMA hour can later be replaced by URMA. Deleting a year's
directory drops it from the rolling window.

Writes take a block of consecutive steps. A write touches every chunk its time range overlaps, so writing
whole chunks of time at once (a month in a backfill) is far cheaper than hour by hour; the Phase 1 pilot
measures what hourly ingest costs (docs/pilot.md).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
import zarr
from zarr.codecs.numcodecs import PCodec

from agdata.catalog import FILL, Variable
from agdata.grid import NDFD, Window

Step = Literal["hour", "day"]

# Source codes stored per step; 0 means nothing written yet
SOURCES = {"urma": 1, "rtma": 2, "hrrr": 3, "nbm": 4, "openmeteo": 5, "derived": 6, "test": 99}
SOURCE_NAMES = {code: name for name, code in SOURCES.items()}

# Chunks (time steps, y, x): hourly for point reads (a cell's month is one chunk), daily for map tiles.
# pcodec compresses the packed int16 values 25-45% better than zstd at the same speed (docs/pilot.md).
DEFAULT_CHUNKS: dict[Step, tuple[int, int, int]] = {"hour": (720, 32, 32), "day": (1, 256, 256)}


@dataclass(frozen=True)
class StoreLayout:
    kind: str  # directory name: hourly, daily, cumulative, …
    step: Step

    def path(self, data_dir: Path, year: int) -> Path:
        return Path(data_dir) / self.kind / f"{year}.zarr"


HOURLY = StoreLayout("hourly", "hour")
DAILY = StoreLayout("daily", "day")
CUMULATIVE = StoreLayout("cumulative", "day")


def steps_in_year(year: int, step: Step) -> int:
    days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    return days * 24 if step == "hour" else days


class GridStore:
    """One year of one kind of gridded data over a window."""

    def __init__(self, group: zarr.Group, path: Path):
        self.group = group
        self.path = path
        attrs: dict[str, Any] = dict(group.attrs)
        self.year = int(attrs["year"])
        self.step: Step = attrs["step"]
        w = attrs["window"]
        self.window = Window(w["j0"], w["j1"], w["i0"], w["i1"])
        self.variables: dict[str, Variable] = {}
        self.stale: set[str] = set()  # derived variables to recompute (D29)

    # Creating and opening

    @classmethod
    def create(
        cls,
        data_dir: Path,
        layout: StoreLayout,
        year: int,
        window: Window,
        variables: Iterable[Variable],
        chunks: tuple[int, int, int] | None = None,
        pcodec_level: int = 8,
    ) -> "GridStore":
        path = layout.path(data_dir, year)
        if path.exists():
            raise FileExistsError(f"{path} exists; open it, or delete it to rebuild")
        n = steps_in_year(year, layout.step)
        chunk_shape = _clamp(chunks or DEFAULT_CHUNKS[layout.step], n, window)
        group = zarr.open_group(path, mode="w")
        group.attrs.update(
            {
                "grid": NDFD.name,
                "year": year,
                "step": layout.step,
                "start": datetime(year, 1, 1, tzinfo=UTC).isoformat(),
                "window": {"j0": window.j0, "j1": window.j1, "i0": window.i0, "i1": window.i1},
            }
        )
        group.attrs["chunks"] = list(chunk_shape)
        group.attrs["pcodec_level"] = pcodec_level
        group.create_group("_meta")
        store = cls(group, path)
        for v in variables:
            store._add_array(v, v.version)
        store.variables = {v.name: v for v in variables}
        return store

    def _add_array(self, v: Variable, version: int) -> None:
        attrs: dict[str, Any] = dict(self.group.attrs)
        n = self.length
        self.group.create_array(
            v.name,
            shape=(n, *self.window.shape),
            chunks=tuple(attrs.get("chunks") or _clamp(DEFAULT_CHUNKS[self.step], n, self.window)),
            dtype="int16",
            fill_value=int(FILL),
            serializer=PCodec(level=int(attrs.get("pcodec_level", 8))),
            compressors=(),
            dimension_names=("time", "y", "x"),
            attributes={
                "long_name": v.long_name,
                "unit": v.unit,
                "scale": v.scale,
                "offset": v.offset,
                "version": version,
            },
        )
        meta = self.group["_meta"]
        assert isinstance(meta, zarr.Group)
        meta.create_array(f"{v.name}.source", shape=(n,), chunks=(n,), dtype="uint8", fill_value=0)
        meta.create_array(f"{v.name}.written", shape=(n,), chunks=(n,), dtype="float64", fill_value=np.nan)

    @classmethod
    def open(
        cls, data_dir: Path, layout: StoreLayout, year: int, variables: Iterable[Variable], add_missing: bool = False
    ) -> "GridStore":
        """Opens a year's store for `variables`. A variable it lacks is an error unless `add_missing`, which adds
        it empty and stale; a derived variable written by another version of its code is stale (D29)."""
        path = layout.path(data_dir, year)
        if not path.exists():
            raise FileNotFoundError(path)
        store = cls(zarr.open_group(path, mode="r+"), path)
        wanted = {v.name: v for v in variables}
        missing = set(wanted) - set(store.group.array_keys())
        if missing and not add_missing:
            raise KeyError(f"{path} has no {', '.join(sorted(missing))}")
        for name in sorted(missing):
            store._add_array(wanted[name], version=0)  # nothing computed yet for the days already stored
        for name, v in wanted.items():
            stored: Any = store._array(name).attrs.get("version", 1)
            if v.derived and int(stored) != v.version:
                store.stale.add(name)
            attrs = store._array(name).attrs
            if (attrs.get("scale"), attrs.get("offset")) != (v.scale, v.offset):
                raise ValueError(
                    f"{path}: {name} is stored at scale {attrs.get('scale')}, offset {attrs.get('offset')}, but the "
                    f"catalog says {v.scale}, {v.offset}; run GridStore.rescale on it"
                )
        store.variables = wanted
        return store

    @classmethod
    def stale_variables(cls, data_dir: Path, layout: StoreLayout, year: int, variables: Iterable[Variable]) -> set[str]:
        """Read-only: the derived variables the store lacks or holds from another version of their code."""
        group = zarr.open_group(layout.path(data_dir, year), mode="r")
        present = set(group.array_keys())
        stale = set()
        for v in variables:
            if not v.derived:
                continue
            if v.name not in present:
                stale.add(v.name)
                continue
            array = group[v.name]
            stored: Any = array.attrs.get("version", 1)
            if int(stored) != v.version:
                stale.add(v.name)
        return stale

    @classmethod
    def rescale(cls, data_dir: Path, layout: StoreLayout, year: int, variable: Variable, steps: int = 720) -> None:
        """Repacks a variable stored at another scale or offset to the catalog's, `steps` at a time. Values keep
        the old precision; refetch them for the new one."""
        group = zarr.open_group(layout.path(data_dir, year), mode="r+")
        array = group[variable.name]
        assert isinstance(array, zarr.Array)
        attrs: dict[str, Any] = dict(array.attrs)
        scale, offset = float(attrs["scale"]), float(attrs["offset"])
        for t in range(0, array.shape[0], steps):
            packed = np.asarray(array[t : t + steps])
            values = packed.astype(np.float64) * scale + offset
            values[packed == FILL] = np.nan
            array[t : t + steps] = variable.encode(values)
        array.attrs.update({"scale": variable.scale, "offset": variable.offset})

    # Time

    @property
    def start(self) -> datetime:
        return datetime(self.year, 1, 1, tzinfo=UTC)

    @property
    def length(self) -> int:
        return steps_in_year(self.year, self.step)

    def index_of(self, when: datetime | date) -> int:
        """The step index of a UTC time (hourly stores) or a date (daily stores)."""
        if self.step == "hour":
            if not isinstance(when, datetime) or when.tzinfo is None:
                raise ValueError("hourly stores take timezone-aware datetimes")
            delta = when.astimezone(UTC) - self.start
            index, remainder = divmod(delta, timedelta(hours=1))
            if remainder:
                raise ValueError(f"{when} isn't on the hour")
        else:
            day = when.date() if isinstance(when, datetime) else when
            index = (day - self.start.date()).days
        if not 0 <= index < self.length:
            raise IndexError(f"{when} is outside {self.year}")
        return index

    def time_of(self, index: int) -> datetime:
        return self.start + (timedelta(hours=index) if self.step == "hour" else timedelta(days=index))

    # Writing

    def write(
        self,
        start: datetime | date,
        values: dict[str, np.ndarray],
        source: str | None,
        window: Window | None = None,
    ) -> None:
        """Writes consecutive steps from `start`: each array is (steps, y, x) over the window (default the
        store's; a sub-window writes part of each step), in the stored unit.

        `source` marks every written step; pass None and call `set_sources` when steps came from different sources.
        """
        t0 = self.index_of(start)
        now = datetime.now(UTC).timestamp()
        rows, cols = self._local_slices(window)
        for name, block in values.items():
            v = self._variable(name)
            block = np.asarray(block)
            if block.ndim == 2:
                block = block[np.newaxis]
            shape = (window or self.window).shape
            if block.shape[1:] != shape:
                raise ValueError(f"{name}: shape {block.shape[1:]} doesn't match the window {shape}")
            t1 = t0 + block.shape[0]
            if t1 > self.length:
                raise IndexError(f"{name}: steps run past the end of {self.year}")
            self._array(name)[t0:t1, rows, cols] = v.encode(block)
            self._array(f"_meta/{name}.written")[t0:t1] = now
            if source is not None:
                self._array(f"_meta/{name}.source")[t0:t1] = SOURCES[source]

    def set_sources(self, name: str, start: datetime | date, sources: list[str | None]) -> None:
        """Records which source filled each step from `start` (None: nothing)."""
        t0 = self.index_of(start)
        codes = np.array([SOURCES[s] if s else 0 for s in sources], dtype=np.uint8)
        self._array(f"_meta/{name}.source")[t0 : t0 + len(codes)] = codes

    def has_data(self, name: str, start: int = 0, stop: int | None = None) -> np.ndarray:
        """Whether each step in start..stop-1 has been written from some source."""
        return np.asarray(self._array(f"_meta/{name}.source")[start:stop]) > 0

    # Reading

    def read_point(self, name: str, j: int, i: int, start: int = 0, stop: int | None = None) -> np.ndarray:
        """One cell's series (grid indices j, i) over steps start..stop-1, in the stored unit; NaN where missing."""
        y, x = self.window.local(j, i)
        packed = self._array(name)[start:stop, y, x]
        return self._variable(name).decode(np.asarray(packed))

    def read_block(self, name: str, index: int, window: Window | None = None) -> np.ndarray:
        """One step over a window (grid indices; default the whole store), in the stored unit."""
        return self.read_steps(name, index, index + 1, window)[0]

    def read_steps(self, name: str, start: int, stop: int, window: Window | None = None) -> np.ndarray:
        """Steps start..stop-1 over a window (default the whole store), (steps, y, x) in the stored unit."""
        rows, cols = self._local_slices(window)
        packed = self._array(name)[start:stop, rows, cols]
        return self._variable(name).decode(np.asarray(packed))

    def _local_slices(self, window: Window | None) -> tuple[slice, slice]:
        window = window or self.window
        y0, x0 = self.window.local(window.j0, window.i0)
        y1, x1 = y0 + window.shape[0], x0 + window.shape[1]
        if y1 > self.window.shape[0] or x1 > self.window.shape[1]:
            raise IndexError(f"{window} reaches outside the store's {self.window}")
        return slice(y0, y1), slice(x0, x1)

    def mark_current(self, names: Iterable[str]) -> None:
        """Records that these variables were recomputed throughout by their catalog version's code."""
        for name in names:
            self._array(name).attrs["version"] = self._variable(name).version
            self.stale.discard(name)

    def read_meta(self, name: str) -> np.ndarray:
        """A whole `_meta` array (per-step sources and write times, or a daily store's time zones)."""
        return np.asarray(self._array(f"_meta/{name}")[:])

    def sources(self, name: str) -> list[str | None]:
        codes = np.asarray(self._array(f"_meta/{name}.source")[:])
        return [SOURCE_NAMES.get(int(code)) for code in codes]

    def _array(self, path: str) -> zarr.Array:
        array = self.group[path]
        if not isinstance(array, zarr.Array):
            raise KeyError(f"{path} isn't an array in {self.path}")
        return array

    def _variable(self, name: str) -> Variable:
        try:
            return self.variables[name]
        except KeyError:
            raise KeyError(f"{name} isn't open in this store") from None


def _clamp(chunks: tuple[int, int, int], steps: int, window: Window) -> tuple[int, int, int]:
    return (min(chunks[0], steps), min(chunks[1], window.shape[0]), min(chunks[2], window.shape[1]))
