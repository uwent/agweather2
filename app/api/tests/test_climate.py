"""Normals at points (`/climate/normals`, D86) over the fixture archive's five gridMET years (`last5` at its NOW,
`fixture_archive.climate_values`): known answers for daily normals, percentiles, running totals, degree days, months,
rolling windows and areas; the period's rules; and a point's normals against the stored normal maps at its cell."""

import shutil
from datetime import date

import numpy as np
import pytest

from agdata import climatestore, normals
from agdata.grid import NDFD, Window
from agdata.testing import WINDOW
from api.tests.fixture_archive import CLIMATE_YEARS, POINT

LAT, LNG = POINT
METRIC = {"lat": LAT, "lng": LNG, "units": "metric", "period": "last5"}


def get(client, **params):
    return client.get("/api/v2/climate/normals", {**METRIC, **params})


def data(response) -> dict:
    assert response.status_code == 200, response.json()
    return response.json()["data"]


def error(response) -> dict:
    assert response.status_code >= 400, response.json()
    return response.json()["errors"][0]


def test_daily_normals_and_percentiles(client, climate_archive):
    found = data(get(client, start="2025-07-01", end="2025-07-03", percentiles="10,50,90"))
    assert found["date"] == ["2025-07-01", "2025-07-02", "2025-07-03"]
    assert found["day_of_year"] == [183, 184, 185]  # a leap year's: July 1 is the same slot every year
    assert found["air_temperature_max"] == [22.0] * 3  # 20 to 24 °C over the years
    assert found["air_temperature_max_p10"] == [20.0] * 3
    assert found["air_temperature_max_p50"] == [22.0] * 3
    assert found["air_temperature_max_p90"] == [24.0] * 3
    assert found["air_temperature_min"] == [10.0] * 3
    assert found["precipitation_sum"] == [1.0] * 3


def test_running_totals_start_on_start(client, climate_archive):
    found = data(get(client, start="2025-01-01", end="2025-01-10", vars="precipitation_sum"))
    assert found["precipitation_sum_cum"][0] == 1.0
    assert found["precipitation_sum_cum"][-1] == 10.0
    later = data(get(client, start="2025-06-01", end="2025-06-30", vars="precipitation_sum"))
    assert later["precipitation_sum_cum"][-1] == 30.0


def test_degree_days_from_each_year_s_own_days(client, climate_archive):
    # Modified 10/30 °C (50/86 °F): 9 + 0.9 °F·d a year from 2020, 10.8 on average, or 6 °C·d
    response = get(client, start="2025-01-01", end="2025-01-10", dd="modified_10_30")
    found = data(response)
    assert "air_temperature_max" not in found  # only the degree days when dd is given alone
    assert found["dd_modified_10_30"] == pytest.approx([6.0] * 10, abs=0.06)
    assert found["dd_modified_10_30_cum"][-1] == pytest.approx(60.0, abs=0.06)
    assert response.json()["meta"]["units"]["dd_modified_10_30"] == "°C·d"


def test_months_and_years_from_each_year_s_own(client, climate_archive):
    months = data(
        get(
            client,
            start="2025-06-01",
            end="2025-07-31",
            interval="month",
            vars="precipitation_sum,air_temperature_max",
            percentiles="10",
        )
    )
    assert months["month"] == ["2025-06", "2025-07"]
    assert months["precipitation_sum"] == [30.0, 31.0]
    assert months["air_temperature_max"] == [22.0, 22.0]
    assert months["air_temperature_max_p10"] == [20.4, 20.4]  # among the years' means: 20, 21, 22, 23, 24
    year = data(get(client, start="2025-06-01", end="2025-06-30", interval="year", vars="precipitation_sum"))
    assert year == {"precipitation_sum": [30.0]}


def test_rolling_windows_wrap_the_year(client, climate_archive):
    found = data(
        get(client, start="2025-01-01", end="2025-01-02", vars="precipitation_sum,air_temperature_max", roll="7")
    )
    assert found["precipitation_sum_7d"] == [7.0, 7.0]  # a sum, reaching back into December
    assert found["air_temperature_max_7d"] == [22.0, 22.0]  # a mean


def test_an_area_averages_the_cells_around(client, climate_archive):
    response = get(client, date="2025-07-01", radius="5")  # km
    assert data(response)["air_temperature_max"] == [22.0]
    assert response.json()["meta"]["location"]["area"]["cells"] > 1


def test_the_period_s_years_and_sources(client, climate_archive):
    meta = get(client, date="2025-07-01").json()["meta"]
    assert meta["summary"]["first_year"] == 2020 and meta["summary"]["last_year"] == 2024
    assert meta["summary"]["years"] == 5 and meta["summary"]["years_with_data"] == 5
    assert meta["sources"] == ["gridmet"]
    longer = get(client, date="2025-07-01", period="last30").json()
    assert "we don't yet have 25 of its years (1995–2019)" in longer["meta"]["warnings"][0]
    assert longer["data"]["air_temperature_max"] == [22.0]  # from the five there are


def test_refusals(client, climate_archive):
    assert error(get(client, lat=46.0, lng=-100.0))["code"] == "not_applicable"
    assert error(get(client, start="2024-12-01", end="2025-01-31"))["param"] == "end"
    assert error(get(client, vars="air_temperature_mean", period="last30"))["param"] == "vars"
    assert error(get(client, interval="month", roll="7"))["param"] == "roll"
    assert error(get(client, percentiles="0,50"))["param"] == "percentiles"
    assert error(get(client, window="100"))["param"] == "window"


def test_an_unchanged_answer_is_not_sent_again(client, climate_archive):
    first = get(client, date="2025-07-01")
    again = client.get(
        "/api/v2/climate/normals", {**METRIC, "date": "2025-07-01"}, HTTP_IF_NONE_MATCH=first.headers["ETag"]
    )
    assert again.status_code == 304


def test_a_point_matches_the_stored_maps_at_its_cell(client, climate_archive, tmp_path):
    """D86: the points compute from the years, the maps store the same statistics; they agree to the packing."""
    for year in CLIMATE_YEARS:
        shutil.copytree(climatestore.path(climate_archive, year), climatestore.path(tmp_path, year))
    normals.build(tmp_path, "last5", list(CLIMATE_YEARS), set(), WINDOW, days_per_chunk=366)
    cell = NDFD.cell_of(LAT, LNG)
    assert cell is not None
    at = Window(j0=cell[0], j1=cell[0] + 1, i0=cell[1], i1=cell[1] + 1)

    def stored(name: str, day: date) -> float:
        return float(normals.read_map(tmp_path, "last5", name, day, at)[0, 0])

    day = date(2025, 9, 30)
    found = data(get(client, date="2025-09-30", vars="air_temperature_max,precipitation_sum"))
    assert found["air_temperature_max"][0] == pytest.approx(stored("air_temperature_max/mean", day), abs=0.05)
    us = client.get(
        "/api/v2/climate/normals",
        {"lat": LAT, "lng": LNG, "period": "last5", "start": "2025-01-01", "end": "2025-09-30", "dd": "modified_50_86"},
    ).json()["data"]
    assert us["dd_modified_50_86_cum"][-1] == pytest.approx(stored("dd_modified_50_86/mean", day), abs=0.3)
    totals = data(get(client, start="2025-01-01", end="2025-09-30", vars="precipitation_sum"))
    assert totals["precipitation_sum_cum"][-1] == pytest.approx(stored("precipitation/mean", day), abs=0.1)
    assert np.isfinite(stored("air_temperature_max/p90", day))
