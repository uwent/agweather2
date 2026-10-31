import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest

from agdata.sources import openmeteo

FIXTURES = Path(__file__).parent / "fixtures"

# Cell centres Open-Meteo returned for models=ecmwf_ifs (WISP 3's spec, 2026-10-03)
CELLS = {
    (44.12, -89.53): (44.112476, -89.58905),  # Hancock, WI
    (44.0773, -89.6): (44.04218, -89.58966),  # the next ring south
    (36.7, -119.8): (36.731106, -119.76378),  # Fresno, CA
    (50.4, -104.6): (50.36907, -104.57745),  # Regina, SK
    (30.27, -97.74): (30.263618, -97.69321),  # Austin, TX
    (46.8, -71.2): (46.78383, -71.24393),  # Québec
}


@pytest.mark.parametrize(("point", "centre"), list(CELLS.items()))
def test_points_snap_to_open_meteos_cells(point, centre):
    cell = openmeteo.cell_for(*point)
    assert cell.latitude == pytest.approx(centre[0], abs=1e-4)
    assert cell.longitude == pytest.approx(centre[1], abs=1e-4)


def test_a_cells_centre_maps_back_to_it():
    rng = np.random.default_rng(3)
    for lat, lon in zip(rng.uniform(18, 84, 50), rng.uniform(-180, -52, 50), strict=True):
        cell = openmeteo.cell_for(lat, lon)
        assert abs(cell.latitude - lat) < 0.06
        assert openmeteo.cell_for(cell.latitude, cell.longitude) == cell


def test_endpoints_by_date():
    today = date(2026, 10, 29)
    assert openmeteo.endpoint_for(date(2026, 10, 22), today) == "forecast"
    assert openmeteo.endpoint_for(date(2026, 10, 21), today) == "historical"
    assert openmeteo.endpoint_for(date(2022, 1, 1), today) == "historical"
    assert openmeteo.endpoint_for(date(2021, 12, 31), today) == "archive"
    assert openmeteo.url("forecast", None) == "https://api.open-meteo.com/v1/forecast"
    assert openmeteo.url("archive", "key") == "https://customer-archive-api.open-meteo.com/v1/archive"
    assert openmeteo.weight(variables=12, days=28) == pytest.approx(2.4)
    assert openmeteo.weight(variables=3, days=3) == 1


class Recorded:
    """Serves the recorded responses by endpoint and model; keeps the requests."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.calls = []

    def get(self, address, params: dict, timeout=None):
        self.calls.append((address, params))
        model = params.get("models", "era5")
        body = json.loads((FIXTURES / f"openmeteo_{self.endpoint}_{model}.json").read_text())

        class Response:
            status_code = 200
            content = b"{}"

            def json(self):
                return body

        return Response()


def test_models_merge_in_order_and_convert():
    cell = openmeteo.cell_for(36.12, -97.07)
    session = Recorded("historical")
    hours, calls = openmeteo.fetch("historical", cell, date(2025, 6, 1), date(2025, 6, 3), session=session)  # type: ignore[arg-type]
    assert [p["models"] for _, p in session.calls] == ["ncep_nbm_conus", "best_match", "ecmwf_ifs"]
    assert all(p["wind_speed_unit"] == "ms" and p["timeformat"] == "unixtime" for _, p in session.calls)
    assert calls == 3
    assert hours.start == datetime(2025, 6, 1, tzinfo=UTC) and hours.count == 72
    v = hours.values
    assert hours.sources["air_temperature"] == "ncep_nbm_conus"
    assert hours.sources["surface_pressure"] == "best_match"  # NBM has none
    assert np.isfinite(v["surface_pressure"]).all() and 90 < np.nanmean(v["surface_pressure"]) < 105  # kPa
    assert np.isfinite(v["air_temperature"]).all() and 10 < np.nanmean(v["air_temperature"]) < 35
    assert np.nanmax(v["shortwave_radiation"]) > 500 and np.nanmin(v["shortwave_radiation"]) == 0
    # Soil between the layers' middles: 4 cm close to the top layer, 30 cm between the second and third
    nbm = json.loads((FIXTURES / "openmeteo_historical_ecmwf_ifs.json").read_text())["hourly"]
    top = np.array(nbm["soil_temperature_0_to_7cm"], dtype=float)
    assert np.abs(v["soil_temperature_4cm"] - top).max() < 0.5
    assert np.isfinite(v["relative_humidity"]).all() and (v["relative_humidity"] <= 100.01).all()
    daytime_et0 = v["et0"][16:24]  # hours ending 16–23Z: late morning to late afternoon in Oklahoma
    assert (daytime_et0 > 0.1).all() and np.nansum(v["et0"][:24]) > 3  # a June day, mm


def test_the_archive_takes_weather_from_era5_and_soil_and_snow_from_era5_land():
    cell = openmeteo.cell_for(36.12, -97.07)
    session = Recorded("archive")
    hours, _ = openmeteo.fetch("archive", cell, date(2015, 6, 1), date(2015, 6, 2), session=session)  # type: ignore[arg-type]
    assert [params.get("models") for _, params in session.calls] == [None, "era5_land"]
    assert "soil_temperature_0_to_7cm" not in session.calls[0][1]["hourly"]
    assert hours.count == 48 and np.isfinite(hours.values["soil_temperature_30cm"]).all()
    assert (hours.values["snow_depth"] == 0).all()  # cm, Oklahoma in June
    assert hours.sources["air_temperature"] == "era5" and hours.sources["soil_temperature_10cm"] == "era5_land"


def test_corrections_keep_the_raw_values_and_say_what_they_did():
    from agdata import corrections

    cell = openmeteo.cell_for(36.12, -97.07)
    hours, _ = openmeteo.fetch("historical", cell, date(2025, 6, 1), date(2025, 6, 3), session=Recorded("historical"))  # type: ignore[arg-type]
    fixed = openmeteo.correct(hours, cell, "historical")
    assert fixed.corrections == (corrections.OPENMETEO_SHORTWAVE.label, corrections.OPENMETEO_RH.label)
    np.testing.assert_array_equal(fixed.raw["shortwave_radiation"], hours.values["shortwave_radiation"])
    np.testing.assert_array_equal(fixed.raw["dew_point"], hours.values["dew_point"])
    np.testing.assert_array_equal(fixed.values["air_temperature"], hours.values["air_temperature"])  # kept
    day = hours.values["shortwave_radiation"] > 100
    assert (fixed.values["shortwave_radiation"][day] < hours.values["shortwave_radiation"][day]).mean() > 0.9
    assert (fixed.values["dew_point"] <= fixed.values["air_temperature"]).all()
    assert fixed.values["relative_humidity"].mean() > hours.values["relative_humidity"].mean()  # wetter, as fitted
    assert fixed.values["et0"].sum() < hours.values["et0"].sum()  # less sun, more humid
    # ERA5 (the archive endpoint) wasn't checked, so it isn't corrected
    assert openmeteo.correct(hours, cell, "archive") is hours


def test_the_corrections_table_is_current():
    from agdata import corrections

    path = Path(__file__).parents[3] / "docs" / "corrections.md"
    assert path.read_text() == corrections.markdown(), "run: uv run python -m agdata.corrections > docs/corrections.md"
