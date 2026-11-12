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


# --- Freezes: every year's minimum is −5 °C on January 1–10 and from December 20, 10 °C between ---------------


def frost(client, path="climate/frost", **params):
    return client.get(f"/api/v2/{path}", {"lat": LAT, "lng": LNG, "period": "last5", **params})


def test_freeze_dates_and_season_length(client, climate_archive):
    found = data(frost(client, thresholds="32,20"))
    assert found["threshold"] == [32.0, 20.0]
    assert found["last_spring_p10"] == found["last_spring_p90"] == ["2025-01-10", None]  # −5 °C isn't 20 °F
    assert found["first_fall_p50"] == ["2025-12-20", None]
    assert found["season_days_p50"] == [345, 366]  # December 20 less January 10; no freeze: the whole year
    assert found["years_spring"] == [5, 5] and found["years_without_spring"] == [0, 5]
    assert found["years_without_fall"] == [0, 5]
    assert data(frost(client, probabilities="25"))["last_spring_p25"] == ["2025-01-10"] * 3


def test_freeze_chances_by_date(client, climate_archive):
    found = data(frost(client, "climate/frost/chances", thresholds="32", start="2025-01-09", end="2025-01-11"))
    assert found["season"] == ["spring"] * 3
    assert found["chance"] == [100, 0, 0]  # a freeze after January 9 every year, after January 10 none
    fall = data(frost(client, "climate/frost/chances", thresholds="32", start="2025-12-19", end="2025-12-20"))
    assert fall["season"] == ["fall"] * 2 and fall["chance"] == [0, 100]
    metric = frost(client, "climate/frost/chances", units="metric", date="2025-01-05")
    assert data(metric)["threshold"] == [0.0, -2.2, -4.4]


def test_freeze_refusals(client, climate_archive):
    assert error(frost(client, probabilities="0"))["param"] == "probabilities"
    assert error(frost(client, thresholds="cold"))["param"] == "thresholds"
    assert error(frost(client, "climate/frost/chances", start="2024-12-01", end="2025-01-31"))["param"] == "end"
    assert error(frost(client, lat=46.0, lng=-100.0))["code"] == "not_applicable"


# --- This year against normal: this year is the fixture archive's July 2025 (observed to the 10th, then the forecast)


def compare(client, **params):
    return client.get("/api/v2/climate/compare", {**METRIC, "start": "2025-07-01", "end": "2025-07-31", **params})


def test_this_year_against_last_year_and_normal(client, climate_archive):
    response = compare(client, dd="modified_10_30", vars="precipitation_sum")
    found = data(response)
    days = data(
        client.get(
            "/api/v2/degree-days",
            {"lat": LAT, "lng": LNG, "units": "metric", "dd": "modified_10_30", "start": "2025-07-01"},
        )
    )
    n = len(days["date"])
    assert found["kind"][:n] == days["kind"] and found["kind"][n:] == [None] * (31 - n)
    assert found["dd_modified_10_30_cum"][:n] == days["dd_modified_10_30_cum"]  # as /degree-days totals them
    assert found["dd_modified_10_30_cum"][n:] == [None] * (31 - n)  # nothing past the forecast
    assert found["dd_modified_10_30_cum_normal"][:3] == pytest.approx([6.0, 12.0, 18.0], abs=0.06)
    assert found["dd_modified_10_30_cum_last_year"][9] == pytest.approx(70.0, abs=0.06)  # 2024: 7 °C·d a day
    assert found["dd_modified_10_30_cum_normal_p10"][0] < 6.0 < found["dd_modified_10_30_cum_normal_p90"][0]
    assert found["precipitation_sum_cum_normal"][9] == 10.0 == found["precipitation_sum_cum_last_year"][9]
    total, normal = found["dd_modified_10_30_cum"][4], found["dd_modified_10_30_cum_normal"][4]
    assert found["dd_modified_10_30_departure"][4] == pytest.approx(total - normal, abs=0.1)
    assert found["dd_modified_10_30_percent_of_normal"][4] == round(total / normal * 100)
    rates = [5.0, 5.5, 6.0, 6.5, 7.0]  # each year's °C·d a day: 9 + 0.9 °F·d a year from 2020
    below = sum(r * 5 < total for r in rates) + 0.5 * sum(r * 5 == total for r in rates)
    assert found["dd_modified_10_30_percentile"][4] == round(100 * below / 5)


def test_days_ahead_of_normal_on_the_last_observed_day(client, climate_archive):
    response = compare(client, dd="modified_10_30")
    found, meta = data(response), response.json()["meta"]
    as_of = meta["summary"]["compare"]["as_of"]
    k = found["date"].index(as_of)
    assert found["kind"][k] == "observed" and found["kind"][k + 1] != "observed"
    total = found["dd_modified_10_30_cum"][k]
    nearest = round(total / 6.0) - 1  # the normal is 6 °C·d a day from July 1: day m has 6 (m + 1)
    assert meta["summary"]["compare"]["totals"]["dd_modified_10_30"]["days_ahead"] == nearest - k


def test_without_the_forecast_this_year_ends_with_the_observed_days(client, climate_archive):
    found = data(compare(client, forecast="false"))
    assert "forecast" not in found["kind"]
    last = max(k for k, kind in enumerate(found["kind"]) if kind is not None)
    assert found["precipitation_sum_cum"][last] is not None and found["precipitation_sum_cum"][last + 1] is None


def test_compare_refusals(client, climate_archive):
    assert error(compare(client, vars="air_temperature_max"))["param"] == "vars"  # not a total
    assert error(compare(client, end="2026-01-31"))["param"] == "end"
