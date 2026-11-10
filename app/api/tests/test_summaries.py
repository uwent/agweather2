"""County and state summaries (PLAN.md Phase 6 C5) on the fixture archive: 2 × 3 cells in Fayette County, Iowa
(19065), observed July 1–10 2025, so the county is a sliver covered and its statistics need `min_coverage=0`."""

import numpy as np
import pytest

from agdata import regions
from agdata.testing import WINDOW
from api.routes import summaries

FAYETTE = "19065"


def get(client, layer, **params):
    return client.get(f"/api/v2/summaries/{layer}", params)


def fayette():
    found = next(a for a in regions.areas("county") if a is not None and a.fips == FAYETTE)
    return found


@pytest.mark.django_db
def test_a_countys_statistics_are_those_of_its_cells(client, archive):
    body = get(client, "air_temperature_max", date="2025-07-05", region=FAYETTE, min_coverage=0).json()
    data, county = body["data"], fayette()
    assert data["fips"] == [FAYETTE] and data["name"] == ["Fayette County"] and data["state"] == ["IA"]
    assert data["cells"] == [county.cells] and data["cells_with_data"] == [WINDOW.size]
    assert data["coverage"] == [round(WINDOW.size * 100 / county.cells, 1)] and data["complete"] == [False]
    assert data["area"] == [round(county.land_m2 / 2_589_988.110336)]  # square miles
    assert body["meta"]["units"]["area"] == "sq mi"
    cells = client.get("/api/v2/grids/air_temperature_max", {"date": "2025-07-05", "region": FAYETTE}).json()["data"][
        "air_temperature_max"
    ]
    assert data["min"] == [min(cells)] and data["max"] == [max(cells)]
    assert data["mean"][0] == pytest.approx(np.mean(cells), abs=0.1)
    assert data["date"] == ["2025-07-05"] and data["kind"] == ["observed"]


@pytest.mark.django_db
def test_under_the_coverage_threshold_a_row_has_no_statistics(client, archive):
    body = get(client, "air_temperature_max", date="2025-07-05", region=FAYETTE).json()
    assert body["data"]["mean"] == [None] and body["data"]["cells_with_data"] == [WINDOW.size]
    assert body["meta"]["summary"]["below_coverage"] == 1 and body["meta"]["request"]["min_coverage"] == 50
    assert any("'min_coverage'" in w for w in body["meta"]["warnings"])


@pytest.mark.django_db
def test_by_state_and_in_metric(client, archive):
    body = get(client, "air_temperature_max", date="2025-07-05", by="state", min_coverage=0, units="metric").json()
    data = body["data"]
    assert data["fips"] == ["19"] and data["name"] == ["Iowa"] and "state" not in data
    iowa = next(a for a in regions.areas("state") if a is not None and a.state == "IA")
    assert data["area"] == [round(iowa.land_m2 / 1e6)] and body["meta"]["units"]["area"] == "km²"
    assert data["cells"] == [iowa.cells] and body["meta"]["units"]["mean"] == "°C"


@pytest.mark.django_db
def test_each_month_of_a_range_and_each_day(client, archive):
    monthly = get(
        client, "precipitation_sum", start="2025-06-20", end="2025-07-09", stat="sum", interval="month", min_coverage=0
    ).json()
    assert monthly["data"]["month"] == ["2025-06", "2025-07"] and "date" not in monthly["data"]
    assert monthly["data"]["mean"][0] is None and monthly["data"]["mean"][1] > 0  # June is before the archive
    daily = get(client, "air_temperature_max", start="2025-07-01", end="2025-07-03", region=FAYETTE).json()["data"]
    assert daily["date"] == ["2025-07-01", "2025-07-02", "2025-07-03"] and daily["fips"] == [FAYETTE] * 3


@pytest.mark.django_db
def test_a_first_day_counts_cells_without_one_as_covered(client, archive):
    found = get(client, "air_temperature_min", first="below_99", end="2025-07-09", min_coverage=0).json()["data"]
    assert found["cells_with_data"] == [WINDOW.size] and found["cells_none"] == [0]
    days = client.get("/api/v2/grids/air_temperature_min", {"first": "below_99", "end": "2025-07-09"}).json()["data"][
        "air_temperature_min"
    ]
    assert found["min"] == [min(days)] and found["max"] == [max(days)]
    none = get(client, "air_temperature_min", first="below_-40", end="2025-07-09", min_coverage=0).json()["data"]
    assert none["cells_with_data"] == [WINDOW.size] and none["cells_none"] == [WINDOW.size]
    assert none["mean"] == [None] and none["coverage"] == found["coverage"]


@pytest.mark.django_db
def test_a_map_of_levels_gives_each_levels_share(client, archive):
    data = get(client, "tar-spot", date="2025-07-05", min_coverage=0).json()["data"]
    shares = [data[name][0] for name in data if name.startswith("pct_")]
    assert sum(shares) == pytest.approx(100, abs=0.5) and "mean" not in data
    assert data["highest"][0] is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "status", "param"),
    [
        ({"date": "2025-07-05", "region": "WI"}, 422, "region"),
        ({"date": "2025-07-05", "region": "atlantis"}, 422, "region"),
        ({"date": "2025-07-05", "interval": "month"}, 422, "interval"),
        ({"start": "2025-07-01", "end": "2025-07-05", "interval": "month"}, 422, "interval"),
        ({"date": "2025-07-05", "min_coverage": "101"}, 422, "min_coverage"),
        ({"date": "2025-07-05", "by": "township"}, 422, "by"),
    ],
)
def test_requests_that_cant_be_summarized(client, archive, params, status, param):
    response = get(client, "air_temperature_max", **params)
    assert response.status_code == status and response.json()["errors"][0]["param"] == param


@pytest.mark.django_db
def test_hourly_layers_take_no_months_and_rows_are_limited(client, archive, monkeypatch):
    hourly = get(
        client, "air_temperature_hourly", start="2025-07-01T00:00Z", end="2025-07-02T00:00Z", stat="max",
        interval="month",
    )  # fmt: skip
    assert hourly.status_code == 422 and hourly.json()["errors"][0]["param"] == "interval"
    monkeypatch.setattr(summaries, "MAX_ROWS", 2)
    many = get(client, "air_temperature_max", start="2025-07-01", end="2025-07-03")
    assert many.status_code == 422 and many.json()["errors"][0]["code"] == "too_large"


@pytest.mark.django_db
def test_a_summary_revalidates_and_comes_as_csv(client, archive):
    first = get(client, "air_temperature_max", date="2025-07-05", min_coverage=0)
    again = client.get(
        "/api/v2/summaries/air_temperature_max",
        {"date": "2025-07-05", "min_coverage": 0},
        HTTP_IF_NONE_MATCH=first["ETag"],
    )
    assert again.status_code == 304
    text = get(client, "air_temperature_max", date="2025-07-05", format="csv", headers="false").content.decode()
    assert text.splitlines()[0].startswith("fips,name,state,date,kind,area,cells,cells_with_data,coverage,complete")
