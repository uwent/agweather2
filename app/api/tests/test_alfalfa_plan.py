"""The alfalfa cutting plan (`GET /models/alfalfa-growth/plan`, F5) over the fixture archive: July 2025's weather
and forecast, the normal of its five gridMET years (`fixture_archive.climate_values`: a killing freeze on January
1–10 and from December 20 every year, GDD 41/86 °F of 18 + 0.9 a year from 2020 on other days)."""

import pytest

from api.tests.fixture_archive import POINT

LAT, LNG = POINT
PATH = "/api/v2/models/alfalfa-growth/plan"


def plan(client, **params):
    return client.get(PATH, {"lat": LAT, "lng": LNG, "period": "last5", **params})


def ok(response) -> dict:
    assert response.status_code == 200, response.json()
    return response.json()


def error(response) -> dict:
    assert response.status_code == 422, response.json()
    return response.json()["errors"][0]


def test_a_season_planned_on_this_years_weather_and_the_normal(client, climate_archive):
    body = ok(plan(client))
    data, meta = body["data"], body["meta"]
    assert len(data["date"]) == 365 and data["date"][0] == "2025-01-01"
    k = data["date"].index("2025-07-01")
    assert data["kind"][k] == "observed" and "forecast" in data["kind"]
    assert data["kind"][-1] == "normal" and data["gdd"][-20] == pytest.approx(19.8, abs=0.05)  # 18 + 0.9 × 2 a day
    # The chance of a killing freeze: still to come after January 9 every year, none after January 10; all by
    # December 20
    chance = dict(zip(data["date"], data["kill_chance"], strict=True))
    assert (chance["2025-01-09"], chance["2025-01-10"], chance["2025-12-19"], chance["2025-12-20"]) == (100, 0, 0, 100)
    p = meta["summary"]["plan"]
    assert p["season_end"] == {"date": "2025-12-20", "basis": "typical"}  # 1 year in 10 by December 20
    assert p["interval"] == 1000 and p["count"] is None
    cuts = p["cuts"]
    assert cuts[-1]["date"] == "2025-12-20"
    assert [d for d, cut in zip(data["date"], data["cut"], strict=True) if cut] == [c["date"] for c in cuts]
    assert all(900 <= c["gdd"] <= 1100 for c in cuts[1:]) and {c["status"] for c in cuts[1:]} == {"window"}
    # The sawtooth runs again from the day after each cut
    after = data["date"].index(cuts[1]["date"]) + 1
    assert data["gdd_since_cut"][after] == round(data["gdd"][after])
    # Every year froze on the last cut's day (December 20): before the regrowth could matter
    assert p["fall"]["years"] == 5 and p["fall"]["before_cut"] == 5
    assert p["thresholds"] == {
        "cut_from": 900,
        "cut_until": 1100,
        "fall_under": 360,
        "fall_over": 900,
        "killing_freeze": 24.0,
    }
    assert meta["units"]["gdd"] == "°F·d" and meta["units"]["kill_chance"] == "%"
    assert "gridmet" in meta["sources"]


def test_by_number_of_cuts_with_one_held(client, climate_archive):
    p = ok(plan(client, count=4, held="2025-06-15"))["meta"]["summary"]["plan"]
    assert len(p["cuts"]) == 4 and p["count"] == 4 and p["interval"] is None
    assert [c["date"] for c in p["cuts"] if c["held"]] == ["2025-06-15"]


def test_cuts_as_given_are_checked(client, climate_archive):
    body = ok(plan(client, cuts="2025-05-20,2025-07-05", held="2025-05-20", units="metric"))
    p = body["meta"]["summary"]["plan"]
    assert [c["date"] for c in p["cuts"]] == ["2025-05-20", "2025-07-05"]
    assert [c["held"] for c in p["cuts"]] == [True, False]
    assert p["interval"] is None and p["count"] is None
    assert p["thresholds"]["cut_from"] == 500 and p["thresholds"]["killing_freeze"] == -4.4  # °C·d, °C
    assert body["meta"]["units"]["gdd"] == "°C·d"
    assert p["fall"]["last_cut"] == "2025-07-05"
    # From July 5 to December 20, every year's regrowth runs well over 900 °F·d
    assert p["fall"]["over"] == 5


def test_an_unchanged_plan_is_not_sent_again(client, climate_archive):
    first = plan(client, interval=1100)
    again = client.get(
        PATH,
        {"lat": LAT, "lng": LNG, "period": "last5", "interval": 1100},
        HTTP_IF_NONE_MATCH=first.headers["ETag"],
    )
    assert again.status_code == 304


@pytest.mark.parametrize(
    ("params", "param"),
    [
        ({"interval": 1000, "count": 4}, "count"),
        ({"interval": 600}, "interval"),
        ({"interval": 1000, "units": "metric"}, "interval"),  # 1,800 °F·d
        ({"count": 20}, "count"),
        ({"cuts": "2025-06-01", "interval": 1000}, "cuts"),
        ({"cuts": "2025-06-01", "held": "2025-06-10"}, "held"),
        ({"held": "2024-06-10"}, "held"),
        ({"held": "June 10"}, "held"),
        ({"year": 1990}, "year"),
    ],
)
def test_refusals(client, climate_archive, params, param):
    assert error(plan(client, **params))["param"] == param


def test_only_inside_the_area_we_cover(client, climate_archive):
    assert error(plan(client, lat=46.0, lng=-100.0))["code"] == "not_applicable"
    assert error(client.get(PATH, {"points": f"{LAT},{LNG};{LAT},{LNG}"}))["param"] == "points"
