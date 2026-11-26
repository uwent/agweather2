"""The shared `status` prop (web.status), the home page's content (web.home) and the sites page."""

import json
import re
from datetime import UTC, date, datetime, timedelta

import pytest

from agdata.layers import LAYERS
from agmodels import seasons
from agmodels.registry import all_models
from ops.models import DatasetStatus
from web import home, status
from web.catalog import crop_entries, model_entries

NOW = datetime(2026, 11, 25, 21, 30, tzinfo=UTC)
INERTIA = {"X-Inertia": "true", "X-Inertia-Version": "dev"}


def page_props(client, url: str) -> dict:
    return client.get(url, headers=INERTIA).json()["props"]


def rows(*, observed: datetime, cycle: datetime | None, by_source: dict[str, datetime] | None = None) -> None:
    for dataset, values in {
        "hourly": {
            "first": datetime(2016, 1, 1, tzinfo=UTC),
            "last": observed,
            "last_by_source": {k: v.isoformat() for k, v in (by_source or {}).items()},
        },
        "daily": {"first": datetime(2016, 1, 1, tzinfo=UTC), "last": datetime(2026, 11, 24, tzinfo=UTC)},
        "cumulative": {"first": None, "last": None},
        "forecast": {"first": cycle, "last": cycle + timedelta(days=11) if cycle else None},
    }.items():
        DatasetStatus.objects.update_or_create(dataset=dataset, defaults={**values, "refreshed_at": NOW})


@pytest.mark.django_db
def test_status_is_none_until_the_rows_exist(client):
    assert status.read_status(NOW) is None
    assert page_props(client, "/")["status"] is None


@pytest.mark.django_db
def test_status_when_current():
    rows(
        observed=NOW - timedelta(hours=2),
        cycle=NOW - timedelta(hours=3),
        by_source={"rtma": NOW - timedelta(hours=2), "urma": NOW - timedelta(hours=7)},
    )
    found = status.read_status(NOW)
    assert found is not None
    assert found.behind == [] and found.stale_sources == []
    assert found.observed_through == NOW - timedelta(hours=2)
    assert found.daily_through == date(2026, 11, 24)
    assert found.forecast_fallback is None


@pytest.mark.django_db
def test_status_names_what_is_behind(settings):
    settings.OPEN_METEO_FALLBACK = True
    rows(
        observed=NOW - timedelta(hours=9),
        cycle=NOW - timedelta(hours=20),
        by_source={"rtma": NOW - timedelta(hours=9), "urma": NOW - timedelta(hours=10)},
    )
    found = status.read_status(NOW)
    assert found is not None
    assert found.behind == ["observed", "forecast"]
    assert found.stale_sources == ["rtma"]
    assert found.forecast_fallback == "openmeteo"


@pytest.mark.django_db
def test_status_reaches_every_page_and_is_kept_a_while(client, monkeypatch):
    rows(observed=datetime.now(UTC) - timedelta(hours=1), cycle=datetime.now(UTC) - timedelta(hours=1))
    shared = page_props(client, "/sites")["status"]
    assert shared["behind"] == [] and shared["observed_through"].endswith("Z")
    # Kept for TTL seconds: a change to the rows shows only after it
    monkeypatch.setattr(status, "TTL", 60.0)
    status.clear()
    first = status.data_status()
    DatasetStatus.objects.filter(dataset="hourly").update(last=None)
    assert status.data_status() == first
    status.clear()
    assert status.data_status().behind == ["observed"]  # pyright: ignore[reportOptionalMemberAccess]
    status.clear()


def test_headline_maps_name_real_layers_for_every_month():
    for month in range(1, 13):
        maps = home.headline_maps(date(2026, month, 15))
        assert len(maps) == 3 and len({m.layer for m in maps}) == 3, month
        for m in maps:
            assert m.layer in LAYERS, f"{m.layer} isn't a layer (agdata.layers)"
            assert m.image_url.startswith(f"/api/v2/maps/{m.layer}.png?") and "width=640" in m.image_url
            assert m.map_url == f"/map?layer={m.layer}"
            assert m.alt.endswith(".") and m.title


def test_a_risk_headline_is_in_season_in_its_month():
    for month in range(1, 13):
        day = date(2026, month, 15)
        for m in home.headline_maps(day):
            if m.layer in all_models():
                spec = all_models()[m.layer].SPEC
                assert seasons.in_season(spec, day), f"{m.layer} in month {month}"


def test_models_in_season_by_crop():
    november = home.models_in_season(date(2026, 11, 25))
    # Alfalfa growth to November 30, rye biomass, potato volunteer; the insects wait for April
    assert [c.crop for c in november] == ["alfalfa", "rye", "potato"]
    july = {c.crop: [m.id for m in c.models] for c in home.models_in_season(date(2026, 7, 15))}
    assert "tar-spot" in july["corn"] and "late-blight-dsv" in july["potato"] and "late-blight-dsv" in july["tomato"]
    assert not any("cotton" in ids for ids in july.values()) and "cotton" not in july  # outside the coverage
    assert all(ids == sorted(ids, key=lambda i: all_models()[i].SPEC.name.lower()) for ids in july.values())
    assert not any("colorado-potato-beetle-adults" in ids for ids in july.values())  # retired


def test_an_insect_is_in_season_on_the_home_page_once_open_over_the_region(monkeypatch):
    """D128: the region's day (the 10th percentile over cultivated land) opens it; without normals, the calendar's."""
    from agdata import seasonopens

    def corn(day):
        return {m.id for c in home.models_in_season(day) if c.crop == "corn" for m in c.models}

    assert "corn-rootworm" in corn(date(2026, 5, 20))  # the calendar's May 15: the tests have no normals
    monkeypatch.setattr(
        seasonopens, "region", lambda data_dir, spec: "05-25" if spec.id == "corn-rootworm" else spec.season[0]
    )
    assert "corn-rootworm" not in corn(date(2026, 5, 20)) and "corn-rootworm" in corn(date(2026, 5, 25))


@pytest.mark.django_db
def test_home_page_props(client):
    props = page_props(client, "/")
    assert len(props["maps"]) == 3
    assert props["in_season"] and props["api_docs_url"] == "/api/v2/docs"


@pytest.mark.django_db
def test_sites_page(client):
    response = client.get("/sites")
    assert response.status_code == 200
    found = re.search(r'data-page="app" type="application/json">(.*?)</script>', response.content.decode(), re.S)
    assert found
    data = json.loads(found.group(1))
    assert data["component"] == "Sites/Index"
    models = {m["id"]: m for m in data["props"]["models"]}
    assert models["late-blight-dsv"]["risk_levels"] == ["Very low", "Low", "Moderate", "High", "Very high"]
    assert models["corn-stages"]["risk_levels"] == []
    assert "custom-degree-days" not in models
    assert data["props"]["crops"][0] == {"id": "corn", "name": "Corn", "category": "Field crops"}


def test_catalog_lists_retired_models_only_when_asked():
    assert "tarnished-plant-bug" not in {m.id for m in model_entries()}
    assert "tarnished-plant-bug" in {m.id for m in model_entries(retired=True)}
    assert {c.id for c in crop_entries()} >= {"corn", "potato", "apple", "oak"}


@pytest.mark.django_db
def test_the_status_page_shows_the_apis_answer_with_each_sources_usual_delay_and_recent_outages(client, archive):
    from updates.models import ChangelogEntry

    today = datetime.now(UTC).date()
    ChangelogEntry.objects.create(title="Late hours", kind="outage", published=True, date=today - timedelta(days=3))
    ChangelogEntry.objects.create(title="Long ago", kind="outage", published=True, date=today - timedelta(days=200))
    ChangelogEntry.objects.create(title="Not an outage", kind="data", published=True, date=today)
    response = client.get("/status", headers=INERTIA).json()
    assert response["component"] == "Status/Show"
    props = response["props"]
    assert props["report"] == client.get("/api/v2/status").json()["data"]
    sources = {s["id"]: s for s in props["sources"]}
    assert list(sources) == ["urma", "rtma", "hrrr", "era5land", "ifs"]
    assert sources["urma"]["normal_lag_hours"] == 14 and sources["era5land"]["normal_lag_hours"] == 168
    assert sources["hrrr"]["name"].startswith("HRRR (High-Resolution Rapid Refresh)")
    assert [e["title"] for e in props["outages"]] == ["Late hours"]
    assert props["refresh_seconds"] == 60
