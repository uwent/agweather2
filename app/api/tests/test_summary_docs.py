"""Each endpoint page's "In meta.summary" list (`api/docs/<operation>.md`) names every key a response's `meta.summary`
holds: one or a few representative requests per endpoint on the fixture archives. `missing` and `stats`, which every
table has, are described once in `intro.md`. A key the list names that these requests don't send is fine (it comes
with an option); the list is checked against the code by reading it."""

import json
import re

import pytest

from api import docs
from api.tests.fixture_archive import POINT

LAT, LNG = POINT
HERE = {"lat": LAT, "lng": LNG}
EVERY_TABLE = {"missing", "stats"}
WEEK = {"start": "2025-07-05", "end": "2025-07-08"}  # inside the fixture archive
MARKER = "## In meta.summary"
DAILY = [f"2025-07-0{d}" for d in range(2, 10)]  # the days a station sends


def listed(operation: str) -> tuple[set[str], set[str]]:
    """The keys a page lists for the top-level `meta.summary`, and for each model's (indented items)."""
    found = docs.endpoint(operation)
    assert found is not None
    _, body = found
    if MARKER not in body:
        return set(), set()
    section = body.split(MARKER, 1)[1].split("\n## ", 1)[0]
    top: set[str] = set()
    nested: set[str] = set()
    for line in section.splitlines():
        item = re.match(r"(\s*)- (.*)", line)
        if item is None:
            continue
        head = item.group(2).split(": ", 1)[0]
        (nested if item.group(1) else top).update(re.findall(r"`([a-z_]+)`", head))
    return top, nested


def keys(summary: dict) -> set[str]:
    return set(summary) - EVERY_TABLE


def check(operation: str, body: dict, nested: bool = False) -> None:
    assert "errors" not in body, body.get("errors")
    top, inner = listed(operation)
    assert keys(body["meta"]["summary"]) <= top, f"{operation}.md: add {keys(body['meta']['summary']) - top}"
    if nested:
        for model, answer in body["data"].items():
            sent = keys(answer["meta"]["summary"])
            assert sent <= inner, f"{operation}.md, each model's ({model}): add {sent - inner}"


def post(client, path: str, body: dict) -> dict:
    return client.post(f"/api/v2/{path}", json.dumps(body), content_type="application/json").json()


def station(**rest) -> dict:
    daily = {"date": DAILY, "air_temperature_min": [10.0] * 8, "air_temperature_max": [20.0] * 8}
    return {"location": {"lat": LAT, "lng": LNG}, "units": "metric", "daily": daily, **rest}


GETS = [
    ("weather_daily", "weather/daily", {**HERE, "roll": "3"}),
    ("weather_hourly", "weather/hourly", HERE),
    ("weather_totals", "weather/totals", HERE),
    ("degree_days_daily", "degree-days", {**HERE, "dd": "sine_50_86", "targets": "100", "roll": "3"}),
    ("degree_days_table", "degree-days/table", {**HERE, "dd": "sine_50_86"}),
    ("degree_days_freeze", "freeze", HERE),
    ("degree_days_chill_at_points", "chill", {**HERE, "start": "2025-07-02", "end": "2025-07-08"}),
    ("models_run", "models/white-mold/run", {**HERE, **WEEK, "irrigation": "all"}),
    ("models_run", "models/tar-spot/run", {"points": f"{LAT},{LNG};{LAT},{LNG}", **WEEK}),
    ("models_risk", "risk", {**HERE, "date": "2025-07-08"}),
    ("grids_grid", "grids/air_temperature_max", {"date": "2025-07-08"}),
    (
        "grids_grid",
        "grids/degree_days",
        {"start": "2025-07-02", "end": "2025-07-08", "stat": "sum", "dd": "sine_50_86"},
    ),
    ("summaries_summary", "summaries/air_temperature_max", {"date": "2025-07-05"}),
]


@pytest.mark.parametrize(("operation", "path", "params"), GETS, ids=[f"{o}:{p}" for o, p, _ in GETS])
def test_a_responses_summary_keys_are_listed(client, archive, operation, path, params):
    check(operation, client.get(f"/api/v2/{path}", params).json())


def test_each_models_summary_keys_are_listed(client, archive):
    body = client.get("/api/v2/models/run", {**HERE, **WEEK, "models": "tar-spot,white-mold"}).json()
    check("models_run_several", body, nested=True)
    check(
        "models_run_posted",
        post(client, "models/early-blight-pdays/run", station(start=DAILY[0], end=DAILY[-1])),
    )
    several = post(client, "models/run", station(models=["early-blight-pdays", "tar-spot"]))
    check("models_run_posted_several", several, nested=True)
    evaluated = client.post(
        "/api/v2/models/early-blight-pdays/evaluate", {"inputs": {"tmin": 9.0}}, content_type="application/json"
    )
    check("models_evaluate", evaluated.json())


def test_projected_summary_keys_are_listed(client, projection_archive):
    check(
        "degree_days_daily",
        client.get("/api/v2/degree-days", {**HERE, "dd": "sine_50_86", "projection": "true"}).json(),
    )
    blight = {**HERE, "biofix": "2025-07-02", "end": "2025-08-20", "projection": "true"}
    check("models_run", client.get("/api/v2/models/early-blight-pdays/run", blight).json())


def test_climate_summary_keys_are_listed(client, climate_archive):
    metric = {**HERE, "units": "metric", "period": "last5"}
    check("climate_normals_at_points", client.get("/api/v2/climate/normals", {**metric, "roll": "3"}).json())
    check("climate_frost", client.get("/api/v2/climate/frost", metric).json())
    check("climate_frost_chances", client.get("/api/v2/climate/frost/chances", {**metric, "date": "2025-01-05"}).json())
    compare = {**metric, "start": "2025-07-01", "end": "2025-07-31", "dd": "modified_10_30"}
    check("climate_compare", client.get("/api/v2/climate/compare", compare).json())


def test_the_list_parser_reads_nested_items():
    top, nested = listed("models_run_several")
    assert "corrections" in top and "estimated_by_input" in nested and "estimated_by_input" not in top
