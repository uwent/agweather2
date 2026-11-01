import sys
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from agdata.grid import NDFD, LatLonGrid, Window
from agdata.sources import era5land
from agdata.sources.grib import eccodes
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
    assert 5 < np.nanmax(snow) < 50  # cm of snow (a 10-20 cm cover that week), not metres


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


def test_snow_free_ground_reads_as_zero_not_missing():
    # ERA5-Land's snow-free cells come as packing's tiny negatives (-7.3e-24 m in December 2025's fields), which
    # QC's range (0-1000 cm) would drop: a snow-free day would read as missing
    from agdata.catalog import variable
    from agdata.qc import check_range

    metres = np.array([-7.34536e-24, 0.0, 0.37, np.nan])
    assert check_range(variable("snow_depth"), metres * 100)[1] == 1  # what happened before
    cleaned, dropped = check_range(variable("snow_depth"), era5land.no_negative_snow(metres) * 100)
    assert dropped == 0
    np.testing.assert_array_equal(cleaned, [0.0, 0.0, 37.0, np.nan])


def write_messages(path: Path, source: Path, keep, change=None) -> Path:
    """A GRIB file of the messages in `source` that `keep(short_name, valid_time)` accepts; `change(index, handle)`
    may alter a message before it's written."""
    index = 0
    with open(source, "rb") as f, open(path, "wb") as out:
        while (handle := eccodes.codes_grib_new_from_file(f)) is not None:
            try:
                if keep(eccodes.codes_get_string(handle, "shortName"), era5land.valid_time(handle)):
                    if change is not None:
                        change(index, handle)
                    eccodes.codes_write(handle, out)
                    index += 1
            finally:
                eccodes.codes_release(handle)
    return path


def global_mask_file(path: Path, land_at_longitudes: tuple[float, ...]) -> Path:
    """A 12-row, 0.1° global land-sea mask GRIB (longitudes 0..359.9, north to south) that is land at these
    longitudes and sea elsewhere."""
    handle = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib1")
    try:
        eccodes.codes_set_long(handle, "Ni", 3600)
        eccodes.codes_set_long(handle, "Nj", 12)
        for key, value in {
            "latitudeOfFirstGridPointInDegrees": 43.9,
            "latitudeOfLastGridPointInDegrees": 42.8,
            "longitudeOfFirstGridPointInDegrees": 0.0,
            "longitudeOfLastGridPointInDegrees": 359.9,
            "iDirectionIncrementInDegrees": 0.1,
            "jDirectionIncrementInDegrees": 0.1,
        }.items():
            eccodes.codes_set_double(handle, key, value)
        fraction = np.zeros((12, 3600))
        for lon in land_at_longitudes:
            fraction[:, round(lon / 0.1)] = 1.0
        eccodes.codes_set_values(handle, fraction.ravel())
        with open(path, "wb") as out:
            eccodes.codes_write(handle, out)
    finally:
        eccodes.codes_release(handle)
    return path


def test_a_global_land_mask_is_rolled_to_start_at_minus_180_and_runs_south_to_north(tmp_path):
    path = global_mask_file(tmp_path / "lsm.grib", land_at_longitudes=(0.0, 270.0))  # Greenwich and 90 °W
    land = era5land.read_land_mask(path)
    assert (land.grid.first_lon, land.grid.nx, land.grid.ny) == (-180.0, 3600, 12)
    assert land.grid.first_lat == pytest.approx(42.8)  # south first, though the file runs north to south
    assert land.fraction[:, 1800].tolist() == [1.0] * 12  # longitude 0 is column 1800 from -180
    assert land.fraction[:, 900].tolist() == [1.0] * 12  # 270 °E is -90
    assert land.fraction.sum() == 24  # nothing else is land


def test_a_land_mask_crops_to_a_window_and_survives_saving(tmp_path):
    mask = era5land.read_land_mask(global_mask_file(tmp_path / "lsm.grib", land_at_longitudes=(272.0,)))  # -88 °W
    j_mid, i_mid = NDFD.cell_of(43.3, -88.0) or (0, 0)
    window = Window(j0=j_mid - 1, j1=j_mid + 1, i0=i_mid - 2, i1=i_mid + 2)
    cropped = mask.crop(window)
    north, west, south, east = era5land.area(window)
    assert (cropped.grid.first_lat, cropped.grid.first_lon) == (south, west)
    assert cropped.fraction.shape == (round((north - south) / 0.1) + 1, round((east - west) / 0.1) + 1)
    lon_of_column = west + 0.1 * np.arange(cropped.fraction.shape[1])
    assert np.flatnonzero(cropped.fraction[0]).tolist() == [
        int(np.argmin(abs(lon_of_column + 88.0)))
    ]  # the one land column
    cropped.save(tmp_path / "crop.npz")
    loaded = era5land.LandMask.load(tmp_path / "crop.npz")
    assert loaded.grid == cropped.grid
    np.testing.assert_array_equal(loaded.fraction, cropped.fraction)


def test_a_land_mask_file_without_messages_is_refused(tmp_path):
    empty = tmp_path / "empty.grib"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="has no messages"):
        era5land.read_land_mask(empty)


def test_a_file_that_is_not_on_a_latitude_longitude_grid_is_refused():
    with pytest.raises(ValueError, match="regular latitude/longitude"):
        era5land.read_land_mask(FIXTURES / "urma_tmp_small.grb2")  # a Lambert grid


def test_a_file_without_messages_for_our_variables_has_no_hours(tmp_path):
    land = era5land.LandMask.load(FIXTURES / "era5land_milwaukee_lsm.npz")
    nothing = write_messages(
        tmp_path / "none.grib", FIXTURES / "era5land_milwaukee.grib", keep=lambda name, when: False
    )
    hours = era5land.read(nothing, MILWAUKEE, land)
    assert hours.times == [] and hours.values == {}


def test_an_hour_missing_one_of_the_variables_is_refused_not_half_filled(tmp_path):
    land = era5land.LandMask.load(FIXTURES / "era5land_milwaukee_lsm.npz")
    cut = write_messages(
        tmp_path / "cut.grib",
        FIXTURES / "era5land_milwaukee.grib",
        keep=lambda name, when: not (name == "sde" and when.hour == 3),
    )
    with pytest.raises(ValueError, match="hours missing variables") as error:
        era5land.read(cut, MILWAUKEE, land)
    assert "2025, 12, 16, 3, 0" in str(error.value) and "{'sde'}" in str(error.value)


def test_messages_on_different_grids_are_refused(tmp_path):
    land = era5land.LandMask.load(FIXTURES / "era5land_milwaukee_lsm.npz")

    def shift_second(index: int, handle) -> None:
        if index == 1:
            first = eccodes.codes_get_double(handle, "latitudeOfLastGridPointInDegrees")
            eccodes.codes_set_double(handle, "latitudeOfLastGridPointInDegrees", first + 0.1)

    shifted = write_messages(
        tmp_path / "shifted.grib", FIXTURES / "era5land_milwaukee.grib", lambda n, w: True, shift_second
    )
    with pytest.raises(ValueError, match="different grids"):
        era5land.read(shifted, MILWAUKEE, land)


def test_the_land_mask_and_a_day_are_requested_with_the_account_key(monkeypatch, tmp_path):
    calls = []

    class Client:
        def __init__(self, **kwargs):
            calls.append(("client", kwargs))

        def retrieve(self, dataset, request, target):
            calls.append(("retrieve", dataset, request, target))

    monkeypatch.setitem(sys.modules, "cdsapi", SimpleNamespace(Client=Client))
    target = tmp_path / "day.grib"
    assert era5land.retrieve(date(2025, 12, 16), date(2025, 12, 16), MILWAUKEE, target, key="secret") == target
    assert calls[0] == ("client", {"url": era5land.API, "key": "secret", "quiet": True, "progress": False})
    assert calls[1][1:] == (
        "reanalysis-era5-land",
        era5land.request(date(2025, 12, 16), date(2025, 12, 16), MILWAUKEE),
        str(target),
    )

    calls.clear()
    assert era5land.retrieve_land_mask(tmp_path / "lsm.grib", key="secret") == tmp_path / "lsm.grib"
    request = calls[1][2]
    assert request["variable"] == ["land_sea_mask"] and "area" not in request  # the whole globe, whatever the area
