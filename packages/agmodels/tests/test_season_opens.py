"""How insect seasons open (D128): each insect's one rule, its first activity, and `in_season` with a place's day."""

from dataclasses import MISSING, fields
from datetime import date

import numpy as np
import pytest

from agmodels import registry
from agmodels.phenology import FIRST_ACTIVITY, Insect, curves, dd_grid, first_activity, form_insect
from agmodels.runner import run
from agmodels.seasons import in_season
from agmodels.spec import OpensOnCalendar, OpensOnCropStage, OpensOnDegreeDays

INSECTS = registry.all_insects()
CALENDAR = {
    "aphid-pvy-vectors",
    "black-cutworm",
    "cabbage-looper",
    "corn-earworm",
    "green-peach-aphid",
    "spotted-wing-drosophila",
    "western-flower-thrips",
}
POTATO = {"colorado-potato-beetle", "colorado-potato-beetle-adults", "colorado-potato-beetle-larvae", "potato-aphid"}


def test_every_insect_declares_its_one_rule():
    """`opens` has no default: an insect without a rule doesn't build, and it's one of three kinds."""
    assert next(f for f in fields(Insect) if f.name == "opens").default is MISSING
    for insect in INSECTS:
        spec = registry.model(insect.id).SPEC
        assert isinstance(spec.opens, OpensOnCalendar | OpensOnDegreeDays | OpensOnCropStage), insect.id
        assert spec.season is not None, insect.id  # the calendar's first day is the fallback without a normal


@pytest.mark.parametrize("insect", INSECTS, ids=lambda i: i.id)
def test_migrants_open_on_the_calendar_crop_pests_on_their_crop_and_the_rest_on_warmth(insect):
    rule = registry.model(insect.id).SPEC.opens
    if insect.id in CALENDAR:
        assert isinstance(rule, OpensOnCalendar)
    elif insect.id in POTATO:
        assert rule == OpensOnCropStage(
            crop="potato-stages", stage="EM", event="early-planted potatoes emerge", planting="early"
        )
    elif insect.id == "codling-moth":
        assert rule == OpensOnCropStage(crop="apple-stages", stage="B", event="apples bloom")
    else:
        assert isinstance(rule, OpensOnDegreeDays)
        assert (rule.method, rule.base_f, rule.upper_f, rule.start) == (
            insect.dd_method,
            insect.base_f,
            insect.upper_f,
            insect.biofix,
        )
        assert rule.lead_days == 7


def test_black_cutworm_is_in_season_before_its_biofix():
    spec = registry.model("black-cutworm").SPEC
    assert spec.season is not None and spec.biofix is not None
    assert spec.season[0] == "04-15" and spec.biofix.default == "05-01"


@pytest.mark.parametrize("insect", [i for i in INSECTS if i.life_stages], ids=lambda i: i.id)
def test_the_first_activity_is_where_a_stage_first_reaches_its_share_of_its_peak(insect):
    dd, label = first_activity(insect)
    x = dd_grid()
    tables = curves(insect)
    stage = next(s for s in insect.life_stages if s.label == label)
    assert tables[f"activity_{stage.key}"][x == dd][0] >= FIRST_ACTIVITY
    for s in insect.life_stages:  # no stage gets there sooner
        assert np.all(tables[f"activity_{s.key}"][x < dd] < FIRST_ACTIVITY)


def test_first_activities_named_for_ben():
    """The first activity each warmth-opened insect's season opens a week before (°F degree days from its start)."""
    found = {
        i.id: (rule.dd, rule.event)
        for i in INSECTS
        if isinstance(rule := registry.model(i.id).SPEC.opens, OpensOnDegreeDays)
    }
    assert found["european-corn-borer"] == (
        395.0,
        "the first adult flight",
    )  # the moths, before the larvae that carry the risk
    assert found["alfalfa-weevil"][0] == 34.0  # egg hatch starts at 0: its 5 % comes a few warm days in
    assert found["seedcorn-maggot"] == (98.0, "the first adult flight")
    ecb = registry.model("european-corn-borer").SPEC.opens
    assert isinstance(ecb, OpensOnDegreeDays) and ecb.form_dd == first_activity(form_insect(INSECT_ECB))[0] == 960.0
    assert ecb.form_below == 1500


INSECT_ECB = next(i for i in INSECTS if i.id == "european-corn-borer")


def test_a_places_opening_day_replaces_the_calendars_first():
    spec = registry.model("corn-rootworm").SPEC  # May 15 to September 30
    assert not in_season(spec, date(2026, 5, 10))
    assert in_season(spec, date(2026, 5, 10), opens="05-01")
    assert not in_season(spec, date(2026, 5, 20), opens="05-25")
    assert in_season(spec, date(2026, 5, 25), opens="05-25")
    assert not in_season(spec, date(2026, 10, 1), opens="05-01")  # the end stays the calendar's
    assert not in_season(spec, date(2026, 9, 1), opens="12-31")  # never opens where the normal never gets there
    assert not in_season(spec, date(2026, 6, 1), opens="05-01", ended=True)


def test_the_runner_marks_days_by_the_places_opening():
    dates = [date(2026, 5, 1 + k) for k in range(20)]
    daily = {"air_temperature_min": np.full(20, 10.0), "air_temperature_max": np.full(20, 25.0)}
    calendar = run("corn-rootworm", dates=dates, daily=daily, latitude=43.0)
    opened = run("corn-rootworm", dates=dates, daily=daily, latitude=43.0, season_opens="05-08")
    assert calendar.in_season is not None and opened.in_season is not None
    assert next(d.day for d, s in zip(dates, calendar.in_season, strict=True) if s) == 15
    assert next(d.day for d, s in zip(dates, opened.in_season, strict=True) if s) == 8
    for name, values in calendar.outputs.items():  # the opening marks days; it changes no output
        assert np.array_equal(values, opened.outputs[name], equal_nan=True), name
