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
        chunk_t, chunk_y, chunk_x = chunks or DEFAULT_CHUNKS[layout.step]
        chunk_shape = (min(chunk_t, n), min(chunk_y, window.shape[0]), min(chunk_x, window.shape[1]))
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
        meta = group.create_group("_meta")
        for v in variables:
            group.create_array(
                v.name,
                shape=(n, *window.shape),
                chunks=chunk_shape,
                dtype="int16",
                fill_value=int(FILL),
                serializer=PCodec(level=pcodec_level),
                compressors=(),
                dimension_names=("time", "y", "x"),
                attributes={"long_name": v.long_name, "unit": v.unit, "scale": v.scale, "offset": v.offset},
            )
            meta.create_array(f"{v.name}.source", shape=(n,), chunks=(n,), dtype="uint8", fill_value=0)
            meta.create_array(f"{v.name}.written", shape=(n,), chunks=(n,), dtype="float64", fill_value=np.nan)
        store = cls(group, path)
        store.variables = {v.name: v for v in variables}
        return store

    @classmethod
    def open(cls, data_dir: Path, layout: StoreLayout, year: int, variables: Iterable[Variable]) -> "GridStore":
        path = layout.path(data_dir, year)
        if not path.exists():
            raise FileNotFoundError(path)
        store = cls(zarr.open_group(path, mode="r+"), path)
        wanted = {v.name: v for v in variables}
        missing = set(wanted) - set(store.group.array_keys())
        if missing:
            raise KeyError(f"{path} has no {', '.join(sorted(missing))}")
        store.variables = wanted
        return store

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

    def write(self, start: datetime | date, values: dict[str, np.ndarray], source: str | None) -> None:
        """Writes consecutive steps from `start`: each array is (steps, y, x) over the window, in the stored unit.

        `source` marks every written step; pass None and call `set_sources` when steps came from different sources.
        """
        t0 = self.index_of(start)
        now = datetime.now(UTC).timestamp()
        for name, block in values.items():
            v = self._variable(name)
            block = np.asarray(block)
            if block.ndim == 2:
                block = block[np.newaxis]
            if block.shape[1:] != self.window.shape:
                raise ValueError(f"{name}: shape {block.shape[1:]} doesn't match the window {self.window.shape}")
            t1 = t0 + block.shape[0]
            if t1 > self.length:
                raise IndexError(f"{name}: steps run past the end of {self.year}")
            self._array(name)[t0:t1] = v.encode(block)
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
        window = window or self.window
        y0, x0 = self.window.local(window.j0, window.i0)
        y1, x1 = y0 + window.shape[0], x0 + window.shape[1]
        if y1 > self.window.shape[0] or x1 > self.window.shape[1]:
            raise IndexError(f"{window} reaches outside the store's {self.window}")
        packed = self._array(name)[index, y0:y1, x0:x1]
        return self._variable(name).decode(np.asarray(packed))

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
