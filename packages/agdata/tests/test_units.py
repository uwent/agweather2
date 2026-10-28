import json
from pathlib import Path

import numpy as np
import pytest

from agdata.units import UNITS, convert, display_unit, to_display

CASES = json.loads((Path(__file__).parent / "fixtures" / "units_cases.json").read_text())


@pytest.mark.parametrize("case", CASES["convert"], ids=lambda c: f"{c['from']}->{c['to']}")
def test_shared_conversion_table(case):
    assert convert(case["value"], case["from"], case["to"]) == pytest.approx(case["expected"], abs=1e-6)


@pytest.mark.parametrize("case", CASES["display"], ids=lambda c: f"{c['stored']}-{c['system']}")
def test_shared_display_table(case):
    assert display_unit(case["stored"], case["system"]) == case["unit"]


def test_known_values():
    assert convert(0, "degC", "degF") == pytest.approx(32)
    assert convert(1, "in", "mm") == pytest.approx(25.4)
    assert convert(1, "mph", "m_s") == pytest.approx(0.44704)
    assert convert(10, "degC_day", "degF_day") == pytest.approx(18)  # an interval: no offset


def test_arrays_keep_missing_values():
    result = convert(np.array([0.0, np.nan, 100.0]), "degC", "degF")
    np.testing.assert_allclose(result, [32, np.nan, 212])
    assert convert(None, "mm", "in") is None


def test_round_trips_every_unit():
    for symbol, unit in UNITS.items():
        for other in (u for u in UNITS.values() if u.dimension == unit.dimension):
            assert convert(convert(12.5, symbol, other.symbol), other.symbol, symbol) == pytest.approx(12.5)


def test_mismatched_dimensions():
    with pytest.raises(ValueError):
        convert(1, "mm", "degC")
    with pytest.raises(ValueError):
        convert(1, "furlong", "mm")


def test_degree_days_display_in_the_users_system():
    assert to_display(1000, "degF_day", "imperial") == 1000
    assert to_display(1000, "degF_day", "metric") == pytest.approx(555.5556, abs=1e-3)
