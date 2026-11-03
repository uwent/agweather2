"""Shared helpers for the forecast and series tests: a small archive and NBM runs over a 2 x 3 Central window."""

from pathlib import Path

import numpy as np
import pytest
import requests

from agdata.grid import Window
from agdata.testing import central


@pytest.fixture
def fx(monkeypatch):
    """The window in Central time, and helpers: archive, nbm_run, read."""
    return central(monkeypatch)


@pytest.fixture(scope="module")
def fx_module():
    """As `fx`, for a module's shared data (build it once in a module-scoped fixture)."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        yield central(monkeypatch)


# --- GRIB files in a fake bucket ---------------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"
GRIB_ROWS, GRIB_COLS = 40, 50  # urma_tmp_small.grb2 covers NDFD rows 900-939 and columns 1400-1449
GRIB_WINDOW = Window(j0=900, j1=904, i0=1400, i1=1404)  # inside it


def grib_message(values: float | np.ndarray) -> bytes:
    """A GRIB2 message on the fixture's grid holding `values` (a number fills the grid), with no missing cells."""
    from agdata.sources.grib import eccodes

    grid = np.broadcast_to(np.asarray(values, dtype=float), (GRIB_ROWS, GRIB_COLS))
    handle = eccodes.codes_new_from_message((FIXTURES / "urma_tmp_small.grb2").read_bytes())
    try:
        eccodes.codes_set_values(handle, np.ascontiguousarray(grid).ravel())
        return eccodes.codes_get_message(handle)
    finally:
        eccodes.codes_release(handle)


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b"", headers: dict | None = None, url: str = ""):
        self.status_code, self.content, self.headers, self.url = status_code, content, headers or {}, url
        self.text = content.decode(errors="replace")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


class Bucket:
    """A requests-like session over GRIB files held in memory: HEAD, `.idx` and range requests. A URL that was
    never added is a 404 (a file that isn't published); `fail` makes a URL answer with that status instead."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.idx: dict[str, str] = {}
        self.fail: dict[str, int] = {}
        self.gets: list[str] = []

    def add(self, url: str, messages: list[tuple[tuple[str, str], str, float | np.ndarray]]) -> None:
        """A file of messages, each (key, the .idx's time field, values), with a wgrib2-style `.idx`."""
        body, lines = b"", []
        for n, (key, detail, values) in enumerate(messages, start=1):
            lines.append(f"{n}:{len(body)}:d=2025071518:{key[0]}:{key[1]}:{detail}:")
            body += grib_message(values)
        self.files[url], self.idx[url] = body, "\n".join(lines) + "\n"

    def get(self, url: str, headers=None, timeout=None) -> FakeResponse:
        self.gets.append(url)
        base = url.removesuffix(".idx")
        if base in self.fail:
            return FakeResponse(self.fail[base], url=url)
        if base not in self.files:
            return FakeResponse(404, url=url)
        if url.endswith(".idx"):
            return FakeResponse(200, self.idx[base].encode(), url=url)
        first, _, last = (headers or {})["Range"].removeprefix("bytes=").partition("-")
        return FakeResponse(206, self.files[base][int(first) : int(last) + 1 if last else None], url=url)

    def head(self, url: str, timeout=None) -> FakeResponse:
        if url in self.fail:
            return FakeResponse(self.fail[url], url=url)
        if url not in self.files:
            return FakeResponse(404, url=url)
        return FakeResponse(200, headers={"Content-Length": str(len(self.files[url]))}, url=url)


@pytest.fixture
def bucket() -> Bucket:
    return Bucket()
