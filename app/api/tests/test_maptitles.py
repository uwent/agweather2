"""Map titles, subtitles and captions (`api.maptitles`): broad to specific, in the public style."""

import re
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pytest

from agdata.layers import LAYERS
from api import maptitles
from api.params import DegreeDaySetting
from api.routes import maps
from api.tests.test_docs import BANNED

NOV1, NOV5 = date(2026, 11, 1), date(2026, 11, 5)
SINE = DegreeDaySetting(name="sine_50_86", method="sine", base_f=50, upper_f=86)
MODIFIED = DegreeDaySetting(name="modified_50_86", method="modified", base_f=50, upper_f=86)
WEATHER = [layer for layer in LAYERS.values() if layer.source != "model"]


def ask(layer_id, first, last=None, stat=None, setting=None, model=None):
    return SimpleNamespace(
        layer=LAYERS[layer_id], first=first, last=last or first, stat=stat, setting=setting, model=model
    )


@pytest.mark.parametrize("layer", WEATHER, ids=lambda layer: layer.id)
def test_every_weather_layer_has_a_public_name(layer):
    title = maptitles.layer_title(layer)
    # not the catalog's technical wording
    catalog = r"hour ending|FAO-56|Downward| at 2 m| at 10 m|daily max\b|daily min\b|\(hourly\)"
    assert not re.search(catalog, title), title
    assert not BANNED.search(title) and "_" not in title and "RH" not in title.split()
    if layer.time_axis == "day" and layer.source == "daily":
        assert maptitles.subject(layer)[1] is not None  # each daily layer names its statistic


@pytest.mark.parametrize(
    ("a", "units", "title"),
    [
        (ask("air_temperature_max", NOV5), "us", "Air temperature, daily maximum"),
        (ask("precipitation_sum", date(2026, 11, 5)), "us", "Precipitation, daily total"),
        (ask("precipitation_sum", NOV1, NOV5, "sum"), "us", "Precipitation, cumulative total"),
        (ask("precipitation_total", date(2026, 11, 5)), "us", "Precipitation, cumulative total"),
        (ask("air_temperature_max", NOV1, NOV5, "max"), "us", "Air temperature, cumulative maximum"),
        (ask("air_temperature_max", NOV1, NOV5, "mean"), "us", "Air temperature, mean daily maximum"),
        (ask("air_temperature_min", NOV1, NOV5, "max"), "us", "Air temperature, highest daily minimum"),
        (
            ask("hours_rh_over_90", NOV1, NOV5, "sum"),
            "us",
            "Hours with relative humidity of 90% or more, cumulative count",
        ),
        (ask("soil_temperature_10cm_mean", date(2026, 11, 5)), "us", "Soil temperature, 10 cm (3.9 in), daily mean"),
        (ask("air_temperature_hourly", datetime(2026, 11, 6, 13, tzinfo=UTC)), "us", "Air temperature, hourly"),
        (
            ask("degree_days", date(2026, 1, 1), date(2026, 11, 5), "sum", SINE),
            "us",
            "Growing degree days, single sine 50–86 °F, cumulative total",
        ),
        (
            ask("degree_days", date(2026, 1, 1), date(2026, 11, 5), "sum", MODIFIED),
            "metric",
            "Growing degree days, modified 10–30 °C, cumulative total",
        ),
        (ask("dd_sine_50", date(2026, 11, 5)), "us", "Growing degree days, single sine, base 50 °F, cumulative total"),
    ],
)
def test_titles_go_from_broad_to_specific(a, units, title):
    assert maptitles.title(a, units) == title


def test_a_model_is_its_name_and_result():
    output = SimpleNamespace(label="P-days since emergence")
    model = SimpleNamespace(
        spec=SimpleNamespace(name="Early blight P-days", options=()), output=output, tier="mid", crop="potato",
        options={}, season=None,
    )  # fmt: skip
    a = ask("early-blight-pdays", date(2026, 7, 15), model=model)
    assert maptitles.title(a, "us") == "Early blight P-days: P-days since emergence"
    assert maptitles.subtitle(a) == "Jul 15, 2026 · Potatoes planted on typical mid-season dates"
    model.output = SimpleNamespace(label="Risk level")  # a plain word after the colon is lowercase
    assert maptitles.title(a, "us") == "Early blight P-days: risk level"


def test_dates_use_three_letter_months_and_hours_central_time_with_utc():
    assert maptitles.day_text(date(2026, 11, 5)) == "Nov 5, 2026"
    assert maptitles.range_text(date(2026, 1, 1), date(2026, 11, 5)) == "Jan 1 – Nov 5, 2026"
    assert maptitles.range_text(date(2025, 11, 1), date(2026, 3, 31)) == "Nov 1, 2025 – Mar 31, 2026"
    assert maptitles.hour_text(datetime(2026, 11, 6, 13, tzinfo=UTC)) == "Nov 6, 2026, 7 a.m. CST (13:00 UTC)"
    assert maptitles.hour_text(datetime(2026, 7, 6, 17, tzinfo=UTC)) == "Jul 6, 2026, noon CDT (17:00 UTC)"
    assert maptitles.subtitle(ask("precipitation_total", date(2026, 11, 5)), "Wisconsin") == (
        "Wisconsin · Jan 1 – Nov 5, 2026"
    )


def test_the_caption_gives_sources_the_forecast_and_the_days_combined():
    a = ask("precipitation_sum", date(2026, 11, 1), date(2026, 11, 7), "sum")
    computed = SimpleNamespace(
        values=np.array([[[1.0, 2.0, np.nan]]]),  # the last cell has no data at all (open water): not counted
        steps=[date(2026, 11, d) for d in range(1, 8)],
        kinds=["observed"] * 5 + ["partial", "forecast"],
        extra={"missing_days": np.array([[1.0, 0.0, 7.0]]), "estimated_days": np.array([[0.0, 0.0, 0.0]])},
    )
    assert maptitles.caption(a, computed) == [
        "Data sources: Precipitation from URMA/RTMA hourly grids; the National Blend of Models (NBM) forecast from "
        "Nov 6, 2026.",
        "7 days combined; up to 1 day missing at some locations.",
    ]


def test_a_static_map_is_drawn_with_its_title_subtitle_and_caption(client, archive):
    with mock.patch.object(maps.mapimage, "map_png", return_value=b"png") as drawn:
        response = client.get("/api/v2/maps/precipitation_sum.png", {"stat": "sum", "end": "2025-07-08"})
    assert response.status_code == 200
    args, kwargs = drawn.call_args
    assert args[4:6] == ("Precipitation, cumulative total", "Jan 1 – Jul 8, 2025")
    assert kwargs["caption"][0] == "Data sources: Precipitation from URMA/RTMA hourly grids."
    assert kwargs["caption"][1].startswith("189 days combined")
