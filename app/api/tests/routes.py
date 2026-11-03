"""A test-only API exercising the plumbing (params, envelope, errors) on the fixture archive, before real endpoints
exist; mounted by `@pytest.mark.urls("api.tests.routes")`."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import path
from ninja import NinjaAPI, Query

from agdata import series
from agdata.catalog import DAILY_VARIABLES
from agdata.grid import NDFD
from api import clock, errors
from api.envelope import Column, Result, catalog_column, etag_for, not_modified, respond
from api.locations import describe
from api.params import DaysQuery, OutputQuery, PointsQuery, QueryParser, SeriesQuery, check_vars
from api.schemas import TableResponse, responses

api = NinjaAPI(title="test", urls_namespace="api-test", parser=QueryParser())
errors.install(api)


@api.get("/days", response=responses(TableResponse))
def days(
    request: HttpRequest,
    where: Query[PointsQuery],
    when: Query[DaysQuery],
    series_options: Query[SeriesQuery],
    output: Query[OutputQuery],
    vars: str | None = None,
) -> HttpResponse:
    names = check_vars(vars, DAILY_VARIABLES, ["air_temperature_max", "precipitation_sum"])
    now = clock.now()
    first, last = when.span(default_end=now.date())
    computed = {**where.echo(), "start": first, "end": last, "vars": names, "units": output.units}
    etag = etag_for(request, computed, series.last_written(settings.DATA_DIR, first, last, now=now))
    if (unchanged := not_modified(request, etag)) is not None:
        return unchanged
    locations = [describe(lat, lng) for lat, lng in where.locations()]
    columns: dict[str, list] = {"point": [], "date": [], "kind": [], **{n: [] for n in names}}
    for k, (lat, lng) in enumerate(where.locations()):
        cell = NDFD.cell_of(lat, lng)
        assert cell is not None
        found = series.point_days(settings.DATA_DIR, *cell, first, last, names, now=now)
        columns["point"] += [k] * len(found.dates)
        columns["date"] += found.dates
        columns["kind"] += found.kinds
        for n in names:
            columns[n] += list(found.values[n])
    table = [Column(name=n, values=columns[n]) for n in ("point", "date", "kind")]
    table += [catalog_column(n, columns[n]) for n in names]
    if len(locations) == 1:
        table = table[1:]  # one point: no point column
    return respond(
        request,
        Result(
            request=computed,
            columns=table,
            location=locations[0] if len(locations) == 1 else None,
            locations=locations if len(locations) > 1 else None,
            summary={"days_requested": (last - first).days + 1},
            sources=["urma", "nbm"],
            etag=etag,
            filename=f"agweather-days-{first}-{last}",
            timings={"read": 1.5},
        ),
    )


@api.get("/broken")
def broken(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("secret internals")


urlpatterns = [path("api/test/", api.urls)]
