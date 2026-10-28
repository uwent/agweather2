"""Reading selected fields from remote GRIB2 files with HTTP range requests, and placing them on the NDFD grid.

A file's messages are found from its wgrib2 `.idx` when there is one. Older URMA files (2016-2017) have
none, so `scan_index` reads just the first bytes of each message (sections 0-4) to learn its length and
what it holds; either way only the wanted messages are downloaded. Messages are identified like the `.idx`
does, by (name, level), e.g. ("TMP", "2 m above ground").
"""

import struct
import warnings
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
import requests

# The system ecCodes (libeccodes0) does the decoding. Not the eccodeslib wheel: it bundles its own PROJ, and
# a process that loads it before pyproj crashes on exit. The bindings prefer ecCodes 2.42+, but Ubuntu 24.04's
# 2.34 decodes these files fine.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="ecCodes .* or higher is recommended")
    import eccodes

from agdata.grid import NDFD, LambertGrid, Window

Key = tuple[str, str]  # (name, level), as in a wgrib2 .idx line


@dataclass(frozen=True)
class MessageRef:
    key: Key
    offset: int
    length: int | None  # None: to the end of the file
    detail: str = ""  # the .idx's time field, e.g. "anl" or "15-30 min ave fcst" ("" when scanned)


@dataclass
class Field:
    key: Key
    values: np.ndarray  # (ny, nx), NaN where the message has no value
    units: str
    first_lat: float
    first_lon: float


# GRIB2 parameters by (discipline, category, number) → wgrib2 name; only those our sources use
PARAMETERS: dict[tuple[int, int, int], str] = {
    (0, 0, 0): "TMP",
    (0, 0, 6): "DPT",
    (0, 1, 0): "SPFH",
    (0, 1, 8): "APCP",
    (0, 2, 0): "WDIR",
    (0, 2, 1): "WIND",
    (0, 2, 2): "UGRD",
    (0, 2, 3): "VGRD",
    (0, 2, 22): "GUST",
    (0, 3, 0): "PRES",
    (0, 3, 5): "HGT",
    (0, 6, 1): "TCDC",
    (0, 6, 13): "CEIL",
    (0, 19, 0): "VIS",
    (10, 0, 3): "HTSGW",
}

# Fixed surface types (GRIB2 code table 4.5) → wgrib2 level text; 103 takes its height
SURFACES: dict[int, str] = {
    1: "surface",
    10: "entire atmosphere (considered as a single layer)",
    200: "entire atmosphere (considered as a single layer)",
    215: "cloud ceiling",
}


def parse_idx(text: str) -> list[MessageRef]:
    """A wgrib2 inventory (`1:0:d=2025071518:TMP:2 m above ground:anl:`) → message refs."""
    rows = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        rows.append((int(parts[1]), (parts[3], parts[4]), parts[5] if len(parts) > 5 else ""))
    return [
        MessageRef(
            key=key, offset=offset, length=(rows[n + 1][0] - offset) if n + 1 < len(rows) else None, detail=detail
        )
        for n, (offset, key, detail) in enumerate(rows)
    ]


def describe_message_head(head: bytes) -> tuple[int, Key]:
    """The total length and (name, level) of a GRIB2 message, from its first bytes (through section 4)."""
    if head[:4] != b"GRIB" or head[7] != 2:
        raise ValueError("not a GRIB2 message")
    discipline = head[6]
    total = struct.unpack(">Q", head[8:16])[0]
    pos = 16
    while pos + 5 <= len(head):
        length, number = struct.unpack(">IB", head[pos : pos + 5])
        if number == 4:
            section = head[pos : pos + length]
            if len(section) < 28:
                break
            category, parameter = section[9], section[10]
            surface, scale = section[22], struct.unpack(">b", section[23:24])[0]
            value = struct.unpack(">I", section[24:28])[0]
            name = PARAMETERS.get((discipline, category, parameter), f"var{discipline}_{category}_{parameter}")
            if surface == 103:
                level = f"{value / 10**scale:g} m above ground"
            else:
                level = SURFACES.get(surface, f"surface type {surface}")
            return total, (name, level)
        pos += length
    raise ValueError("section 4 not found in the bytes read; read more of the message")


def scan_index(read_range: Callable[[int, int], bytes], size: int, head_bytes: int = 2048) -> list[MessageRef]:
    """Builds an index by reading the head of each message in turn (two small reads per message)."""
    refs, offset = [], 0
    while offset < size:
        head = read_range(offset, min(offset + head_bytes, size) - 1)
        total, key = describe_message_head(head)
        refs.append(MessageRef(key=key, offset=offset, length=total))
        offset += total
    return refs


def decode(message: bytes) -> Field:
    handle = eccodes.codes_new_from_message(message)
    try:
        nx, ny = eccodes.codes_get_long(handle, "Nx"), eccodes.codes_get_long(handle, "Ny")
        lambert = eccodes.codes_get_string(handle, "gridType") == "lambert"
        if not lambert or not eccodes.codes_get_long(handle, "jScansPositively"):
            raise ValueError("expected a Lambert grid scanning south to north")
        values = np.asarray(eccodes.codes_get_double_array(handle, "values"), dtype=np.float64)
        if eccodes.codes_get_long(handle, "bitmapPresent"):
            values[values == eccodes.codes_get_double(handle, "missingValue")] = np.nan
        return Field(
            key=(eccodes.codes_get_string(handle, "shortName"), ""),
            values=values.reshape(ny, nx),
            units=eccodes.codes_get_string(handle, "units"),
            first_lat=eccodes.codes_get_double(handle, "latitudeOfFirstGridPointInDegrees"),
            first_lon=eccodes.codes_get_double(handle, "longitudeOfFirstGridPointInDegrees"),
        )
    finally:
        eccodes.codes_release(handle)


def place(field: Field, window: Window, grid: LambertGrid = NDFD) -> np.ndarray:
    """A field on its own (aligned) grid → the window's cells, NaN where the field doesn't reach."""
    j_off, i_off = grid.offset_of(field.first_lat, field.first_lon)
    ny, nx = field.values.shape
    out = np.full(window.shape, np.nan)
    j0, j1 = max(window.j0, j_off), min(window.j1, j_off + ny)
    i0, i1 = max(window.i0, i_off), min(window.i1, i_off + nx)
    if j0 < j1 and i0 < i1:
        out[j0 - window.j0 : j1 - window.j0, i0 - window.i0 : i1 - window.i0] = field.values[
            j0 - j_off : j1 - j_off, i0 - i_off : i1 - i_off
        ]
    return out


class RemoteGrib:
    """A GRIB2 file over HTTP: its index (from .idx or by scanning) and its messages by key."""

    def __init__(self, url: str, session: requests.Session | None = None, timeout: float = 60):
        self.url = url
        self.session = session or requests.Session()
        self.timeout = timeout
        self._index: list[MessageRef] | None = None

    def exists(self) -> bool:
        return self.session.head(self.url, timeout=self.timeout).status_code == 200

    def index(self) -> list[MessageRef]:
        if self._index is None:
            response = self.session.get(self.url + ".idx", timeout=self.timeout)
            if response.status_code == 200:
                self._index = parse_idx(response.text)
            else:
                head = self.session.head(self.url, timeout=self.timeout)
                if head.status_code != 200:
                    raise FileNotFoundError(f"{self.url}: HTTP {head.status_code}")
                self._index = scan_index(self._read_range, int(head.headers["Content-Length"]))
        return self._index

    def fields(self, keys: Iterable[Key]) -> dict[Key, Field]:
        """Downloads and decodes the messages with these keys; keys the file lacks are left out."""
        wanted = set(keys)
        found = {}
        for ref in self.index():
            if ref.key in wanted and ref.key not in found:
                end = ref.offset + ref.length - 1 if ref.length else None
                field = decode(self._read_range(ref.offset, end))
                field.key = ref.key
                found[ref.key] = field
        return found

    def fields_where(self, predicate: Callable[[MessageRef], bool]) -> list[tuple[MessageRef, Field]]:
        """Downloads and decodes every message the predicate accepts, in file order."""
        found = []
        for ref in self.index():
            if predicate(ref):
                end = ref.offset + ref.length - 1 if ref.length else None
                field = decode(self._read_range(ref.offset, end))
                field.key = ref.key
                found.append((ref, field))
        return found

    def _read_range(self, start: int, end: int | None) -> bytes:
        headers = {"Range": f"bytes={start}-{'' if end is None else end}"}
        response = self.session.get(self.url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.content
