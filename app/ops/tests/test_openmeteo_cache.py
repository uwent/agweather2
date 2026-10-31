from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest

from agdata import corrections
from agdata.sources import openmeteo as source
from ops import openmeteo, points
from ops.models import WeatherCellCache

NOW = datetime(2026, 7, 15, 18, tzinfo=UTC)
STILLWATER = (36.12, -97.07)  # outside the Wisconsin box


def test_spans_are_months_then_the_forecast():
    today = NOW.date()
    assert openmeteo.spans(date(2026, 5, 20), date(2026, 7, 20), today) == [
        ("historical", date(2026, 5, 1), date(2026, 5, 31)),
        ("historical", date(2026, 6, 1), date(2026, 6, 30)),
        ("historical", date(2026, 7, 1), date(2026, 7, 7)),  # to the day before the forecast reaches back
        ("forecast", date(2026, 7, 8), date(2026, 7, 26)),
    ]
    assert openmeteo.spans(date(2021, 12, 30), date(2022, 1, 2), today) == [
        ("archive", date(2021, 12, 1), date(2021, 12, 31)),
        ("historical", date(2022, 1, 1), date(2022, 1, 31)),
    ]


@pytest.fixture
def fake_fetch(monkeypatch):
    """Open-Meteo at 20 °C (forecast 25 °C), counting fetches."""
    fetched = []

    def fetch(endpoint, cell, first, last, session=None, api_key=None):
        fetched.append((endpoint, first, last))
        n = ((last - first).days + 1) * 24
        start = datetime(first.year, first.month, first.day, tzinfo=UTC)
        values = {name: np.full(n, 1.0) for name in ("precipitation", "wind_speed", "dew_point")}
        values["air_temperature"] = np.full(n, 25.0 if endpoint == "forecast" else 20.0)
        return source.Hours(start=start, values=values), 1.0

    monkeypatch.setattr(source, "fetch", fetch)
    return fetched


@pytest.mark.django_db
def test_the_cache_fetches_each_span_once_and_expires_the_forecast(fake_fetch):
    start, end = datetime(2026, 6, 28, tzinfo=UTC), datetime(2026, 7, 20, tzinfo=UTC)
    values, kinds, applied = openmeteo.cell_hours(*STILLWATER, start, end, NOW)
    assert [f[0] for f in fake_fetch] == ["historical", "historical", "forecast"]
    assert applied == (corrections.OPENMETEO_RH.label,)  # the fake hours have no shortwave to correct
    assert values["air_temperature"][0] == 20 and values["air_temperature"][-1] == 25
    assert kinds[0] == "observed" and kinds[-1] == "forecast"
    assert kinds[(NOW - start) // timedelta(hours=1)] == "observed"

    openmeteo.cell_hours(*STILLWATER, start, end, NOW + timedelta(hours=1))
    assert len(fake_fetch) == 3  # all cached
    openmeteo.cell_hours(*STILLWATER, start, end, NOW + timedelta(hours=4))
    assert [f[0] for f in fake_fetch[3:]] == ["forecast"]  # the forecast expires after 3 hours
    openmeteo.cell_hours(*STILLWATER, start, end, NOW + timedelta(hours=25))
    assert [f[:2] for f in fake_fetch[4:]] == [("historical", date(2026, 7, 1)), ("forecast", date(2026, 7, 9))]
    june = WeatherCellCache.objects.get(first_day=date(2026, 6, 1))
    assert june.expires_at is None  # a past month never expires


@pytest.mark.django_db
def test_a_model_outside_the_box_runs_on_open_meteo(fake_fetch, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    settings.SERVICE_BOX = "wisconsin"
    assert not points.in_archive(*STILLWATER, date(2026, 7, 1), date(2026, 7, 20))
    result = points.model_at_point(
        *STILLWATER, "degree-days", date(2026, 7, 5), date(2026, 7, 20), NOW, biofix=date(2026, 7, 1)
    )
    assert result.reason is None
    assert result.kinds[:10] == ["observed"] * 10 and result.kinds[10] == "partial" and result.kinds[-1] == "forecast"
    dd = result.outputs["dd"]
    # July 5–7 from history (20 °C), from July 8 the forecast endpoint, which also covers the last week (25 °C)
    assert dd[0] == pytest.approx(20 * 1.8 + 32 - 50, abs=0.1) and dd[-1] == pytest.approx(25 * 1.8 + 32 - 50, abs=0.1)
