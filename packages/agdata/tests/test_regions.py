import numpy as np

from agdata import coast, regions
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


def test_summaries_leave_open_water_out_of_a_shore_county():
    door = regions.find("55029")
    assert door is not None
    window = Window(j0=980, j1=1030, i0=1520, i1=1570)  # the Door Peninsula with Green Bay and Lake Michigan
    grid = regions.cell_counties(window) == 3029
    kept = regions.summary_counties(window) == 3029
    assert kept.sum() < grid.sum() and not (kept & coast.water(window)).any()
    assert (kept <= grid).all()


def test_areas_by_county_and_state_carry_land_area_and_cells():
    dane = regions.areas("county")[3027]
    assert dane is not None and dane.fips == "55025" and dane.name == "Dane County" and dane.cells > 500
    assert 3.0e9 < dane.land_m2 < 3.2e9  # 1,197 sq mi
    states = {a.state: a for a in regions.areas("state") if a is not None}
    wisconsin = states["WI"]
    assert wisconsin.fips == "55" and wisconsin.name == "Wisconsin"
    in_wi = [a for a in regions.areas("county") if a is not None and a.state == "WI"]
    assert wisconsin.cells == sum(a.cells for a in in_wi) and len(in_wi) == 72
    window = Window(j0=900, j1=930, i0=1460, i1=1490)  # around Madison
    by_state = regions.area_labels("state", window)
    by_county = regions.area_labels("county", window)
    assert {regions.areas("state")[k].state for k in np.unique(by_state) if k} == {  # type: ignore[union-attr]
        regions.areas("county")[k].state
        for k in np.unique(by_county)
        if k  # type: ignore[union-attr]
    }


def test_area_stats_skip_missing_cells_and_count_levels_and_nones():
    labels = np.array([[1, 1, 2], [2, 2, 0]])
    values = np.array([[1.0, 3.0, np.nan], [2.0, 0.0, 9.0]])
    stats = regions.area_stats(values, labels, n=4, levels=4)
    assert stats.with_data.tolist() == [0, 2, 2, 0]
    assert stats.mean[1] == 2.0 and stats.min[2] == 0.0 and stats.max[2] == 2.0
    assert np.isnan(stats.mean[3]) and np.isnan(stats.min[0])  # an area without a value
    assert stats.levels is not None
    assert stats.levels[1].tolist() == [0, 1, 0, 1] and stats.levels[2].tolist() == [1, 0, 1, 0]
    present = np.isfinite(values) | (labels == 2)  # area 2's missing cell is an answer of none
    with_none = regions.area_stats(values, labels, n=4, present=present)
    assert with_none.with_data[2] == 3 and with_none.none[2] == 1 and with_none.mean[2] == 1.0
