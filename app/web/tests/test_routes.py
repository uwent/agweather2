from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
from django.http import HttpResponse
from django.urls import URLResolver, include, path, re_path, reverse
from django.urls.resolvers import RegexPattern

from web.management.commands.export_routes import page_routes, routes_ts

ROUTES_TS = Path(__file__).resolve().parents[3] / "frontend" / "lib" / "routes.ts"


def view(request, **kwargs):
    return HttpResponse()


HERE = view.__module__.split(".")[0]


def resolver(patterns) -> URLResolver:
    return URLResolver(RegexPattern(r"^/"), patterns)


def test_the_site_routes_are_pages_not_the_api_or_admin():
    names = {route.name for route in page_routes()}
    assert {"home", "changelog", "api-use", "up"} <= names
    assert "api-root" not in names  # Django's RedirectView, into the API
    assert not any(name.startswith("admin") or name.startswith("api-2") for name in names)


def test_routes_ts_names_every_route():
    """bin/types writes it and Prettier formats it, so bin/ci checks it's current with git diff; here, that no route
    is missing."""
    written = ROUTES_TS.read_text()
    for route in page_routes():
        assert f"/** {route.name}: " in written, "frontend/lib/routes.ts is stale: run bin/types"


def test_parameters_from_path_converters_and_regex_groups():
    patterns = [
        path("", view, name="home"),
        path("sites/<str:lat>,<str:lng>", view, name="site"),
        path("years/<int:year>/report-card", view, name="report_card"),
        re_path(r"^files/(?P<path>.+)$", view, name="files"),
        path("hidden", view),  # no name
        path("section/", include(([path("inner", view, name="inner")], "app"), namespace="app")),
        path("open/", include([path("nested", view, name="nested")])),
    ]
    routes = {route.name: route for route in page_routes(resolver(patterns), apps=[HERE])}
    assert set(routes) == {"home", "site", "report_card", "files", "nested"}
    assert routes["site"].params == (("lat", "string"), ("lng", "string"))
    assert routes["report_card"].params == (("year", "number"),)

    ts = routes_ts(list(routes.values()))
    assert "  home: (): string => '/',\n" in ts
    assert (
        "  site: (params: { lat: string; lng: string }): string => `/sites/${part(params.lat)},${part(params.lng)}`,"
        in ts
    )
    assert "  reportCard: (params: { year: number }): string => `/years/${part(params.year)}/report-card`," in ts
    assert (
        "  /** files: /files/<path> */\n  files: (params: { path: string }): string => `/files/${part(params.path)}`,"
        in ts
    )
    assert "  nested: (): string => '/open/nested'," in ts


def test_no_helper_without_parameters():
    ts = routes_ts(page_routes(resolver([path("about", view, name="about")]), apps=[HERE]))
    assert "function part" not in ts
    assert ts.endswith("export const routes = {\n  /** about: /about */\n  about: (): string => '/about',\n}\n")


def test_a_name_used_twice_is_refused():
    patterns = [path("a", view, name="twice"), path("b/<int:n>", view, name="twice")]
    with pytest.raises(CommandError, match="more than one pattern"):
        page_routes(resolver(patterns), apps=[HERE])
    with pytest.raises(CommandError, match="same function name"):
        routes_ts(page_routes(resolver([path("a", view, name="a-b"), path("b", view, name="a_b")]), apps=[HERE]))


def test_command_prints_it(capsys):
    call_command("export_routes")
    assert capsys.readouterr().out == routes_ts(page_routes())


def test_encoding_matches_django():
    """routes.test.ts holds the frontend to the same paths."""
    assert (
        reverse("downloads", kwargs={"path": "daily/2025/a b+c,d#e?.nc"}) == "/downloads/daily/2025/a%20b+c,d%23e%3F.nc"
    )
