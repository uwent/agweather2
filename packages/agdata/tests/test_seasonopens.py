"""The days insect seasons open from the 30-year normal (`agdata.seasonopens`, D128)."""

import math
from datetime import date

import numpy as np
import pytest

from agdata import climatology, cropland, normals, potatoplanting, regions, seasonopens
from agdata.grid import NDFD, Window
from agdata.testing import freeze_normal
from agmodels import registry
from agmodels.spec import OpensOnCalendar, OpensOnCropStage, OpensOnDegreeDays

WINDOW = Window(j0=1000, j1=1040, i0=1400, i1=1440)  # central Wisconsin
SPRING = 110.0  # the 28 °F freeze, April 20
UPPERS = {"dd_sine_80p1", "dd_sine_86", "dd_sine_90", "dd_sine_92", "dd_sine_95"}  # never reached: 0


def _store(data_dir, rate: float | np.ndarray, spring=SPRING) -> None:
    """Normals whose every running total (but the uppers') adds `rate` (°F·d a day, per cell or everywhere) from
    March 1 (slot 60), and whose daily means are 10 and 20 °C (59 °F: 21 capped-mean degree days above 38 °F)."""
    s = np.arange(366, dtype=float)[:, None, None]
    total = np.asarray(rate, dtype=float) * np.maximum(s - 59, 0) * np.ones((1, *WINDOW.shape))
    daily = {f"{name}/mean": (np.zeros(366) if name in UPPERS else total) for name in normals.RUNNING_NAMES}
    daily |= {"air_temperature_min/mean": np.full(366, 10.0), "air_temperature_max/mean": np.full(366, 20.0)}
    freeze_normal(data_dir, WINDOW, spring, daily=daily)


def _slot(mmdd: str) -> int:
    month, day = (int(p) for p in mmdd.split("-"))
    return climatology.slot(date(climatology.LEAP, month, day))


def _expected(spec, rate: float) -> float:
    """The opening on an even field (where the area's mean is every cell's own) with `_store`'s totals."""
    rule = spec.opens
    if isinstance(rule, OpensOnCalendar):
        return _slot(spec.season[0])
    if isinstance(rule, OpensOnCropStage):
        if rule.crop == "potato-stages":
            planted = SPRING + potatoplanting.OFFSETS["early"]
            return planted - 1 + math.ceil(208 * 1.8 / rate)  # its total from the planting day
        return 59 + math.ceil(346 / rate)  # apple bloom from January 1
    assert isinstance(rule, OpensOnDegreeDays)
    if rule.method == "average_capped_mean":  # 21 a day from its start, March 1
        return 59 + math.ceil(rule.dd / 21) - rule.lead_days
    start = _slot(rule.start)
    dd = rule.dd
    if rule.form_dd is not None:  # 5 a day from March 1 to August 1 is ~770, under the one-flight bound
        assert rule.form_below is not None and rate * (_slot("08-01") - 59) < rule.form_below
        dd = rule.form_dd
    return max(start - 1, 59) + math.ceil(dd / rate) - rule.lead_days


def test_an_even_field_opens_each_insect_by_its_rule(tmp_path):
    _store(tmp_path, rate=5.0)
    for insect in registry.all_insects():
        spec = registry.model(insect.id).SPEC
        found = seasonopens.slots(tmp_path, spec, WINDOW)
        assert np.all(found == _expected(spec, 5.0)), (insect.id, np.unique(found), _expected(spec, 5.0))


def test_a_point_reads_its_map_cell(tmp_path):
    """A gradient (warmer to the east) opens the east first; `at` and `at_point` give exactly the map's cell, read over
    any window."""
    rate = np.linspace(3.0, 8.0, WINDOW.shape[1])[None, :]
    _store(tmp_path, rate=rate)
    spec = registry.model("corn-rootworm").SPEC
    whole = seasonopens.slots(tmp_path, spec, WINDOW)
    assert whole[20, 0] > whole[20, -1]
    part = Window(j0=1030, j1=1060, i0=1420, i1=1450)  # reaching past the normals
    found = seasonopens.slots(tmp_path, spec, part)
    assert np.isnan(found[10:]).all() and np.isnan(found[:, 20:]).all()
    for y, x in ((0, 0), (5, 9), (9, 19)):
        j, i = part.j0 + y, part.i0 + x
        assert found[y, x] == whole[j - WINDOW.j0, i - WINDOW.i0]
        assert seasonopens.at(tmp_path, spec, (j, i)) == seasonopens.slot_text(found[y, x])
        lat, lon = NDFD.latlon(j, i)
        assert seasonopens.at_point(tmp_path, spec, float(lat), float(lon)) == (
            seasonopens.slot_text(found[y, x]),
            None,
        )


def test_without_the_normal_a_point_takes_the_calendar_and_says_so(tmp_path):
    spec = registry.model("corn-rootworm").SPEC
    assert seasonopens.at_point(tmp_path, spec, 43.07, -89.40) == (None, seasonopens.MISSING)  # not built
    assert seasonopens.at_point(None, spec, 43.07, -89.40) == (None, seasonopens.MISSING)
    _store(tmp_path, rate=5.0)
    assert seasonopens.at_point(tmp_path, spec, 37.1, -87.9) == (None, seasonopens.MISSING)  # Kentucky: past them
    migrant = registry.model("corn-earworm").SPEC
    assert seasonopens.at_point(tmp_path, migrant, 37.1, -87.9) == (None, None)  # the calendar is its rule
    assert seasonopens.region(tmp_path, migrant) == migrant.season[0]  # type: ignore[index]


def test_a_store_without_degree_days_has_no_openings(tmp_path):
    """The test archives' normals hold only the freeze: rules that read degree days have no map, not an error."""
    freeze_normal(tmp_path, WINDOW, SPRING)
    assert np.isnan(seasonopens.slots(tmp_path, registry.model("corn-rootworm").SPEC, WINDOW)).all()


def test_the_weighted_percentile():
    values = np.arange(1.0, 11.0)
    assert seasonopens.weighted_percentile(values, np.ones(10), 10) == 1.0
    assert seasonopens.weighted_percentile(values, np.ones(10), 50) == 5.0
    weights = np.where(values > 6, 1.0, 0.0)  # only 7–10 count
    assert seasonopens.weighted_percentile(values, weights, 10) == 7.0
    assert seasonopens.weighted_percentile(values, np.array([np.nan] * 10), 10) is None


def test_the_region_opens_on_the_tenth_percentile_of_cultivated_land(tmp_path, monkeypatch):
    rate = np.linspace(3.0, 8.0, WINDOW.shape[1])[None, :]
    _store(tmp_path, rate=rate)
    spec = registry.model("corn-rootworm").SPEC
    slots = seasonopens.slots(tmp_path, spec, WINDOW)
    share = np.zeros(WINDOW.shape)
    share[:, :10] = 0.5  # farmland only in the cool west
    found = cropland.Cropland(window=WINDOW, years=(2025,), cells={"cultivated": cropland.pack(share)}, stamp=1.0)
    monkeypatch.setattr(cropland, "load", lambda data_dir: found)
    land = regions.land(WINDOW)  # cells in a county and not open water
    west = land & (share > 0)
    expected = seasonopens.weighted_percentile(slots[west], np.full(int(west.sum()), 0.5), 10)
    assert expected is not None
    assert seasonopens.region(tmp_path, spec) == seasonopens.slot_text(expected)
    assert expected > np.nanpercentile(slots[land], 10)  # later than the whole area's, whose warm east opens first
    monkeypatch.setattr(cropland, "load", lambda data_dir: None)  # no store: every cell alike
    even = seasonopens.weighted_percentile(slots[land], np.ones(int(land.sum())), 10)
    assert even is not None and seasonopens.region(tmp_path, spec) == seasonopens.slot_text(even)


def test_built_maps_are_read_while_current(tmp_path, monkeypatch):
    _store(tmp_path, rate=5.0)
    assert seasonopens.status(tmp_path) == "none yet"
    assert seasonopens.build(tmp_path) == len(seasonopens.opening_specs())
    assert seasonopens.status(tmp_path) is None
    computed = seasonopens.compute(tmp_path, seasonopens.opening_specs(), WINDOW)
    seasonopens._whole.cache_clear()
    monkeypatch.setattr(seasonopens, "compute", lambda *a, **k: pytest.fail("read from the built file"))
    for spec in seasonopens.opening_specs():
        np.testing.assert_array_equal(seasonopens.slots(tmp_path, spec, WINDOW), computed[spec.id])
    _store(tmp_path, rate=6.0)  # the normals rebuilt
    assert seasonopens.status(tmp_path) is not None


def test_a_map_says_where_the_season_hasnt_opened():
    spec = registry.model("corn-rootworm").SPEC
    opens = np.array([[140.0, 150.0]])  # May 20 and May 30
    land = np.ones(opens.shape, dtype=bool)
    assert seasonopens.map_warning(spec, opens, [date(2026, 5, 31)], land) is None
    text = seasonopens.map_warning(spec, opens, [date(2026, 5, 25)], land)
    assert (
        text
        == "Blank areas are where the season for corn rootworm hasn't opened yet. It opens about a week before the first egg hatch in a typical year."
    )
    assert seasonopens.map_warning(spec, opens, [date(2026, 5, 25)], np.array([[True, False]])) is None  # water
    potato = registry.model("colorado-potato-beetle").SPEC
    assert seasonopens.how(potato) == "on the day early-planted potatoes emerge in a typical year"
