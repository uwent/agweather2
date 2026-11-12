"""Open water and terrain per cell (`agdata.terrain`, PLAN.md Phase 6 D6): exact water shares, which NHD features
count, the Great Lakes' holes filled, elevation statistics, a build from a small shapefile and DEM read back, and
regions taking their water from the store."""

from pathlib import Path

import numpy as np
import pytest
import shapely

from agdata import coast, regions, terrain
from agdata.grid import NDFD, Window
from agdata.testing import WINDOW, terrain_store

ROW = Window(j0=900, j1=901, i0=1400, i1=1403)  # three cells in a row near Madison


def test_water_share_is_exact_and_100_only_for_a_cell_all_water():
    xs, ys = terrain.cell_edges(ROW)
    lake = shapely.box(xs[0], ys[0], (xs[1] + xs[2]) / 2, ys[1])  # the first cell and half the second
    islanded = shapely.box(xs[2], ys[0], xs[3], ys[1]).difference(
        shapely.box(xs[2] + 10, ys[0] + 10, xs[2] + 11, ys[0] + 11)
    )
    share = terrain.water_share([lake, islanded], ROW)
    assert share.tolist() == [[100, 50, 99]]  # a 1 m² island keeps the third cell from being all water
    overlapping = [lake, shapely.box(xs[0], ys[0], xs[1], ys[1])]  # a lake on a river counts once
    assert terrain.water_share(overlapping, ROW).tolist() == [[100, 50, 0]]


def _shapefile(path: Path, features: list[tuple[str, int, tuple[float, float, float, float]]]) -> Path:
    """A waterbody shapefile in lat/lon as NHD's: (FTYPE, FCODE, (west, south, east, north)) per feature."""
    import shapefile

    w = shapefile.Writer(str(path), shapeType=shapefile.POLYGON)
    # pyshp's decorator on Writer.field hides its `self` from pyright; the calls are fine
    w.field(name="FTYPE", field_type="C", size=24)  # pyright: ignore[reportCallIssue]
    w.field(name="FCODE", field_type="N", size=9)  # pyright: ignore[reportCallIssue]
    for ftype, fcode, (west, south, east, north) in features:
        w.poly([[(west, south), (west, north), (east, north), (east, south), (west, south)]])
        w.record(ftype, fcode)
    w.close()
    return path.with_suffix(".shp")


def test_open_water_is_lakes_reservoirs_and_wide_rivers(tmp_path):
    lat, lng = (float(v) for v in NDFD.latlon(WINDOW.j0, WINDOW.i0))
    near = (lng - 0.005, lat - 0.005, lng + 0.005, lat + 0.005)
    found = _shapefile(
        tmp_path / "water",
        [
            ("LakePond", 39004, near),
            ("LakePond", 39001, near),  # intermittent
            ("SwampMarsh", 46600, near),  # a wetland
            ("Inundation Area", 40307, near),
            ("StreamRiver", 46006, near),
            ("LakePond", 39004, (lng + 5, lat + 5, lng + 5.01, lat + 5.01)),  # far outside the window
        ],
    )
    polygons = terrain.read_water([found], terrain.window_box(WINDOW))
    assert len(polygons) == 2
    expected = terrain.project(np.asarray([shapely.box(*near)], dtype=object))[0]
    assert shapely.area(polygons[0]) == pytest.approx(shapely.area(expected))
    assert 0.5e6 < shapely.area(polygons[0]) < 1.5e6  # ~0.01° square at 43° N, in m²


def test_holes_in_the_great_lakes_are_filled_from_the_wave_height_mask():
    wave = np.zeros((5, 5), dtype=bool)
    wave[:, 1:] = True  # a lake east of a land column
    share = np.full((5, 5), 100, dtype=np.uint8)
    share[:, 0] = 0
    share[:, 1] = 60  # the shore cells, part land
    share[1:4, 3:5] = 0  # a hole offshore in NHD's lake
    share[0, 3] = 40  # a cell on the hole's straight edge
    out, filled = terrain.fill_holes(share, wave)
    assert (out[1:4, 3:5] == 100).all() and out[0, 3] == 100 and filled == 7
    assert (out[:, 0] == 0).all() and (out[:, 1] == 60).all()  # land and the shore keep NHD's share
    share[2, 1] = 0  # a hole reaching the shore: it and its partial neighbours are water, but not all water
    out, filled = terrain.fill_holes(share, wave)
    assert out[2, 1] == out[1, 1] == out[3, 1] == 99 and out[0, 1] == 60 and filled == 10


def test_cell_statistics_need_some_elevation():
    sub = terrain.SUB
    fine = np.full((sub, 2 * sub), np.nan, dtype=np.float32)
    fine[:, :sub] = np.linspace(250, 270, sub)[None, :]  # a slope across the first cell
    fine[: sub // 10, sub:] = 300.0  # the second cell 10% covered (an island): its land's statistics
    stats = terrain.cell_stats(fine)
    assert stats["elevation_mean"][0, 0] == pytest.approx(260, abs=0.01)
    assert stats["elevation_min"][0, 0] == 250 and stats["elevation_max"][0, 0] == 270
    assert stats["elevation_mean"][0, 1] == 300 and stats["elevation_std"][0, 1] == 0
    fine[: sub // 10, sub:] = np.nan
    fine[0, sub] = 300.0  # one fine cell: under MIN_COVER
    assert np.isnan(terrain.cell_stats(fine)["elevation_mean"][0, 1])


def _dem(path: Path, window: Window) -> Path:
    """A DEM as NHDPlus's (Albers, 30 m, centimeters, int32) over the window: 250 m rising 1 m per km east."""
    import rasterio
    from pyproj import Transformer
    from rasterio.transform import from_origin

    box = terrain.window_box(window, margin=0.05)
    to_albers = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    x0, y1 = to_albers.transform(box.west, box.north)
    x1, y0 = to_albers.transform(box.east, box.south)
    width, height = int((x1 - x0) / 30) + 1, int((y1 - y0) / 30) + 1
    xs = x0 + 30 * (np.arange(width) + 0.5)
    values = np.broadcast_to((25000 + (xs - x0) / 10).astype(np.int32), (height, width))
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1, dtype="int32", crs="EPSG:5070",
        transform=from_origin(x0, y1, 30, 30), nodata=-2147483647,
    ) as out:  # fmt: skip
        out.write(values, 1)
    return path


def test_a_build_from_a_shapefile_and_dem_reads_back(tmp_path, monkeypatch):
    lat, lng = (float(v) for v in NDFD.latlon(WINDOW.j0, WINDOW.i0))
    shp = _shapefile(tmp_path / "water", [("LakePond", 39004, (lng - 0.05, lat - 0.05, lng + 0.005, lat + 0.05))])
    dem = _dem(tmp_path / "dem.tif", WINDOW)
    unit = terrain.UNITS[0]
    monkeypatch.setattr(terrain, "archives_for", lambda window: [(unit, "water.7z"), (unit, "elev.7z")])
    monkeypatch.setattr(terrain, "extract", lambda data_dir, file: [shp] if file == "water.7z" else [dem])
    monkeypatch.setattr(terrain, "_is_snapshot", lambda file: file == "water.7z")
    assert terrain.status(tmp_path, WINDOW) == "missing"
    assert terrain.build(tmp_path, WINDOW, np.zeros(WINDOW.shape, dtype=bool))
    assert terrain.status(tmp_path, WINDOW) is None
    found = terrain.load(tmp_path)
    assert found is not None
    share = found.cells["water_share"]
    assert share[0, 0] > 50 and share[0, 2] == 0  # the lake's east edge is just past the first cell's center
    # The DEM's slope: 1 m per km east, and NDFD's cells are ~2.37 km apart on the ground at 43° N (2.54 km is the
    # projection's, true at 25° N); a point reads its own spot
    mean = found.cells["elevation_mean"]
    assert mean[0, 1] - mean[0, 0] == pytest.approx(2.37, abs=0.05)
    point = terrain.point_elevation(tmp_path, lat, lng)
    assert point == pytest.approx(mean[0, 0], abs=0.2)
    assert terrain.point_elevation(tmp_path, lat + 5, lng) is None  # outside the store


def test_regions_take_open_water_from_the_store(tmp_path, monkeypatch):
    found = NDFD.cell_of(44.0, -88.42)  # Lake Winnebago
    assert found is not None
    j, i = found
    window = Window(j0=j - 2, j1=j + 2, i0=i - 2, i1=i + 2)
    share = np.zeros(window.shape, dtype=np.uint8)
    share[1:3, 1:3] = [[100, 50], [49, 99]]
    monkeypatch.setattr(regions, "_terrain_dir", None)
    assert not regions.water(window).any()  # the wave-height mask has no inland lakes
    before = regions.areas("county")
    terrain_store(tmp_path, window, share)
    monkeypatch.setattr(regions, "_terrain_dir", lambda: tmp_path)
    assert regions.water(window).sum() == 3  # 100, 50 and 99: at least half water
    assert not regions.land(window)[1, 1] and regions.land(window)[2, 1]
    county = int(regions.cell_counties(window)[1, 1])
    assert regions.areas("county")[county].cells == before[county].cells - 3  # type: ignore[union-attr]
    outside = Window(j0=window.j1, j1=window.j1 + 2, i0=window.i0, i1=window.i1)
    np.testing.assert_array_equal(regions.water(outside), coast.water(outside))
