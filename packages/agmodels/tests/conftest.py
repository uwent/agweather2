"""Fixtures for agmodels tests: the Crop Risk Tool parity data (tests/fixtures/make_crt_fixtures.R)."""

import csv
from functools import cache
from pathlib import Path

import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> dict[str, np.ndarray]:
    """A fixture's columns; numbers as float (empty and NA as NaN, TRUE/FALSE as 1/0), others as str."""
    with (FIXTURES / f"crt_{name}.csv").open() as f:
        rows = list(csv.DictReader(f))
    columns = {}
    for key in rows[0]:
        values = [row[key] for row in rows]
        try:
            columns[key] = np.array([_number(v) for v in values])
        except ValueError:
            columns[key] = np.array(values)
    return columns


@cache
def _read_cached(name: str) -> dict[str, np.ndarray]:
    return read(name)


@pytest.fixture
def crt():
    """`crt(name)`: a Crop Risk Tool fixture's columns."""
    return _read_cached


def _number(value: str) -> float:
    if value in ("", "NA"):
        return np.nan
    booleans = {"TRUE": 1.0, "FALSE": 0.0}
    return booleans[value] if value in booleans else float(value)
