import numpy as np

from agdata import regions
from agdata.grid import NDFD, Window


def region(spec: str) -> regions.Region:
    found = regions.find(spec)
    assert found is not None, spec
    return found


def test_regions_by_name_code_or_fips():
    assert regions.find("wisconsin") == regions.find("WI") == regions.find("Wisconsin")
    assert region("new york").id == "new-york" and region("new_york").name == "New York"
    dane = region("55025")
    assert dane.name == "Dane County, WI" and len(dane.county_ids) == 1
    assert regions.find("xx") is None and regions.find("99999") is None
    assert len(region("WI").county_ids) == 72


def test_a_state_line_splits_the_cells():
    beloit = NDFD.cell_of(42.5, -89.03)  # on the Wisconsin–Illinois line
    assert beloit is not None
    j, i = beloit
    window = Window(j0=j - 6, j1=j + 6, i0=i - 3, i1=i + 3)
    wi, il = regions.mask(region("WI"), window), regions.mask(region("IL"), window)
    assert wi.any() and il.any() and not (wi & il).any()
    lat, _ = NDFD.window_latlon(window)
    assert lat[wi].min() > lat[il].max() - 0.05  # Wisconsin north of Illinois, give or take a cell


def test_a_county_holds_its_seat():
    madison = NDFD.cell_of(43.0731, -89.4012)
    assert madison is not None
    window = Window(j0=madison[0] - 2, j1=madison[0] + 3, i0=madison[1] - 2, i1=madison[1] + 3)
    assert regions.mask(region("55025"), window)[2, 2]
    assert np.isin(regions.cell_counties(window), list(region("WI").county_ids)).all()
