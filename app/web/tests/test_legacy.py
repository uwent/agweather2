"""v1's and VDIFN's URLs (D62, `web.legacy`): a test per row of the map in docs/frontend.md's "Legacy URLs", then the
catch-all route over the real URL configuration."""

import pytest
from django.test import Client, override_settings

from agmodels.registry import all_models
from web.content import topics
from web.legacy import VDIFN_RENAMED, VDIFN_SAME, legacy_target, retired_page

LEGACY = "https://legacy.agweather.cals.wisc.edu"


def to(path: str, query: str = "") -> str:
    found = legacy_target(path, query)
    assert found is not None
    url, status = found
    assert status in (302, 308)
    return url


# Navigation


def test_home():
    assert to("/home") == "/"


def test_king_hall():
    assert to("/king-hall") == "/about"


def test_ag_weather_is_the_api_docs():
    assert to("/ag_weather") == "/api/v2/docs"


# /weather


def test_weather_index_and_awon_go_to_the_map():
    assert to("/weather") == "/map"
    assert to("/weather/awon") == "/map"
    assert to("/weather/no-such-page") == "/map"


def test_weather_data_a_day():
    assert to("/weather/data", "stat=min&date=2024-05-01&units=C") == (
        "/map?layer=air_temperature_min&span=day&date=2024-05-01"
    )
    assert to("/weather/data") == "/map?layer=air_temperature_mean&span=day"
    assert to("/weather/data", "stat=avg&date=yesterday") == "/map?layer=air_temperature_mean&span=day"


def test_weather_data_cumulative_is_a_range_of_the_same_stat():
    # v1 summarized the stat's own column over the range: the lowest daily minimum, the mean of daily means
    assert to("/weather/data", "cumulative=true&stat=max&start_date=2024-04-01&end_date=2024-06-30") == (
        "/map?layer=air_temperature_max&span=range&start=2024-04-01&date=2024-06-30&stat=max"
    )
    assert to("/weather/data", "cumulative=true&end_date=2024-06-30") == (
        "/map?layer=air_temperature_mean&span=range&start=2024-01-01&date=2024-06-30&stat=mean"
    )


def test_weather_precip():
    assert to("/weather/precip", "date=2024-05-01") == "/map?layer=precipitation_sum&span=day&date=2024-05-01"
    assert to("/weather/precip", "cumulative=1&start_date=2024-05-01&end_date=2024-05-31") == (
        "/map?layer=precipitation_sum&span=range&start=2024-05-01&date=2024-05-31&stat=sum"
    )
    # v1's default start, January 1, is the season's
    assert to("/weather/precip", "cumulative=1&end_date=2024-05-31&stat=avg") == (
        "/map?layer=precipitation_sum&span=season&date=2024-05-31&stat=mean"
    )


def test_weather_et():
    assert to("/weather/et", "date=2024-07-04&et_method=adjusted") == "/map?layer=et0_sum&span=day&date=2024-07-04"


def test_weather_insol():
    assert to("/weather/insol", "units=KWh") == "/map?layer=shortwave_radiation_sum&span=day"


def test_weather_doycal_is_the_calendar():
    assert to("/weather/doycal", "year=2024") == "/calendar?year=2024"
    assert to("/weather/doycal-grid", "year=2023") == "/calendar?year=2023"
    assert to("/weather/doycal-grid") == "/calendar"
    assert to("/weather/doycal", "year=next") == "/calendar"


def test_weather_hyd_is_the_downloads():
    assert to("/weather/hyd") == "/data"
    assert to("/weather/hyd-grid") == "/data"


def test_weather_fragments_images_and_csv_go_to_the_legacy_host():
    assert legacy_target("/weather/precip.csv", "date=2024-05-01") == (
        f"{LEGACY}/weather/precip.csv?date=2024-05-01",
        302,
    )
    assert to("/weather/et", "format=csv&date=2024-05-01") == f"{LEGACY}/weather/et?format=csv&date=2024-05-01"
    for action in ("map-image", "weather-data", "precip-data", "et-data", "insol-data"):
        assert to(f"/weather/{action}", "date=2024-05-01") == f"{LEGACY}/weather/{action}?date=2024-05-01"


# /sites


def test_site_data_fragments_go_to_the_site():
    assert to("/sites/site-data-weather", "lat=43.1&lng=-89.4") == "/sites/43.1,-89.4"
    assert to("/sites/site-data-dd", "lat=45.00&lng=-90") == "/sites/45,-90"
    assert to("/sites/site-data-dd", "lat=north") == "/sites"


def test_other_sites_paths_go_to_the_list():
    assert to("/sites/17") == "/sites"
    assert to("/sites/17/edit") == "/sites"
    assert to("/sites/91,-89") == "/sites"


def test_v2s_own_forms_under_sites_are_not_legacy():
    assert legacy_target("/sites/models", "") is None
    assert legacy_target("/sites/madison/models/late-blight-dsv", "") is None


def test_a_site_with_a_plus_sign():
    assert to("/sites/+43.1,-89.4") == "/sites/43.1,-89.4"


# /thermal-models


def test_thermal_models_index():
    assert to("/thermal-models") == "/models"
    assert to("/thermal-models/") == "/models"


def test_degree_days_and_get_dds():
    assert to("/thermal-models/degree-days") == "/tools/degree-days"
    assert to("/thermal-models/get-dds", "lat=43&lng=-89&base_temp=50") == "/tools/degree-days?at=43,-89"
    assert to("/thermal-models/get-dds", "lat=43.07305&lng=-89.40123") == "/tools/degree-days?at=43.0731,-89.4012"
    assert to("/thermal-models/get-dds", "lat=91&lng=-89") == "/tools/degree-days"


def test_get_dds_as_csv_or_json_goes_to_the_legacy_host():
    assert to("/thermal-models/get-dds.json", "lat=43") == f"{LEGACY}/thermal-models/get-dds.json?lat=43"
    assert to("/thermal-models/get-dds", "format=csv") == f"{LEGACY}/thermal-models/get-dds?format=csv"


def test_dd_map_degree_days():
    assert to("/thermal-models/dd-map") == "/map?layer=degree_days&dd=sine_50_86&span=season"
    assert to("/thermal-models/dd-map", "map_type=dd&dd_model=dd_39p2_86&end_date=2024-06-30") == (
        "/map?layer=degree_days&dd=sine_39p2_86&span=season&date=2024-06-30"
    )
    assert to("/thermal-models/dd-map", "dd_model=dd_41&start_date=2024-01-01&end_date=2024-06-30") == (
        "/map?layer=degree_days&dd=sine_41&span=season&date=2024-06-30"
    )
    assert to("/thermal-models/dd-map", "dd_model=dd_32&start_date=2024-03-15&end_date=2024-06-30") == (
        "/map?layer=degree_days&dd=sine_32&span=range&start=2024-03-15&date=2024-06-30"
    )
    assert to("/thermal-models/dd-map", "dd_model=nonsense") == "/map?layer=degree_days&dd=sine_50_86&span=season"


@pytest.mark.parametrize(
    ("dsv_model", "layer"),
    [
        ("potato_blight_dsv", "late-blight-dsv"),
        ("potato_p_days", "early-blight-pdays"),
        ("carrot_foliar_dsv", "carrot-foliar-dsv"),
        ("cercospora_div", "cercospora-beet-div"),
        ("botcast_dsi", "botrytis-onion-botcast"),
        ("unknown", "late-blight-dsv"),  # v1's default
    ],
)
def test_dd_map_disease(dsv_model: str, layer: str):
    assert to("/thermal-models/dd-map", f"map_type=dsv&dsv_model={dsv_model}") == f"/map?layer={layer}"
    assert to("/thermal-models/dd-map", f"map_type=dsv&dsv_model={dsv_model}&end_date=2024-07-01") == (
        f"/map?layer={layer}&date=2024-07-01"
    )


def test_frost_map_is_the_freeze_tool():
    assert to("/thermal-models/frost-map") == "/tools/freeze"
    assert to("/thermal-models/frost-map", "lat=44.5&lng=-89.5") == "/tools/freeze?at=44.5,-89.5"


def test_oak_wilt():
    assert to("/thermal-models/oak-wilt") == "/tools/oak-wilt"
    assert to("/thermal-models/oak-wilt-dd", "lat=43&lng=-89") == "/tools/oak-wilt?at=43,-89"
    assert to("/thermal-models/oak-wilt-dd", "lat=43") == "/tools/oak-wilt"


@pytest.mark.parametrize(
    ("page", "topic"),
    [
        ("alfalfa-weevil", "alfalfa-weevil"),
        ("corn-stalk-borer", "stalk-borer"),
        ("ecb", "european-corn-borer"),
        ("scm", "seedcorn-maggot"),
        ("western-bean-cutworm", "western-bean-cutworm"),
        ("corn-dev", "corn"),
        ("potato", "potato"),
        ("potato-data", "potato"),
    ],
)
def test_pest_and_crop_pages_are_topics(page: str, topic: str):
    assert to(f"/thermal-models/{page}") == f"/topics/{topic}"


def test_spongy_moth_is_the_models_index():
    assert to("/thermal-models/spongy-moth") == "/models"


def test_thermal_models_machine_endpoints_go_to_the_legacy_host():
    assert legacy_target("/thermal-models/map-image", "", method="POST") == (f"{LEGACY}/thermal-models/map-image", 307)
    assert legacy_target("/thermal-models/download-csv", "", method="POST") == (
        f"{LEGACY}/thermal-models/download-csv",
        307,
    )


# /subscribers and the old API


def test_subscribers_go_to_the_legacy_host():
    assert to("/subscribers") == f"{LEGACY}/subscribers"
    assert to("/subscribers/manage") == f"{LEGACY}/subscribers/manage"
    assert to("/subscribers/12/confirm", "token=abc") == f"{LEGACY}/subscribers/12/confirm?token=abc"
    assert to("/subscribers/12/unsubscribe") == f"{LEGACY}/subscribers/12/unsubscribe"


def test_the_old_api_goes_to_the_legacy_host_keeping_the_method():
    assert legacy_target("/api/weather", "date=2024-05-01") == (f"{LEGACY}/api/weather?date=2024-05-01", 308)
    assert legacy_target("/api/degree_days", "", method="POST") == (f"{LEGACY}/api/degree_days", 308)


def test_bare_api_is_the_v2_docs():
    assert to("/api") == "/api/v2/docs"
    assert to("/api/") == "/api/v2/docs"


def test_api_v2_is_not_legacy():
    assert legacy_target("/api/v2", "") is None
    assert legacy_target("/api/v2/weather", "") is None


# /vdifn


@pytest.mark.parametrize(
    ("model", "layer"),
    [
        ("early-blight", "early-blight-pdays"),
        ("late-blight", "late-blight-dsv"),
        ("carrot-foliar", "carrot-foliar-dsv"),
        ("cercospora-leaf-spot", "cercospora-beet-div"),
        ("botrytis-leaf-blight", "botrytis-onion-botcast"),
        ("pvy-vectors", "aphid-pvy-vectors"),
        ("oak-wilt", "oak-wilt-vectors"),
        ("cpb", "colorado-potato-beetle"),
        ("cpb-old", "colorado-potato-beetle"),
    ],
)
def test_vdifn_renamed_models(model: str, layer: str):
    assert to("/vdifn", f"p=insect&m={model}") == f"/map?layer={layer}"


@pytest.mark.parametrize(
    "model",
    [
        "alfalfa-weevil",
        "black-cutworm",
        "cabbage-looper",
        "cabbage-maggot",
        "common-asparagus-beetle",
        "corn-earworm",
        "corn-rootworm",
        "crucifer-flea-beetle",
        "european-corn-borer",
        "imported-cabbageworm",
        "japanese-beetle",
        "mint-flea-beetle",
        "mint-root-borer",
        "onion-maggot",
        "seedcorn-maggot",
        "spotted-wing-drosophila",
        "squash-vine-borer",
        "stalk-borer",
        "variegated-cutworm",
        "western-bean-cutworm",
    ],
)
def test_vdifn_models_with_the_same_id(model: str):
    assert to("/vdifn", f"type=insect&model={model}") == f"/map?layer={model}"


@pytest.mark.parametrize(
    ("model", "topic"),
    [
        ("tarnished-plant-bug", "tarnished-plant-bug"),
        ("western-flower-thrips", "western-flower-thrips"),
        ("cpbad", "colorado-potato-beetle"),
        ("cpbl", "colorado-potato-beetle"),
    ],
)
def test_vdifn_retired_models_go_to_their_topics(model: str, topic: str):
    assert to("/vdifn", f"panel=insect&model={model}") == f"/topics/{topic}"


def test_every_retired_model_vdifn_linked_goes_to_a_topic_that_exists():
    # One rule by the spec's status, not a list: every VDIFN model whose v2 model is retired lands on a topic page
    linked = {VDIFN_RENAMED.get(m, m) for m in [*VDIFN_RENAMED, *VDIFN_SAME]}
    retired = {i for i, m in all_models().items() if m.SPEC.status == "retired"}
    assert retired & linked
    for model_id in retired & linked:
        page = retired_page(model_id)
        assert page is not None and page.startswith("/topics/"), model_id
        assert page.removeprefix("/topics/") in topics(), model_id
    assert retired_page("colorado-potato-beetle") is None and retired_page("no-such-model") is None


def test_vdifn_query_keys_and_defaults():
    # The panel from type, panel or p (disease by default), the model from model or m, as VDIFN read them
    assert to("/vdifn", "model=late-blight") == "/map?layer=late-blight-dsv"
    assert to("/vdifn/", "panel=disease&m=early-blight") == "/map?layer=early-blight-pdays"
    assert to("/vdifn") == "/map"
    assert to("/vdifn", "p=insect") == "/map"
    assert to("/vdifn", "p=insect&m=bmsb") == "/map"  # commented out of VDIFN's seeds
    assert to("/vdifn", "p=weather&m=late-blight") == "/map"  # VDIFN dropped an unknown panel's query


def test_vdifn_custom_panel_is_degree_days():
    assert to("/vdifn", "type=custom") == "/map?layer=degree_days&dd=sine_50_86&span=season"
    # VDIFN's degree-day panel ignored the model; one of its DegreeDay.remote_names is carried over anyway
    assert to("/vdifn", "p=custom&m=dd_45_80p1") == "/map?layer=degree_days&dd=sine_45_80p1&span=season"
    assert to("/vdifn", "p=custom&m=late-blight") == "/map?layer=degree_days&dd=sine_50_86&span=season"


def test_vdifn_endpoints_go_to_the_legacy_host():
    assert (
        to("/vdifn/point_details", "lat=43&lng=-89&pest=dd_50")
        == f"{LEGACY}/vdifn/point_details?lat=43&lng=-89&pest=dd_50"
    )
    assert to("/vdifn/severities", "pest=potato_blight_dsv") == f"{LEGACY}/vdifn/severities?pest=potato_blight_dsv"
    assert to("/vdifn/db/insect_panel") == f"{LEGACY}/vdifn/db/insect_panel"


# Status codes


def test_permanent_after_the_first_weeks():
    assert legacy_target("/thermal-models", "", permanent=True) == ("/models", 301)
    # The legacy host goes away after a year, so redirects there stay temporary
    assert legacy_target("/subscribers", "", permanent=True) == (f"{LEGACY}/subscribers", 302)


def test_the_legacy_host_is_a_setting():
    assert legacy_target("/subscribers", "a=1", legacy_host="https://old.example.edu/") == (
        "https://old.example.edu/subscribers?a=1",
        302,
    )


def test_not_a_legacy_path():
    assert legacy_target("/", "") is None
    assert legacy_target("/somewhere", "") is None


# The catch-all route


@pytest.mark.parametrize(
    ("path", "location"),
    [
        ("/weather/precip?date=2024-05-01", "/map?layer=precipitation_sum&span=day&date=2024-05-01"),
        ("/thermal-models/", "/models"),
        ("/vdifn?p=insect&m=cpb", "/map?layer=colorado-potato-beetle"),
        ("/vdifn/severities?pest=x", f"{LEGACY}/vdifn/severities?pest=x"),
        ("/home", "/"),
        ("/king-hall", "/about"),
        ("/ag_weather", "/api/v2/docs"),
        ("/api", "/api/v2/docs"),
        ("/api/weather?date=2024-05-01", f"{LEGACY}/api/weather?date=2024-05-01"),
        ("/sites/site-data-dd?lat=43.1&lng=-89.4", "/sites/43.1,-89.4"),
        ("/subscribers/manage", f"{LEGACY}/subscribers/manage"),
    ],
)
def test_the_route_redirects(client: Client, path: str, location: str):
    response = client.get(path)
    assert response.status_code in (302, 308)
    assert response["Location"] == location


def test_a_post_from_v1s_forms_is_redirected_without_a_csrf_token(client: Client):
    client = Client(enforce_csrf_checks=True)
    response = client.post("/thermal-models/download-csv", {"lat": "43"})
    assert (response.status_code, response["Location"]) == (307, f"{LEGACY}/thermal-models/download-csv")


@override_settings(LEGACY_REDIRECT_PERMANENT=True, LEGACY_HOST="https://old.example.edu")
def test_the_route_reads_the_settings(client: Client):
    assert client.get("/thermal-models/ecb")["Location"] == "/topics/european-corn-borer"
    assert client.get("/thermal-models/ecb").status_code == 301
    assert client.get("/subscribers")["Location"] == "https://old.example.edu/subscribers"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/sites", "/sites/43.1,-89.4", "/api/v2/docs", "/about"])
def test_v2s_own_routes_come_first(client: Client, path: str):
    assert client.get(path).status_code == 200


def test_api_v2_without_its_slash_is_not_sent_to_the_legacy_host(client: Client):
    response = client.get("/api/v2")
    assert response.status_code == 301  # Django's APPEND_SLASH, to the API's root
    assert response["Location"] == "/api/v2/"
