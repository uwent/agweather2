"""Degree days and freezes at points (PLAN.md Phase 5 C), and the threshold checks they share, on the fixture
archive: observed days at 9–21 °C (48.2–69.8 °F) to July 9, the forecast's at 19–31 °C (66.2–87.8 °F)."""

import numpy as np
import pytest

from agdata.series import DailySeries, Forecast
from agmodels.degree_days import degree_days_modified, degree_days_sine
from api.routes import degree_days
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
OBSERVED_SINE_50 = float(degree_days_sine(48.2, 69.8, 50))


def get(client, path="degree-days", **params):
    return client.get(f"/api/v2/{path}", {"lat": LAT, "lng": LNG, **params})


def test_daily_and_running_degree_days_for_several_settings(client, archive):
    body = get(client, dd="sine_50,modified_50_86", start="2025-07-07", end="2025-07-12").json()
    data = body["data"]
    assert list(data) == [
        "date",
        "kind",
        "air_temperature_min",
        "air_temperature_max",
        "temperature_estimated",
        "dd_sine_50",
        "dd_sine_50_cum",
        "dd_modified_50_86",
        "dd_modified_50_86_cum",
    ]
    assert data["dd_sine_50"][0] == round(OBSERVED_SINE_50, 1)
    assert data["dd_sine_50"][-1] > 2 * data["dd_sine_50"][0]  # the forecast's warmer days (NBM-corrected)
    assert data["dd_modified_50_86"][0] == round(float(degree_days_modified(48.2, 69.8, 50, 86)), 1)
    assert data["dd_sine_50_cum"][1] == round(2 * OBSERVED_SINE_50, 1)
    assert data["temperature_estimated"] == [False] * 6
    meta = body["meta"]
    assert meta["units"]["dd_sine_50"] == "°F·d" and meta["units"]["air_temperature_min"] == "°F"
    assert meta["request"]["dd"] == ["sine_50", "modified_50_86"] and meta["request"]["threshold_units"] == "°F"
    assert meta["request"]["biofix"] == "2025-07-07" and meta["warnings"] == []
    assert "hrrr-shortwave v2" not in meta["summary"]["corrections"]  # degree days read no shortwave


def test_running_totals_start_at_the_biofix(client, archive):
    data = get(client, dd="sine_50", start="2025-07-07", end="2025-07-10", biofix="2025-07-09").json()["data"]
    assert data["dd_sine_50_cum"][:2] == [None, None]
    assert data["dd_sine_50_cum"][2] == round(OBSERVED_SINE_50, 1)
    # A biofix before the start counts from the biofix, though only the days from the start are shown
    data = get(client, dd="sine_50", start="2025-07-07", end="2025-07-07", biofix="2025-07-05").json()["data"]
    assert data["dd_sine_50_cum"] == [round(3 * OBSERVED_SINE_50, 1)]


def test_one_setting_by_base_upper_and_method(client, archive):
    data = get(client, base=50, upper=86, method="modified", date="2025-07-08").json()["data"]
    assert data["dd_modified_50_86"] == [round(float(degree_days_modified(48.2, 69.8, 50, 86)), 1)]
    response = get(client, dd="sine_50", base=50, date="2025-07-08")
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "conflict"


def test_metric_thresholds_give_the_same_degree_days_in_celsius(client, archive):
    body = get(client, dd="sine_10", units="metric", date="2025-07-08").json()
    assert body["meta"]["request"]["threshold_units"] == "°C"
    assert body["meta"]["units"]["dd_sine_10"] == "°C·d"
    assert body["data"]["dd_sine_10"] == [round(OBSERVED_SINE_50 * 5 / 9, 2)]  # 0.1 °F·d is 0.06 °C·d
    assert body["meta"]["warnings"] == []


def test_the_degree_day_table_totals_each_point_and_setting(client, archive):
    body = get(client, "degree-days/table", dd="sine_50,average_43", start="2025-07-02", end="2025-07-09").json()
    data = body["data"]
    assert data["setting"] == ["sine_50", "average_43"]
    assert data["dd"][0] == round(8 * OBSERVED_SINE_50, 1)
    assert data["estimated_days"] == [0, 0] and data["missing_days"] == [0, 0] and data["forecast_days"] == [0, 0]
    many = client.get(
        "/api/v2/degree-days/table",
        {"points": f"{LAT},{LNG};{LAT},{LNG}", "dd": "sine_50,average_43", "start": "2025-07-02", "end": "2025-07-09"},
    ).json()["data"]
    assert many["point"] == [0, 0, 1, 1] and many["setting"] == ["sine_50", "average_43"] * 2


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"dd": "sine_1000"}, "out_of_range"),  # no stored temperature reaches it
        ({"dd": "sine_-100"}, "out_of_range"),
        ({"dd": "sine_10_86", "units": "metric"}, "out_of_range"),  # 86 °C: beyond any stored air temperature
        ({"dd": "sine_86_50"}, "invalid"),  # upper below base
        ({"dd": "cubic_50"}, "invalid"),
        ({"dd": "sine_fifty"}, "invalid"),
        ({"dd": "sine_50,sine_50"}, "invalid"),
        ({}, "missing"),
        ({"base": 50, "method": "cubic"}, "invalid"),
    ],
)
def test_impossible_settings_are_refused(client, archive, params, code):
    response = get(client, date="2025-07-08", **params)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == code


@pytest.mark.parametrize(
    ("params", "said"),
    [
        ({"dd": "sine_70"}, "outside the usual 32–60 °F"),
        ({"dd": "sine_10"}, "if that's °C, add units=metric"),
        ({"dd": "sine_50", "units": "metric"}, "50 °C is 122 °F; thresholds follow units=metric"),
        ({"dd": "sine_10_60"}, "a degree-day upper threshold of 60 °F is outside the usual 70–95 °F"),
    ],
)
def test_unusual_settings_run_with_a_warning(client, archive, params, said):
    response = get(client, date="2025-07-08", **params)
    assert response.status_code == 200
    assert any(said in warning for warning in response.json()["meta"]["warnings"]), response.json()["meta"]


def test_short_gaps_are_estimated_and_flagged_and_long_ones_add_nothing():
    n = 12
    tmin, tmax = np.full(n, 10.0), np.full(n, 20.0)
    tmin[2:4] = np.nan  # a 2-day gap: bridged
    tmax[5:14] = np.nan  # past day 5: more than MAX_GAP_DAYS to the end, so missing
    days = DailySeries(
        dates=[],
        values={"air_temperature_min": tmin, "air_temperature_max": tmax},
        kinds=[],
        forecast=Forecast(path=None),
    )
    lo, hi, estimated, usable = degree_days.temperatures(days, n, "estimate")
    assert estimated.tolist() == [False, False, True, True] + [False] * 8
    assert usable.tolist() == [True] * 5 + [False] * 7
    daily = degree_days_sine(lo, hi, 50)
    total = degree_days.running(daily, usable, 0)
    assert np.all(total[5:] == total[4])  # missing days add nothing (D56)
    _, _, estimated, usable = degree_days.temperatures(days, n, "missing")
    assert not estimated.any() and usable.tolist() == [True, True, False, False, True] + [False] * 7


def test_freezes_at_thresholds(client, archive):
    data = get(client, "freeze", start="2025-07-02", end="2025-07-12").json()["data"]
    assert data["threshold"] == [32, 28, 24] and data["freeze_days"] == [0, 0, 0]
    assert data["first_fall"] == [None, None, None] and data["missing_days"] == [0, 0, 0]
    body = get(client, "freeze", start="2025-07-02", end="2025-07-12", thresholds="50").json()
    assert body["data"]["freeze_days"] == [9]  # July 2–10: the observed nights' 48.2 °F, not the forecast's
    assert body["data"]["first_fall"] == ["2025-07-02"] and body["data"]["last_spring"] == [None]
    assert any("outside the usual" in w for w in body["meta"]["warnings"])
    metric = get(client, "freeze", date="2025-07-08", units="metric").json()["meta"]["request"]
    assert metric["thresholds"] == [0.0, -2.2, -4.4] and metric["threshold_units"] == "°C"
