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


def test_land_is_in_a_county_and_mostly_land_on_era5lands_mask(tmp_path):
    """Without a mask, land is the county grid; with ERA5-Land's, cells where it's mostly water are left out."""
    from agdata.grid import NDFD, LatLonGrid, Window
    from agdata.sources.era5land import STEP, LandMask

    window = Window(j0=900, j1=904, i0=1400, i1=1406)
    assert regions.land(tmp_path, window).all()  # Fayette County, Iowa: every cell in a county
    lat, lon = NDFD.window_latlon(window)
    south, west = float(np.floor(lat.min() / STEP) * STEP) - STEP, float(np.floor(lon.min() / STEP) * STEP) - STEP
    grid = LatLonGrid(name="era5land", first_lat=south, first_lon=west, step=STEP, ny=6, nx=8)
    fraction = np.ones((6, 8))
    fraction[:, 4:] = 0.0  # water to the east
    (tmp_path / "static").mkdir()
    LandMask(grid=grid, fraction=fraction).save(tmp_path / "static" / "era5land_land_0_1_0_1.npz")
    regions.land.cache_clear()
    found = regions.land(tmp_path, window)
    assert found[lon < west + 2.9 * STEP].all() and not found[lon > west + 4 * STEP].any()
