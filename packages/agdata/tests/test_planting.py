"""County lookup and typical planting dates (D34)."""

import csv

import numpy as np
import pytest

from agdata.places import DATA, counties, county_at, county_ids
from agdata.planting import CROPS, typical_planting
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
    assert ids.shape == (3,) and ids[2] == 0 and all(counties()[k] for k in ids[:2])


def test_dane_county_from_deines_and_alabama_from_nass():
    corn = typical_planting("corn", 43.0731, -89.4012)
    assert corn is not None and corn.level == "county" and corn.typical == "05-08" and "Deines" in corn.source
    soy = typical_planting("soybean", 43.0731, -89.4012)
    assert soy is not None and soy.typical > corn.typical
    south = typical_planting("corn", 32.37, -86.30)  # Montgomery, outside Deines's 12 states
    assert south is not None and south.level == "state" and south.area == "AL" and "NASS" in south.source
    kansas = typical_planting("winter-wheat", 38.0, -97.5)
    assert kansas is not None and kansas.typical.startswith("10-")  # in the fall
    assert typical_planting("corn", 61.2, -149.9) is None
    with pytest.raises(ValueError):
        typical_planting("rice", 43.0, -89.4)


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
        assert any(r["crop"] == crop and r["level"] == "state" for r in rows)


def test_crop_models_have_planting_dates():
    for model in all_models().values():
        if model.SPEC.group == "crop":
            assert model.SPEC.topics[0] in CROPS, model.SPEC.id
