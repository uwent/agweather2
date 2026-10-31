from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest

from agdata.grid import NDFD, LatLonGrid, Window
from agdata.sources import era5land
from agdata.sources.openmeteo import SOIL_LAYERS, soil_at_depths

FIXTURES = Path(__file__).parent / "fixtures"
j, i = NDFD.cell_of(43.04, -88.0) or (0, 0)
MILWAUKEE = Window(j0=j - 4, j1=j + 4, i0=i - 4, i1=i + 16)  # as make_era5land_fixtures.py


@pytest.fixture(scope="module")
def hours() -> era5land.Hours:
    land = era5land.LandMask.load(FIXTURES / "era5land_milwaukee_lsm.npz")
    return era5land.read(FIXTURES / "era5land_milwaukee.grib", MILWAUKEE, land)


def test_a_day_reads_as_24_hours_by_valid_time(hours):
    # Snow depth is stamped as the previous day's 00Z plus a step and soil as an analysis; both key on validity
    assert hours.times == [datetime(2025, 12, 16, h, tzinfo=UTC) for h in range(24)]
    assert set(hours.values) == {"soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm", "snow_depth"}
    assert all(v.shape == (24, *MILWAUKEE.shape) for v in hours.values.values())


def test_values_are_in_stored_units(hours):
    soil = hours.values["soil_temperature_10cm"]
    assert np.nanmin(soil) > -5 and np.nanmax(soil) < 10  # °C, not K: a December day under snow
    snow = hours.values["snow_depth"]
    assert 0.05 < np.nanmax(snow) < 0.5  # metres of snow (a 10-20 cm cover that week)


def test_open_water_is_missing_and_the_shore_is_land(hours):
    soil = hours.values["soil_temperature_4cm"][0]
    _, lon = NDFD.window_latlon(MILWAUKEE)
    assert np.isfinite(soil[lon < -87.95]).all()  # the city, up to the shore
    assert np.isnan(soil[lon > -87.6]).all()  # Lake Michigan, 25 km out
    # Lake cells carry the lake's temperature at every depth; none of it reaches a land cell
    assert np.nanmax(soil) < 3


def test_depths_come_from_the_layers_as_ifs_does():
    layers = {name: np.array([float(k)]) for k, name in enumerate(SOIL_LAYERS)}  # 0, 1, 2 at 3.5, 17.5, 64 cm

    at = {name: value[0] for name, (value, _) in soil_at_depths(layers).items()}
    assert at["soil_temperature_4cm"] == pytest.approx(0.5 / 14)
    assert at["soil_temperature_30cm"] == pytest.approx(1 + 12.5 / 46.5)


def test_fill_coast_reaches_one_cell_from_land():
    values = np.array([[1.0, 3.0, np.nan, np.nan]] * 3)
    out = era5land.fill_coast(values, passes=1)
    np.testing.assert_allclose(out[:, 2], 3.0)
    assert np.isnan(out[:, 3]).all()


def test_the_land_mask_crops_and_matches_the_data_grid():
    land = era5land.LandMask.load(FIXTURES / "era5land_milwaukee_lsm.npz")
    north, west, south, _ = era5land.area(MILWAUKEE)
    assert (land.grid.first_lat, land.grid.first_lon) == (south, west)
    grid = LatLonGrid(name="part", first_lat=south + 0.1, first_lon=west + 0.1, step=0.1, ny=2, nx=2)
    np.testing.assert_array_equal(land.on(grid), land.fraction[1:3, 1:3] >= 0.5)
    with pytest.raises(ValueError, match="doesn't cover"):
        land.on(LatLonGrid(name="far", first_lat=north + 1, first_lon=west, step=0.1, ny=2, nx=2))


def test_a_request_covers_whole_days_of_one_month():
    r = era5land.request(date(2025, 12, 30), date(2025, 12, 31), MILWAUKEE)
    assert (r["year"], r["month"], r["day"]) == ("2025", "12", ["30", "31"])
    assert len(r["time"]) == 24 and r["area"] == era5land.area(MILWAUKEE)
    with pytest.raises(ValueError, match="within one month"):
        era5land.request(date(2025, 12, 31), date(2026, 1, 1), MILWAUKEE)
    assert era5land.days_of(date(2025, 12, 30), date(2026, 2, 2)) == [
        (date(2025, 12, 30), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 2)),
    ]
