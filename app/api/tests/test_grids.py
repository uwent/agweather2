"""Grids and the layer catalog (PLAN.md Phase 5 E) on the fixture archive: 2 × 3 cells in Fayette County, Iowa,
observed July 1–10 2025 at 15 °C ± 6 and 0.1 mm an hour, then an NBM run at 25 °C ± 6."""

import io
from dataclasses import replace
from datetime import date

import numpy as np
import pytest
import tifffile
import xarray as xr
from django.conf import settings
from pyproj import CRS, Transformer

from agdata import series
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from agdata.store import DAILY
from agdata.testing import WINDOW
from api import layermaps
from api.gridfiles import CRS_NAME
from api.routes import grids
from api.routes.models import SUSCEPTIBILITY
from api.tests.fixture_archive import NOW, POINT

LAT, LNG = POINT


def get(client, layer, http_headers=None, **params):
    return client.get(f"/api/v2/grids/{layer}", params, headers=http_headers)


@pytest.mark.django_db
def test_layers_list_every_layer_with_its_axis_and_range(client, archive):
    data = {layer["id"]: layer for layer in client.get("/api/v2/layers").json()["data"]}
    tmax = data["air_temperature_max"]
    assert tmax["time_axis"] == "day" and tmax["palette"] == "BuYlRd" and tmax["units"]["us"] == "°F"
    assert tmax["range"]["last"] == "2025-07-09" and tmax["range"]["forecast_through"] == "2025-07-21"
    assert data["air_temperature_hourly"]["range"]["last"] == "2025-07-10T15:00Z"
    assert data["degree_days"]["parameters"] == ["dd"] and "sum" in data["degree_days"]["stats"]
    assert data["dd_modified_50_86"]["stats"] == [] and data["dd_modified_50_86"]["group"] == "running_total"


def test_a_day_is_a_row_per_cell(client, archive):
    body = get(client, "air_temperature_max", date="2025-07-05", cells="true").json()
    data, meta = body["data"], body["meta"]
    assert len(data["lat"]) == WINDOW.size and set(data["date"]) == {"2025-07-05"} and set(data["kind"]) == {"observed"}
    assert set(data["air_temperature_max"]) == {69.8}  # 21 °C
    lat, lng = NDFD.latlon(data["j"][0], data["i"][0])
    assert (data["lat"][0], data["lng"][0]) == (round(float(lat), 4), round(float(lng), 4))
    assert (data["j"][0], data["i"][0]) == (WINDOW.j0, WINDOW.i0) and data["i"][1] == WINDOW.i0 + 1
    assert meta["units"]["air_temperature_max"] == "°F" and meta["sources"] == ["urma"]
    assert meta["request"]["window"] == [WINDOW.j0, WINDOW.j1, WINDOW.i0, WINDOW.i1]


def test_the_default_day_is_the_last_observed_everywhere(client, archive):
    assert get(client, "air_temperature_max").json()["meta"]["request"]["date"] == "2025-07-09"


def test_a_range_runs_into_the_forecast_with_each_days_kind(client, archive):
    data = get(client, "air_temperature_max", start="2025-07-09", end="2025-07-11", units="metric").json()["data"]
    assert data["kind"] == ["observed"] * 6 + ["partial"] * 6 + ["forecast"] * 6
    assert data["air_temperature_max"][0] == 21.0 and data["air_temperature_max"][-1] == 31.0


def test_csv_has_the_same_rows(client, archive):
    response = get(client, "precipitation_sum", date="2025-07-05", format="csv", headers="false")
    lines = response.content.decode().strip().splitlines()
    assert lines[0] == "date,kind,lat,lng,precipitation_sum" and len(lines) == 1 + WINDOW.size
    assert response["Content-Disposition"] == 'attachment; filename="agweather-precipitation_sum-20250705.csv"'


def test_a_stat_reduces_the_range_to_one_map_with_its_counts(client, archive):
    body = get(client, "precipitation_sum", start="2025-07-02", end="2025-07-08", stat="sum", units="metric").json()
    data = body["data"]
    assert "date" not in data and len(data["lat"]) == WINDOW.size
    assert data["precipitation_sum"] == [pytest.approx(16.8)] * WINDOW.size  # 7 days × 2.4 mm
    assert set(data["missing_days"]) == {0} and set(data["estimated_days"]) == {0}
    assert body["meta"]["summary"]["kinds"] == {"observed": 7} and body["meta"]["summary"]["stat"] == "sum"
    assert "total" not in body["meta"]["summary"]["stats"]["precipitation_sum"]  # a sum over cells means nothing


def test_days_without_data_are_counted_missing(client, archive):
    data = get(client, "air_temperature_max", start="2025-07-20", end="2025-07-23", stat="max").json()
    assert set(data["data"]["missing_days"]) == {3}  # the run ends at 13Z on July 21: not a whole day
    assert "3 days of the 4 asked for have no data yet and show as missing." in data["meta"]["warnings"]


def test_degree_days_from_running_totals_match_computing_them_and_the_points(client, archive):
    params = {"dd": "sine_50", "start": "2025-07-03", "end": "2025-07-08", "stat": "sum"}
    cubes = get(client, "degree_days", **params).json()
    computed = get(client, "degree_days", gaps="missing", **params).json()
    assert cubes["meta"]["summary"]["from_running_totals"] == ["dd_sine_50"]
    assert "from_running_totals" not in computed["meta"]["summary"]
    np.testing.assert_allclose(cubes["data"]["degree_days"], computed["data"]["degree_days"], atol=0.5)
    point = client.get(
        "/api/v2/degree-days/table",
        {"lat": POINT[0], "lng": POINT[1], "dd": "sine_50", "start": "2025-07-03", "end": "2025-07-08"},
    ).json()["data"]
    cell = _row_of(computed["data"], (LAT, LNG))
    assert computed["data"]["degree_days"][cell] == pytest.approx(point["dd"][0], abs=0.1)


def test_each_days_degree_days_for_any_setting(client, archive):
    data = get(client, "degree_days", dd="modified_48_86", start="2025-07-03", end="2025-07-04").json()["data"]
    assert len(data["degree_days"]) == 2 * WINDOW.size and set(data["kind"]) == {"observed"}
    assert data["degree_days"] == [pytest.approx((48.2 + 69.8) / 2 - 48, abs=0.1)] * 2 * WINDOW.size  # 9, 21 °C


def test_a_running_total_layer_is_each_days_total(client, archive):
    day = get(client, "dd_sine_50", date="2025-07-08").json()["data"]["dd_sine_50"]
    total, _ = series.grid_total(settings.DATA_DIR, "dd_sine_50", date(2025, 7, 8), WINDOW, now=NOW)
    assert day == pytest.approx(total.ravel(), abs=0.5)  # stored in °F·d, shown in us units


def test_bbox_region_and_stride_choose_the_cells(client, archive):
    lat, lng = NDFD.latlon(WINDOW.j0, WINDOW.i0)
    bbox = f"{float(lat) - 0.005},{float(lng) - 0.005},{float(lat) + 0.005},{float(lng) + 0.005}"
    data = get(client, "air_temperature_max", date="2025-07-05", bbox=bbox, cells="true").json()["data"]
    assert (data["j"], data["i"]) == ([WINDOW.j0], [WINDOW.i0])
    assert len(get(client, "air_temperature_max", date="2025-07-05", stride=2).json()["data"]["lat"]) == 2
    body = get(client, "air_temperature_max", date="2025-07-05", region="IA").json()
    assert len(body["data"]["lat"]) == WINDOW.size and body["meta"]["request"]["region"]["name"] == "Iowa"
    assert get(client, "air_temperature_max", date="2025-07-05", region="19065").status_code == 200
    error = get(client, "air_temperature_max", date="2025-07-05", region="WI").json()["errors"][0]
    assert error["code"] == "outside_box" and error["param"] == "region"


def test_a_latlon_grid_takes_the_cell_under_each_point(client, archive):
    body = get(client, "air_temperature_max", date="2025-07-05", grid="latlon", res="0.025").json()
    assert body["meta"]["request"]["method"] == "nearest"
    assert set(body["data"]["air_temperature_max"]) == {69.8}
    assert all(round(v / 0.025) * 0.025 == pytest.approx(v) for v in body["data"]["lat"])


def test_netcdf_keeps_the_lambert_grid(client, archive):
    response = get(client, "air_temperature_max", start="2025-07-04", end="2025-07-05", format="netcdf", units="metric")
    assert response["Content-Type"] == "application/x-netcdf"
    ds = xr.open_dataset(io.BytesIO(response.content), engine="h5netcdf")
    tmax = ds["air_temperature_max"]
    assert tmax.shape == (2, *WINDOW.shape) and float(tmax[0, 0, 0]) == pytest.approx(21.0)
    assert tmax.attrs["units"] == "degC" and tmax.attrs["cell_methods"] == "time: maximum"
    assert "request" in ds.attrs
    # One gridded variable, no 2-D lat/lon: GDAL opens the file as one raster rather than subdatasets, whose names
    # terra on Windows breaks on a drive letter's colon (D71)
    assert [k for k, v in ds.data_vars.items() if v.ndim >= 2] == ["air_temperature_max"]
    assert "lat" not in ds and "lon" not in ds and "coordinates" not in tmax.attrs
    assert ds["x"].attrs["axis"] == "X" and ds["y"].attrs["axis"] == "Y"
    assert "_FillValue" not in ds["x"].encoding or ds["x"].encoding["_FillValue"] is None
    # The CF attributes and the WKT name one projection, the grid's own
    mapping = ds["lambert_conformal_conic"].attrs
    assert mapping["longitude_of_central_meridian"] == -95.0 and mapping["standard_parallel"] == 25.0
    crs = CRS.from_wkt(mapping["crs_wkt"])
    assert crs.name == CRS_NAME and CRS.from_cf(mapping).equals(crs, ignore_axis_order=True)
    lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(float(ds.x[1]), float(ds.y[1]))
    expected = NDFD.latlon(WINDOW.j0 + 1, WINDOW.i0 + 1)
    assert (lat, lon) == (pytest.approx(float(expected[0]), abs=1e-7), pytest.approx(float(expected[1]), abs=1e-7))


def test_netcdf_on_a_latlon_grid_has_plain_coordinates(client, archive):
    response = get(
        client,
        "precipitation_sum",
        start="2025-07-02",
        end="2025-07-08",
        stat="sum",
        grid="latlon",
        res="0.025",
        format="netcdf",
    )
    ds = xr.open_dataset(io.BytesIO(response.content), engine="h5netcdf")
    assert ds["precipitation_sum"].dims == ("lat", "lon") and ds["lat"].attrs["axis"] == "Y"
    assert ds["precipitation_sum"].attrs["cell_methods"] == "time: sum time: sum"
    assert "lambert_conformal_conic" not in ds
    assert "missing_days" not in ds  # one gridded variable a file (D71): the counts come with JSON, CSV and GeoTIFF


def test_geotiff_has_a_band_per_day_north_up(client, archive):
    response = get(client, "air_temperature_max", start="2025-07-09", end="2025-07-10", format="geotiff")
    with tifffile.TiffFile(io.BytesIO(response.content)) as tif:
        bands = tif.asarray()
        page = tif.pages[0]
        assert isinstance(page, tifffile.TiffPage)
        tags = page.tags
        assert bands.shape == (2, *WINDOW.shape)
        assert tags["GeoKeyDirectoryTag"].value[3] == 20 and tags["ModelPixelScaleTag"].value[0] == NDFD.dx
        assert "2025-07-10" in tags["GDAL_METADATA"].value
    assert bands[0, 0, 0] == pytest.approx(69.8) and bands[1, 0, 0] == pytest.approx(87.8)


def test_answers_revalidate(client, archive):
    first = get(client, "air_temperature_max", date="2025-07-05")
    again = get(client, "air_temperature_max", http_headers={"If-None-Match": first["ETag"]}, date="2025-07-05")
    assert again.status_code == 304


def test_a_stale_variable_is_computed_from_the_hours(client, archive, monkeypatch):
    fresh = get(client, "air_temperature_max", date="2025-07-05").json()["data"]["air_temperature_max"]
    newer = replace(DAILY_VARIABLES["air_temperature_max"], version=DAILY_VARIABLES["air_temperature_max"].version + 1)
    monkeypatch.setitem(DAILY_VARIABLES, "air_temperature_max", newer)
    found = series.grid_days(
        settings.DATA_DIR, DAILY, "air_temperature_max", date(2025, 7, 5), date(2025, 7, 5), WINDOW, now=NOW
    )
    assert found.stale.all()
    calls = []
    real = layermaps.days_from_hours
    monkeypatch.setattr(layermaps, "days_from_hours", lambda *a: calls.append(a) or real(*a))
    assert get(client, "air_temperature_max", date="2025-07-06").json()["data"]["air_temperature_max"] == fresh
    assert len(calls) == 1
    response = get(client, "air_temperature_max", start="2025-07-01", end="2025-07-09", stat="max")
    assert response.status_code == 503 and response.json()["errors"][0]["code"] == "stale"


@pytest.mark.parametrize(
    ("layer", "params", "status", "param"),
    [
        ("nothing", {}, 404, "layer"),
        ("dd_sine_50", {"stat": "sum"}, 422, "stat"),
        ("air_temperature_max", {"stat": "sum"}, 422, "stat"),
        ("air_temperature_hourly", {"date": "2025-07-05"}, 422, "date"),
        ("air_temperature_max", {"time": "2025-07-05T12:00Z"}, 422, "time"),
        ("air_temperature_max", {"date": "2025-07-05", "start": "2025-07-01"}, 422, "date"),
        ("air_temperature_max", {"start": "2025-07-06", "end": "2025-07-05"}, 422, "start"),
        ("air_temperature_max", {"start": "2024-01-01", "end": "2025-07-05"}, 422, "start"),
        ("degree_days", {}, 422, "dd"),
        ("degree_days", {"dd": "sine_50,sine_48"}, 422, "dd"),
        ("air_temperature_max", {"dd": "sine_50"}, 422, "dd"),
        ("air_temperature_max", {"grid": "latlon"}, 422, "res"),
        ("air_temperature_max", {"grid": "latlon", "res": "0.01"}, 422, "res"),
        ("air_temperature_max", {"grid": "latlon", "res": "0.1", "stride": "2"}, 422, "stride"),
        ("air_temperature_max", {"res": "0.1"}, 422, "res"),
        ("air_temperature_max", {"bbox": "1,2,3"}, 422, "bbox"),
        ("air_temperature_max", {"bbox": "44,-90,45,-89"}, 422, "bbox"),
        ("air_temperature_max", {"region": "atlantis"}, 422, "region"),
        ("air_temperature_max", {"format": "xml"}, 422, "format"),
        ("air_temperature_max", {"output": "risk_level"}, 422, "output"),
        ("tar-spot", {"output": "nothing"}, 422, "output"),
        ("tar-spot", {"planting_date": "mid"}, 422, "planting_date"),
        ("late-blight-dsv", {"biofix": "2025-06-01"}, 422, "biofix"),
        ("corn-stages", {"black_layer_gdd": "2400"}, 422, "black_layer_gdd"),
        ("white-mold", {"irrigation": "all"}, 422, "irrigation"),
        ("white-mold", {"irrigation": "sometimes"}, 422, "irrigation"),
        ("tar-spot", {"start": "2025-07-01", "end": "2025-07-05", "stat": "sum"}, 422, "stat"),
        ("tar-spot", {"planting": "sometime"}, 422, "planting"),
        ("tar-spot", {"planting": "none", "output": "susceptibility"}, 422, "planting"),
        ("alfalfa-weevil", {"planting": "mid"}, 422, "planting"),
        ("soybean-stages", {"planting": "none"}, 422, "planting"),
        ("air_temperature_max", {"planting": "mid"}, 422, "planting"),
        ("air_temperature_max", {"time": "2025-07-08T12:00Z"}, 422, "time"),
        ("air_temperature_hourly", {"date": "2025-07-08"}, 422, "date"),
        ("air_temperature_hourly", {"time": "2025-07-08T12:00Z", "start": "2025-07-08T10:00Z"}, 422, "time"),
        ("air_temperature_hourly", {"time": "noon"}, 422, "time"),
        ("air_temperature_hourly", {"time": "2025-07-08T12:30Z"}, 422, "time"),
        (
            "air_temperature_hourly",
            {"start": "2025-06-01T00:00Z", "end": "2025-07-08T00:00Z", "stat": "mean"},
            422,
            "start",
        ),  # 889 hours: a map covers up to 744
    ],
)
def test_requests_that_cant_be_answered(client, archive, layer, params, status, param):
    response = get(client, layer, **params)
    assert response.status_code == status, response.content
    assert response.json()["errors"][0]["param"] == param


def test_too_many_values_for_json_points_to_the_files(client, archive, monkeypatch):
    monkeypatch.setattr(grids, "MAX_TEXT_VALUES", 10)
    error = get(client, "air_temperature_max", start="2025-07-01", end="2025-07-05").json()["errors"][0]
    assert error["code"] == "too_large" and "netcdf" in error["message"]
    assert get(client, "air_temperature_max", start="2025-07-01", end="2025-07-05", format="netcdf").status_code == 200


def _row_of(data: dict, point: tuple[float, float]) -> int:
    return min(
        range(len(data["lat"])), key=lambda k: (data["lat"][k] - point[0]) ** 2 + (data["lng"][k] - point[1]) ** 2
    )


def test_a_sum_past_the_running_totals_is_computed_from_the_days_there_are(client, archive):
    params = {"dd": "sine_50", "start": "2025-07-15", "stat": "sum"}
    to_run_end = get(client, "degree_days", end="2025-07-21", **params).json()  # July 21 isn't whole: missing
    assert to_run_end["meta"]["summary"]["from_running_totals"] == ["dd_sine_50"]
    assert set(to_run_end["data"]["missing_days"]) == {1}
    past = get(client, "degree_days", end="2025-07-23", **params).json()
    assert "from_running_totals" not in past["meta"]["summary"]
    assert set(past["data"]["missing_days"]) == {3}
    np.testing.assert_allclose(past["data"]["degree_days"], to_run_end["data"]["degree_days"], atol=0.5)


# Model layers (Phase 5 F3, D66): finished per cell from the stored ingredients


@pytest.mark.django_db
def test_layers_list_each_mapped_models_outputs_and_options(client, archive):
    data = {layer["id"]: layer for layer in client.get("/api/v2/layers").json()["data"]}
    tar = data["tar-spot"]
    assert tar["group"] == "model" and tar["time_axis"] == "day" and tar["options"] == []
    assert [o["name"] for o in tar["outputs"]] == ["risk_level", "probability", "susceptibility"]
    assert tar["palette"] == "BuYlRd_4" and tar["planting"] == ["early", "mid", "late", "none"]
    assert data["alfalfa-weevil"]["planting"] == [] and data["late-blight-dsv"]["planting"]
    assert data["white-mold"]["options"] == ["irrigation", "row_spacing"]
    assert data["corn-stages"]["outputs"][0]["name"] == "stage" and data["corn-stages"]["options"] == []
    assert data["alfalfa-weevil"]["outputs"][0]["name"] == "risk_level"
    assert [o["name"] for o in data["seedcorn-maggot"]["outputs"]][:2] == ["risk_level", "risk_value"]
    assert "degree-days" not in data and data["potato-volunteer"]["seasons"] == []  # none: the archive is July
    assert data["soybean-stages"]["outputs"][0]["name"] == "stage" and data["red-crown-rot"]["planting"]
    assert "susceptibility" in [o["name"] for o in data["white-mold"]["outputs"]]


def test_a_model_map_is_its_risk_level_per_cell(client, archive):
    body = get(client, "late-blight-dsv", date="2025-07-08").json()
    data, meta = body["data"], body["meta"]
    assert len(data["lat"]) == WINDOW.size and set(data["kind"]) == {"observed"}
    assert all(level in (0, 1, 2, 3, 4) for level in data["late-blight-dsv"])
    assert meta["request"]["model"]["id"] == "late-blight-dsv" and meta["request"]["output"] == "risk_level"
    assert meta["summary"]["model"]["output"] == "risk_level" and meta["sources"] == ["urma"]


def test_a_model_output_matches_the_point(client, archive):
    """The map's cell and `/models/{id}/run` at its center give the same severity total (the map from stored
    ingredients and running totals, the point from the hours)."""
    total = get(client, "late-blight-dsv", date="2025-07-08", output="dsv_total").json()["data"]
    row = _row_of(total, (LAT, LNG))
    run = client.get("/api/v2/models/late-blight-dsv/run", {"lat": LAT, "lng": LNG, "start": "2025-07-08"}).json()
    point = run["data"]["dsv_total"][0]
    assert total["late-blight-dsv"][row] == pytest.approx(point, abs=1)


def test_a_model_map_runs_into_the_forecast(client, archive):
    data = get(client, "tar-spot", start="2025-07-09", end="2025-07-12", output="probability").json()["data"]
    assert data["kind"] == ["observed"] * 6 + ["partial"] * 6 + ["forecast"] * 12
    assert all(v is None or 0 <= v <= 100 for v in data["tar-spot"])


def test_a_scenario_option_changes_the_map(client, archive):
    dry = get(client, "white-mold", date="2025-07-08", output="probability", irrigation="dry").json()
    wet = get(client, "white-mold", date="2025-07-08", output="probability", irrigation="irrigated").json()
    assert dry["meta"]["request"]["options"]["irrigation"] == "dry"
    assert dry["data"]["white-mold"] != wet["data"]["white-mold"]


def test_a_models_range_reduces_by_its_stats(client, archive):
    body = get(client, "late-blight-dsv", start="2025-07-02", end="2025-07-08", stat="max").json()
    assert set(body["data"]) >= {"late-blight-dsv", "missing_days"} and len(body["data"]["lat"]) == WINDOW.size


def test_a_model_outside_its_states_is_missing_with_a_warning(client, archive):
    body = get(client, "pecan-scab", date="2025-07-08").json()
    assert set(body["data"]["pecan-scab"]) == {None}
    assert any("was developed for" in w for w in body["meta"]["warnings"])


def test_a_model_map_revalidates(client, archive):
    first = get(client, "tar-spot", date="2025-07-05")
    again = get(client, "tar-spot", http_headers={"If-None-Match": first["ETag"]}, date="2025-07-05")
    assert again.status_code == 304
    other = get(
        client, "tar-spot", http_headers={"If-None-Match": first["ETag"]}, date="2025-07-05", output="probability"
    )
    assert other.status_code == 200


def test_a_model_map_as_a_file(client, archive):
    response = get(client, "corn-stages", date="2025-07-08", format="geotiff")
    assert response.status_code == 200
    with tifffile.TiffFile(io.BytesIO(response.content)) as tif:
        assert tif.pages[0].asarray().shape == WINDOW.shape


def test_a_gated_disease_map_has_its_crops_susceptibility_as_at_the_point(client, archive):
    """With each place's typical (mid) planting, the map's susceptibility and the point's for the same tier agree."""
    body = get(client, "tar-spot", date="2025-07-08", output="susceptibility").json()
    assert body["meta"]["request"]["planting"] == "mid"
    found = body["data"]["tar-spot"][_row_of(body["data"], (LAT, LNG))]
    params = {"lat": LAT, "lng": LNG, "start": "2025-07-08", "end": "2025-07-20", "planting_date": "mid"}
    point = client.get("/api/v2/models/tar-spot/run", params).json()["data"]
    assert SUSCEPTIBILITY[found] == point["susceptibility"][0]  # the point gives it in words
    plain = get(client, "tar-spot", date="2025-07-08", planting="none").json()
    assert plain["meta"]["request"]["planting"] == "none" and plain["meta"]["warnings"] == []


def test_a_crop_map_starts_at_each_places_planting_as_at_the_point(client, archive):
    for tier in ("early", "late"):
        body = get(client, "corn-stages", date="2025-07-08", output="gdd_total", planting=tier).json()
        params = {"lat": LAT, "lng": LNG, "start": "2025-07-08", "end": "2025-07-08", "planting_date": tier}
        point = client.get("/api/v2/models/corn-stages/run", params).json()["meta"]["request"]
        planting = body["meta"]["summary"]["planting"]
        assert planting["dates"] == [point["planting_date"]["date"]] * 2 and planting["cells_without"] == 0


def test_without_typical_planting_dates_a_map_warns_and_takes_the_defaults(client, archive):
    body = get(client, "late-blight-dsv", date="2025-07-08").json()  # no Veg Path potato place near Fayette County
    assert any("no typical potato planting dates in this area" in w for w in body["meta"]["warnings"])
    assert body["meta"]["request"]["planting"] == "mid"


def test_soybean_maps_take_a_tier(client, archive):
    """Soybean's stages are stored per tier (`agdata.croptiers`); the fixture's July has none written, so the map is
    missing, but the request is answered with the tier's dates."""
    for layer, params in (("soybean-stages", {}), ("white-mold", {"output": "susceptibility"}), ("red-crown-rot", {})):
        body = get(client, layer, date="2025-07-08", **params).json()
        assert body["meta"]["summary"]["planting"]["crop"] == "soybean", layer


def test_a_range_reduced_by_a_stat_is_limited_too(client, archive):
    # A stat returns one map, but reads every day of the range
    years = get(client, "air_temperature_max", start="2016-01-01", end="2025-07-08", stat="mean")
    assert years.status_code == 422 and years.json()["errors"][0]["code"] == "too_large"
    assert get(client, "air_temperature_max", start="2024-07-09", end="2025-07-08", stat="mean").status_code == 200


def test_an_hourly_layer_is_a_map_an_hour(client, archive):
    """15 °C ± 6 peaking at 15Z: 10.76 °C at 12Z, and 9.92 °C over 10–12Z."""
    data = get(client, "air_temperature_hourly", time="2025-07-10T12:00Z").json()["data"]
    assert set(data["time"]) == {"2025-07-10T12:00Z"} and set(data["kind"]) == {"observed"}
    assert set(data["air_temperature_hourly"]) == {51.4}
    reduced = get(client, "air_temperature_hourly", start="2025-07-10T10:00Z", end="2025-07-10T12:00Z", stat="mean")
    data = reduced.json()["data"]
    assert set(data["air_temperature_hourly"]) == {49.9} and set(data["missing_hours"]) == {0}


def test_an_hourly_range_out_of_order_says_both_times(client, archive):
    error = get(client, "air_temperature_hourly", start="2025-07-08T12:00Z", end="2025-07-08T10:00Z").json()["errors"]
    assert error[0]["message"] == (
        "The start time (noon UTC, July 8, 2025) is after the end time (10 a.m. UTC, July 8, 2025). Choose a start on "
        "or before the end."
    )


def test_a_model_map_says_when_its_out_of_season_or_before_its_biofix(client, archive):
    cotton = get(client, "cotton-planting", date="2025-07-05").json()["meta"]["warnings"]
    assert "These dates are outside the model's season (March 15 to June 30)." in cotton
    earworm = get(client, "corn-earworm", date="2025-07-08").json()["meta"]["warnings"]
    assert "The season starts at the biofix, August 1, 2025, so nothing has accumulated yet." in earworm


def test_a_mean_of_degree_days_is_the_days_sum_over_their_number(client, archive):
    days = get(client, "degree_days", dd="sine_50", start="2025-07-02", end="2025-07-05").json()["data"]
    mean = get(client, "degree_days", dd="sine_50", start="2025-07-02", end="2025-07-05", stat="mean").json()["data"]
    first_cell = days["degree_days"][:: WINDOW.size]  # rows day by day, each day's cells in the same order
    assert len(first_cell) == 4
    assert mean["degree_days"][0] == pytest.approx(sum(first_cell) / 4, abs=0.05)


def test_an_archive_with_no_data_is_a_503(client, settings):
    settings.SERVICE_BOX = "42.84,-91.69,42.866,-91.627"  # DATA_DIR is an empty folder (app/conftest.py)
    response = get(client, "air_temperature_max")
    assert response.status_code == 503 and response.json()["errors"][0]["code"] == "no_data"


def test_a_stat_without_a_start_runs_from_january_1(client, archive):
    # As at points: a total with no start is the season to date, not the last day alone
    request = get(client, "precipitation_sum", stat="sum").json()["meta"]["request"]
    assert (request["start"], request["end"], request["stat"]) == ("2025-01-01", "2025-07-09", "sum")
    assert get(client, "air_temperature_max").json()["meta"]["request"]["date"] == "2025-07-09"  # no stat: one day


def test_an_hourly_stat_needs_a_start(client, archive):
    error = get(client, "air_temperature_hourly", stat="max").json()["errors"][0]
    assert (error["code"], error["param"]) == ("missing", "start")


@pytest.mark.parametrize("biofix", ["2025-07-03", "07-03"])
def test_a_degree_day_maps_biofix_starts_its_total(client, archive, biofix):
    by_start = get(client, "degree_days", dd="sine_50", start="2025-07-03", stat="sum", gaps="missing").json()
    by_biofix = get(client, "degree_days", dd="sine_50", biofix=biofix, gaps="missing").json()  # sum implied
    assert by_biofix["meta"]["request"]["start"] == "2025-07-03" and by_biofix["meta"]["request"]["stat"] == "sum"
    assert by_biofix["data"]["degree_days"] == by_start["data"]["degree_days"]


@pytest.mark.parametrize(
    ("layer", "params", "code"),
    [
        ("precipitation_sum", {"biofix": "07-03"}, "not_applicable"),  # a degree-day total's start only
        ("degree_days", {"dd": "sine_50", "biofix": "07-03", "start": "2025-07-03"}, "conflict"),
        ("degree_days", {"dd": "sine_50", "biofix": "07-03", "date": "2025-07-05"}, "conflict"),
        ("degree_days", {"dd": "sine_50", "biofix": "2025-07-08", "end": "2025-07-05"}, "out_of_order"),
        ("degree_days", {"dd": "sine_50", "biofix": "13-40"}, "invalid"),
        ("degree_days", {"dd": "sine_50", "biofix": "02-29"}, "invalid"),
    ],
)
def test_biofix_on_maps_that_cant_take_it(client, archive, layer, params, code):
    error = get(client, layer, **params).json()["errors"][0]
    assert error["code"] == code


@pytest.mark.django_db
def test_water_balance_is_a_map_of_rain_less_et0(client, archive):
    found = {}
    for layer in ("water_balance", "precipitation_sum", "et0_sum"):
        body = get(client, layer, start="2025-07-09", end="2025-07-11", units="metric").json()
        found[layer] = np.array(body["data"][layer], dtype=float)
    np.testing.assert_allclose(found["water_balance"], found["precipitation_sum"] - found["et0_sum"], atol=0.02)
    assert body["data"]["kind"] == ["observed"] * 6 + ["partial"] * 6 + ["forecast"] * 6
    layers = {layer["id"]: layer for layer in client.get("/api/v2/layers").json()["data"]}
    assert layers["water_balance"]["palette"] == "BrBG" and "sum" not in layers["water_balance"]["stats"]
    refused = get(client, "water_balance", start="2025-07-09", end="2025-07-11", stat="sum")
    assert refused.status_code == 422 and refused.json()["errors"][0]["param"] == "stat"
