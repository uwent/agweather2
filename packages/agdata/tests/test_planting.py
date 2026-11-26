"""County lookup and typical planting dates (D34)."""

import csv
from datetime import date

import numpy as np
import pytest

from agdata.places import DATA, counties, county_at, county_ids
from agdata.planting import CROPS, planting_crop, typical_planting
from agmodels.registry import all_models


@pytest.mark.parametrize(
    ("lat", "lon", "geoid"),
    [
        (43.0731, -89.4012, "55025"),  # Madison: Dane
        (43.30, -89.35, "55021"),  # Arlington research station: Columbia
        (40.83, -96.67, "31109"),  # Lincoln: Lancaster
        (41.88, -87.615, "17031"),  # Chicago's lakefront: Cook, though the point is just offshore on the grid
        (24.555, -81.78, "12087"),  # Key West: Monroe
    ],
)
def test_county_at(lat, lon, geoid):
    county = county_at(lat, lon)
    assert county is not None and county.geoid == geoid


def test_no_county_offshore_or_outside_the_lower_48():
    assert county_at(43.5, -87.0) is None  # mid Lake Michigan
    assert county_at(43.65, -79.38) is None  # Toronto
    assert county_at(61.2, -149.9) is None  # Anchorage


def test_county_ids_take_arrays():
    ids = county_ids(np.array([43.07, 40.83, 61.2]), np.array([-89.40, -96.67, -149.9]))
    assert ids.shape == (3,) and ids[2] == 0  # Anchorage is in no county
    assert [counties()[k].geoid for k in ids[:2]] == ["55025", "31109"]  # Dane, Lancaster


def test_dane_county_from_deines_and_alabama_from_nass():
    corn = typical_planting("corn", 43.0731, -89.4012, data_dir=None)
    assert corn is not None and corn.level == "county" and corn.typical == "05-08" and "Deines" in corn.source
    soy = typical_planting("soybean", 43.0731, -89.4012, data_dir=None)
    assert soy is not None and soy.typical > corn.typical
    south = typical_planting("corn", 32.37, -86.30, data_dir=None)  # Montgomery, outside Deines's 12 states
    assert south is not None and south.level == "state" and south.area == "AL" and "NASS" in south.source
    kansas = typical_planting("winter-wheat", 38.0, -97.5, data_dir=None)
    assert kansas is not None and kansas.typical.startswith("10-")  # in the fall
    assert typical_planting("corn", 61.2, -149.9, data_dir=None) is None
    with pytest.raises(ValueError):
        typical_planting("rice", 43.0, -89.4, data_dir=None)


def test_the_table_is_consistent():
    geoids = {c.geoid for c in counties() if c}
    states = {c.state for c in counties() if c}
    with (DATA / "planting_dates.csv").open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        assert r["crop"] in CROPS
        assert r["area"] in (geoids if r["level"] == "county" else states), r
        season = [r[k] for k in ("early", "typical", "late")]
        if r["crop"] != "winter-wheat":  # winter wheat's can run into January
            assert season == sorted(season), r
    for crop in CROPS:
        if crop != "potato":  # estimated on the grid (`agdata.potatoplanting`)
            assert any(r["crop"] == crop and r["level"] == "state" for r in rows)


def test_potato_dates_are_each_cells_estimate_from_its_freeze_normal(tmp_path):
    """Potato's early, mid and late planting are the median last 28 °F spring freeze (`last30`) over the area around
    the cell (D127) plus fixed days, at a point as on the map (one answer per cell); None where the normal doesn't
    reach or isn't built."""
    from agdata import springfreeze
    from agdata.grid import NDFD, Window
    from agdata.planting import planting_map
    from agdata.potatoplanting import OFFSETS
    from agdata.testing import freeze_normal

    cell = NDFD.cell_of(44.40, -89.50)  # near Plover
    assert cell is not None
    window = Window(j0=cell[0] - 2, j1=cell[0] + 3, i0=cell[1] - 2, i1=cell[1] + 3)
    assert typical_planting("potato", 44.40, -89.50, data_dir=tmp_path) is None  # no normals built
    slots = 105.0 + np.arange(window.size, dtype=float).reshape(window.shape)  # April 15 onward (a leap year's days)
    slots[0, 0] = np.nan
    freeze_normal(tmp_path, window, slots)
    plover = typical_planting("potato", 44.40, -89.50, data_dir=tmp_path)
    assert plover is not None and plover.level == "cell" and plover.area == f"{cell[0]},{cell[1]}"
    assert "28 °F" in plover.source and "Vegetable Pathology" in plover.source
    area = springfreeze.at(tmp_path, springfreeze.SPRING_28, *cell)  # the freeze over the area around the cell
    assert 115 < area < 119  # near the middle cell's own, slot 117 (April 27): the field rises evenly
    freeze = date(2000, 1, 1).toordinal() + round(area)
    expected = [date.fromordinal(freeze + OFFSETS[t]).strftime("%m-%d") for t in ("early", "mid", "late")]
    assert [plover.early, plover.typical, plover.late] == expected
    for tier, field in (("early", "early"), ("mid", "typical"), ("late", "late")):
        found = planting_map("potato", tier, window, season=2026, data_dir=tmp_path)
        assert np.isnan(found[0, 0]) and np.isfinite(found[1:]).all()
        lat, lng = NDFD.window_latlon(window)
        for y, x in ((2, 2), (4, 3)):
            point = typical_planting("potato", float(lat[y, x]), float(lng[y, x]), data_dir=tmp_path)
            assert point is not None
            assert date.fromordinal(int(found[y, x])) == date.fromisoformat(f"2026-{getattr(point, field)}")
    assert typical_planting("potato", 43.07, -80.0, data_dir=tmp_path) is None  # outside the normals' window
    assert typical_planting("potato", 44.40, -89.50, data_dir=None) is None


def test_a_leap_days_slot_is_march_1_in_other_years():
    from agdata.planting import _slot_dates

    found = _slot_dates(np.array([59.0, 60.0, np.nan]), season=2025)
    assert [date.fromordinal(int(v)) for v in found[:2]] == [date(2025, 3, 1)] * 2 and np.isnan(found[2])
    leap = _slot_dates(np.array([59.0]), season=2024)
    assert date.fromordinal(int(leap[0])) == date(2024, 2, 29)


def test_crop_models_have_planting_dates():
    for model in all_models().values():
        biofix = model.SPEC.biofix
        if model.SPEC.group == "crop" and biofix is not None and biofix.label.startswith("Planting"):
            assert model.SPEC.topics[0] in CROPS, model.SPEC.id


def test_a_perennials_models_take_no_planting():
    """Apple's models count its stages from January 1: no planting tier, so a map doesn't ask for apple's planting
    dates (apple scab's map failed on it)."""
    for model_id in ("apple-scab", "fire-blight", "apple-stages"):
        assert planting_crop(all_models()[model_id].SPEC) is None, model_id
    assert planting_crop(all_models()["late-blight-dsv"].SPEC) == ("potato-stages", "potato")


def test_a_gate_from_a_given_planting_only_has_no_map_tier_or_typical_date():
    """Wheat scab's gate is spring wheat's stages, but its crop is all wheat: a point takes a spring wheat planting
    date the user gives, while its map and a point without one aren't gated (no typical date is assumed)."""
    from datetime import date

    from agdata.planting import map_crop
    from agdata.series import RunSpec, with_planting

    spec = all_models()["wheat-scab"].SPEC
    assert planting_crop(spec) == ("spring-wheat-stages", "spring-wheat") and map_crop(spec) is None
    assert map_crop(all_models()["tar-spot"].SPEC) == ("corn-stages", "corn")
    run = RunSpec(model_id="wheat-scab")
    assert with_planting(run, latitude=46.9, longitude=-97.0, start=date(2025, 6, 1), data_dir=None).planting is None
    tar = with_planting(
        RunSpec(model_id="tar-spot"), latitude=43.0, longitude=-89.4, start=date(2025, 6, 1), data_dir=None
    )
    assert tar.planting is not None
