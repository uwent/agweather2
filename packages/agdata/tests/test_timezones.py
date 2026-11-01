from types import SimpleNamespace

import pytest

from agdata import timezones
from agdata.grid import NDFD, Window
from agdata.timezones import window_timezones, zone_at


def test_a_window_across_the_michigan_shore_has_both_zones_and_each_cell_its_own():
    # Milwaukee (Central) and Muskegon-side cells across the lake (Eastern), a window of one row
    j, i = NDFD.cell_of(43.04, -87.9) or (0, 0)
    _, i_east = NDFD.cell_of(43.04, -86.3) or (0, 0)
    zones, index = window_timezones(Window(j0=j, j1=j + 1, i0=i, i1=i_east + 1))
    assert set(zones) >= {"America/Chicago", "America/Detroit"}
    assert zones[index[0, 0]] == "America/Chicago" and zones[index[0, -1]] == "America/Detroit"


@pytest.mark.parametrize(
    "longitude, zone", [(-40.0, "Etc/GMT+3"), (-7.4, "Etc/GMT"), (0.0, "Etc/GMT"), (40.0, "Etc/GMT-3")]
)
def test_a_point_in_no_zone_takes_a_fixed_offset_from_its_longitude(monkeypatch, longitude, zone):
    monkeypatch.setattr(timezones, "_finder", lambda: SimpleNamespace(timezone_at=lambda lng, lat: None))
    assert zone_at(10.0, longitude) == zone  # POSIX sign: west of Greenwich is plus


def test_a_point_is_in_the_zone_the_boundaries_say():
    assert zone_at(43.07, -89.4) == "America/Chicago"
    assert zone_at(40.7, -74.0) == "America/New_York"
