"""Redirects from v1's site and VDIFN's URLs to v2's pages (D62, Phase 7 track 7.5), so bookmarks, search results and
links in UW's pages and newsletters land somewhere useful.

`legacy_target` is the whole map, pure and tested a row at a time (`tests/test_legacy.py`); the catch-all view in
`web.views.legacy` calls it for paths under v1's and VDIFN's prefixes that no v2 route took. Human pages go to their
v2 page, or the nearest one where there's none (HYD → `/data`, AWON → `/map`, spongy moth → `/models`, Ben,
2026-11-26); machine endpoints (page fragments, CSV and JSON, map images, VDIFN's JSON) and the subscriber pages go to
v1 on the legacy host (`settings.LEGACY_HOST`) with their path and query, for the year it stays up. Caddy sends
`/api/*` outside `/api/v2` there itself (308, `infra/Caddyfile`); the same rule is here so development and tests agree.

Status codes: redirects to v2 pages are 302 for the first four weeks after launch, then 301
(`LEGACY_REDIRECT_PERMANENT`, Ben 2026-11-26). Redirects to the legacy host stay temporary (302, or 307 for a POST),
since that host goes away after a year and a browser would otherwise keep sending people there; the old API's are
308 (D62). The map and its sources are in `docs/frontend.md`'s "Legacy URLs".
"""

import re
from collections.abc import Callable
from datetime import date
from urllib.parse import parse_qs, urlencode

from agmodels.registry import all_models

# The paths the catch-all route takes (config/urls.py), all after v2's own routes: v1's controllers, VDIFN, v1's
# `/ag_weather`, the old API, and `/sites/…` paths that aren't v2's site pages
PREFIXES = (
    r"(?:weather|thermal-models|subscribers|vdifn|home|king-hall|ag_weather)(?:/.*)?|api(?:/(?!v2(?:/|$)).*)?|sites/.+"
)

DEFAULT_LEGACY_HOST = "https://legacy.agweather.cals.wisc.edu"

# A redirect (its URL and status), and the helpers `legacy_target` hands its parts: `here(path, **query)` for a v2
# page, `legacy()` for the same URL on the legacy host
Redirect = tuple[str, int]
Here = Callable[..., Redirect]
Legacy = Callable[[], Redirect]

# v1's /weather/{data,precip,et,insol} map pages: the layer, and v1's `stat` values to the explorer's
WEATHER_LAYERS = {
    "precip": "precipitation_sum",
    "et": "et0_sum",
    "insol": "shortwave_radiation_sum",
}
STATS = {"avg": "mean", "sum": "sum", "min": "min", "max": "max"}

# v1's pest and crop pages under /thermal-models to v2's topics
TOPICS = {
    "alfalfa-weevil": "alfalfa-weevil",
    "corn-stalk-borer": "stalk-borer",
    "ecb": "european-corn-borer",
    "scm": "seedcorn-maggot",
    "western-bean-cutworm": "western-bean-cutworm",
    "corn-dev": "corn",
    "potato": "potato",
    "potato-data": "potato",
}

# v1's disease map (`/thermal-models/dd-map?map_type=dsv&dsv_model=`) to v2's model layers
DSV_MODELS = {
    "potato_blight_dsv": "late-blight-dsv",
    "potato_p_days": "early-blight-pdays",
    "carrot_foliar_dsv": "carrot-foliar-dsv",
    "cercospora_div": "cercospora-beet-div",
    "botcast_dsi": "botrytis-onion-botcast",
}

# VDIFN's models (`local_name` in ../agweather-v1/vdifn/db/seeds.rb) to v2's layers, where the id changed
VDIFN_RENAMED = {
    "early-blight": "early-blight-pdays",
    "late-blight": "late-blight-dsv",
    "carrot-foliar": "carrot-foliar-dsv",
    "cercospora-leaf-spot": "cercospora-beet-div",
    "botrytis-leaf-blight": "botrytis-onion-botcast",
    "pvy-vectors": "aphid-pvy-vectors",
    "oak-wilt": "oak-wilt-vectors",
    "cpb": "colorado-potato-beetle",
    "cpb-old": "colorado-potato-beetle",
    "cpbad": "colorado-potato-beetle-adults",
    "cpbl": "colorado-potato-beetle-larvae",
}
# VDIFN's models whose id is v2's layer's too
VDIFN_SAME = frozenset(
    {
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
        "tarnished-plant-bug",
        "variegated-cutworm",
        "western-bean-cutworm",
        "western-flower-thrips",
    }
)
VDIFN_PANELS = frozenset({"disease", "insect", "custom"})

# v1's and VDIFN's degree-day models: `dd_50_86`, `dd_39p2_86`, `dd_41` (°F, single sine in v1's API)
DD_MODEL = re.compile(r"^dd_(\d+(?:p\d+)?)(?:_(\d+(?:p\d+)?))?$")
# A latitude or longitude as v1 wrote it in /sites/{lat},{lng} and `?lat=&lng=`
NUMBER = re.compile(r"^[-+]?\d+(?:\.\d*)?$")


def legacy_target(
    path: str,
    query: str = "",
    *,
    method: str = "GET",
    permanent: bool = False,
    legacy_host: str = DEFAULT_LEGACY_HOST,
) -> Redirect | None:
    """Where a v1 or VDIFN URL goes in v2, and the redirect's status; None where there's no such URL (a 404).

    `path` is the request's path and `query` its query string as sent. `permanent` makes redirects to v2's pages 301
    rather than 302; `method` keeps a POST to the legacy host a POST (307 or 308)."""
    params = {key: values[0] for key, values in parse_qs(query, keep_blank_values=True).items()}
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    head, rest = parts[0], parts[1:]
    page = 301 if permanent else 302

    def here(target: str, **query_params: str | None) -> Redirect:
        kept = {k: v for k, v in query_params.items() if v is not None}
        return (f"{target}?{urlencode(kept, safe=':,')}" if kept else target), page

    def legacy(status: int | None = None) -> Redirect:
        url = legacy_host.rstrip("/") + path + (f"?{query}" if query else "")
        if status is None:
            status = 302 if method in ("GET", "HEAD") else 307
        return url, status

    if head == "api":
        if not rest:
            return here("/api/v2/docs")
        if rest[0] == "v2":
            return None  # v2's own (config/urls.py answers it before the catch-all)
        return legacy(308)
    if head == "ag_weather":
        return here("/api/v2/docs")
    if head == "home":
        return here("/")
    if head == "king-hall":
        return here("/about")
    if head == "subscribers":
        return legacy()  # until accounts (track 8); then the bare path goes to /account
    if head == "vdifn":
        return legacy() if rest else _vdifn(params, here)
    if _machine(path, params):
        return legacy()
    if head == "weather":
        return _weather(rest, params, here, legacy)
    if head == "thermal-models":
        return _thermal_models(rest, params, here, legacy)
    if head == "sites":
        return _sites(rest, params, here)
    return None


def _machine(path: str, params: dict[str, str]) -> bool:
    """A CSV, JSON, script or image answer (by its extension or Rails' `format=`), which only v1 can give."""
    return bool(re.search(r"\.(csv|json|js|png)$", path)) or params.get("format") in ("csv", "json", "js")


def _weather(rest: list[str], params: dict[str, str], here: Here, legacy: Legacy) -> Redirect:
    action = rest[0] if rest else ""
    if action in ("map-image", "weather-data", "precip-data", "et-data", "insol-data"):
        return legacy()
    if action in ("doycal", "doycal-grid"):
        year = params.get("year", "")
        return here("/calendar", year=year if re.fullmatch(r"\d{4}", year) else None)
    if action in ("hyd", "hyd-grid"):
        return here("/data")  # HYD isn't in v2: the downloads are nearest
    if action == "data":
        stat = STATS.get(params.get("stat", ""), "mean")
        if stat == "sum":
            stat = "mean"
        return _weather_map(f"air_temperature_{stat}", stat, params, here, summable=False)
    if action in WEATHER_LAYERS:
        stat = STATS.get(params.get("stat", ""), "sum")
        return _weather_map(WEATHER_LAYERS[action], stat, params, here, summable=True)
    return here("/map")  # /weather, AWON (gone) and anything else


def _weather_map(layer: str, stat: str, params: dict[str, str], here: Here, *, summable: bool) -> Redirect:
    """A v1 weather map: a day (`date=`), or with `cumulative` a range from `start_date` to `end_date` (v1's default
    start, January 1, is v2's season for layers that sum)."""
    if "cumulative" not in params:
        return here("/map", layer=layer, span="day", date=_date(params.get("date")))
    end = _date(params.get("end_date"))
    start = _date(params.get("start_date"))
    if end and start and start > end:
        start = None
    if start is None and summable:
        return here("/map", layer=layer, span="season", date=end, stat=stat)
    if start is None and end:
        start = f"{end[:4]}-01-01"
    return here("/map", layer=layer, span="range", start=start, date=end, stat=stat)


def _thermal_models(rest: list[str], params: dict[str, str], here: Here, legacy: Legacy) -> Redirect:
    action = rest[0] if rest else ""
    if action in ("map-image", "download-csv"):
        return legacy()
    # The tools open on v1's point (`lat`, `lng`) as their `at`, where v1's link gave one
    point = _point(params.get("lat", ""), params.get("lng", ""))
    at = f"{point[0]},{point[1]}" if point else None
    if action in ("degree-days", "get-dds"):
        return here("/tools/degree-days", at=at)
    if action == "dd-map":
        return _dd_map(params, here)
    if action == "frost-map":
        return here("/tools/freeze")
    if action in ("oak-wilt", "oak-wilt-dd"):
        return here("/tools/oak-wilt", at=at)
    if action in TOPICS:
        return here(f"/topics/{TOPICS[action]}")
    return here("/models")  # the index, spongy moth (no model or topic in v2) and anything else


def _dd_map(params: dict[str, str], here: Here) -> Redirect:
    """v1's degree-day and disease map: `map_type=dd` (the default) with `dd_model`, or `map_type=dsv` with
    `dsv_model`, from `start_date` (January 1 by default) to `end_date`."""
    end = _date(params.get("end_date"))
    if params.get("map_type") == "dsv":
        layer = DSV_MODELS.get(params.get("dsv_model", ""), DSV_MODELS["potato_blight_dsv"])
        return here("/map", layer=layer, date=end)
    dd = _dd_setting(params.get("dd_model", "")) or "sine_50_86"
    start = _date(params.get("start_date"))
    if start and (start > (end or "9999") or (end and start == f"{end[:4]}-01-01")):
        start = None
    if start:
        return here("/map", layer="degree_days", dd=dd, span="range", start=start, date=end)
    return here("/map", layer="degree_days", dd=dd, span="season", date=end)


def _vdifn(params: dict[str, str], here: Here) -> Redirect:
    """VDIFN's page (`/vdifn`), reading its query as VDIFN did: the panel from `type`, `panel` or `p` (disease by
    default), the model from `model` or `m`."""
    panel = params.get("type") or params.get("panel") or params.get("p") or "disease"
    if panel not in VDIFN_PANELS:
        return here("/map")
    model = params.get("model") or params.get("m") or ""
    if panel == "custom":
        # VDIFN's degree-day panel ignored `model`; one of its `DegreeDay.remote_name`s (`dd_50_86`) is kept
        return here("/map", layer="degree_days", dd=_dd_setting(model) or "sine_50_86", span="season")
    layer = VDIFN_RENAMED.get(model) or (model if model in VDIFN_SAME else None)
    if layer is None:
        return here("/map")
    retired = retired_page(layer)
    return here(retired) if retired else here("/map", layer=layer)


def retired_page(model_id: str) -> str | None:
    """Where a retired model's old links go, since it has no map layer or page in v2: its topic page (the first
    topic its spec names), or the models' index without one; None for a model still in service."""
    found = all_models().get(model_id)
    if found is None or found.SPEC.status != "retired":
        return None
    return f"/topics/{found.SPEC.topics[0]}" if found.SPEC.topics else "/models"


def _sites(rest: list[str], params: dict[str, str], here: Here) -> Redirect | None:
    """`/sites/…` paths v2's routes didn't take: v1's site data fragments (`?lat=&lng=`) go to the site's page, a
    `/sites/{lat},{lng}` written with a plus sign or a trailing slash to its plain form, anything else to the sites
    list, as v1 sent it. Paths in v2's own forms under `/sites/` (a `models` part, which v1 never had) stay not found."""
    if "models" in rest:
        return None
    if not rest:
        point = None
    elif rest[0] in ("site-data-weather", "site-data-dd"):
        point = _point(params.get("lat", ""), params.get("lng", ""))
    elif len(rest) == 1 and rest[0].count(",") == 1:
        point = _point(*rest[0].split(","))
    else:
        point = None
    return here(f"/sites/{point[0]},{point[1]}") if point else here("/sites")


def _point(lat: str, lng: str) -> tuple[str, str] | None:
    if not (NUMBER.match(lat) and NUMBER.match(lng)):
        return None
    latitude, longitude = float(lat), float(lng)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return _number(latitude), _number(longitude)


def _number(value: float) -> str:
    return f"{round(value, 4):.4f}".rstrip("0").rstrip(".")


def _dd_setting(model: str) -> str | None:
    """v1's `dd_50_86` as v2's map setting, `sine_50_86` (v1's API computed single sine degree days)."""
    match = DD_MODEL.match(model)
    if not match:
        return None
    base, upper = match.groups()
    return f"sine_{base}_{upper}" if upper else f"sine_{base}"


def _date(text: str | None) -> str | None:
    """A date as v1's forms sent it (YYYY-MM-DD), or None for anything else."""
    if not text or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None
