"""`ops.latency` on the fixture archive: every case answers, within ten times its target (the fixture's 2 x 3 cells
are far smaller than a state, so this catches a large regression, such as a map recomputed for every tile, not a
small one; `manage.py latency` on the real archive judges the targets themselves)."""

from contextlib import suppress
from datetime import date, timedelta
from io import StringIO

import numpy as np
import pytest
from django.core.management import CommandError, call_command

from agdata.series import DailySeries, Forecast
from api.tests import fixture_archive
from ops import latency

LAT, LNG = fixture_archive.POINT
DAY = date(2025, 7, 9)

pytestmark = pytest.mark.django_db  # points read the Open-Meteo cell cache


@pytest.fixture(autouse=True)
def no_open_meteo(monkeypatch):
    """Open-Meteo with nothing to give: models reaching before the fixture archive's July 1 read it (ops.points)."""

    def point_days(lat, lng, first, last, names, now, zone=None):
        n = (last - first).days + 1
        dates = [first + timedelta(days=k) for k in range(n)]
        values = {name: np.full(n, np.nan) for name in names}
        return DailySeries(dates=dates, values=values, kinds=[None] * n, forecast=Forecast(path=None))

    monkeypatch.setattr("ops.points.openmeteo.point_days", point_days)


def _cases():
    return latency.cases(
        lat=LAT,
        lng=LNG,
        map_day=DAY,
        season_start=date(2025, 7, 1),
        last_day=DAY,
        models=("tar-spot",),
        spread=0.0005,  # the sites within the fixture's cells
    )


def test_every_case_answers_well_within_ten_times_its_target(archive):
    latency.warm_up(lat=LAT, lng=LNG, day=date(2025, 7, 2))
    timings = latency.run(_cases(), repeats=1)
    assert [t.status for t in timings] == [200] * len(timings), [latency.describe(t) for t in timings]
    slow = [f"{t.case.name}: {latency.describe(t)}" for t in timings if t.judged_ms > 10 * t.case.target_ms]
    assert not slow


def test_a_kept_map_tile_is_much_faster_than_its_first(archive):
    case = latency.Case(
        name="a day no other test asks for", target_ms=300, path="/tiles/tar-spot/2025-07-05/6/15/23.png"
    )
    found = latency.measure(case, repeats=3)
    assert found.repeat_ms < found.first_ms / 3


def test_tile_of_finds_the_tile_holding_a_point():
    assert latency.tile_of(43.07, -89.40, zoom=6) == (6, 16, 23)
    assert latency.tile_of(0.0, 0.0, zoom=1) == (1, 1, 1)


def test_the_command_reports_each_case(archive):
    out, err = StringIO(), StringIO()
    args = ("--lat", str(LAT), "--lng", str(LNG), "--day", str(DAY), "--models", "tar-spot", "--repeats", "0")
    with suppress(CommandError):  # a case over its target on this machine fails the command; the report is checked
        call_command("latency", *args, stdout=out, stderr=err)
    text = out.getvalue() + err.getvalue()
    assert "risk map, tar-spot, a day" in text
    assert "point, every model through the forecast" in text
