"""Cropland per cell from the Cropland Data Layer (`agdata.cropland`, Phase 6 step 6, D116): the crops' classes,
pixels counted in the cell holding their centre, the statistics over a five-year rotation, the years' lattice,
fetching and unpacking NASS's zips, and the store's status and reading. Synthetic rasters; no network."""

from pathlib import Path

import numpy as np
import pytest

from agdata import cropland
from agdata.grid import Window
from agdata.testing import cdl_raster, cdl_zip
from agmodels import croplist

WINDOW = Window(j0=900, j1=903, i0=1400, i1=1403)  # 3 × 3 cells near Madison
CORN, SOY, SPRING, WINTER, HAY, CLOUDS, DOUBLE = 1, 5, 23, 24, 37, 81, 241

# Each cell's class in each of five years ((years, y, x)): the cases the statistics must get right
ROTATIONS = np.zeros((5, 3, 3), dtype=np.uint8)
ROTATIONS[:, 0, 0] = [CORN, SOY, SOY, SOY, SOY]  # corn one year in five
ROTATIONS[:, 0, 1] = DOUBLE  # corn then soybean in the same year, every year
ROTATIONS[:, 0, 2] = [SPRING, WINTER, SPRING, WINTER, SPRING]  # two wheats: wheat's share is 1, not 2
ROTATIONS[:, 1, 0] = 0  # no data (Canada)
ROTATIONS[:, 1, 1] = [CLOUDS, CORN, CORN, CORN, CORN]  # a cloudy year
ROTATIONS[:, 1, 2] = [HAY, HAY, HAY, HAY, CORN]  # cultivated: the newest year
ROTATIONS[:, 2, 0] = [CORN, HAY, HAY, HAY, HAY]  # not cultivated: once, not the newest
ROTATIONS[:, 2, 1] = [CORN, CORN, HAY, HAY, HAY]  # cultivated: twice
ROTATIONS[:, 2, 2] = [43, 43, 43, 43, 43]  # potato


def test_every_croplist_id_has_classes_or_says_it_has_none():
    for crop_id in croplist.CROPS:
        assert bool(cropland.codes(crop_id)) != (crop_id in cropland.NO_CLASS), crop_id
    assert set(cropland.CODES) <= set(croplist.CROPS)
    assert not any(croplist.CROPS[c].members for c in cropland.CODES)  # groups take their members'
    assert set(croplist.CROPS) >= cropland.NO_CLASS and not cropland.NO_CLASS & set(cropland.CODES)
    assert cropland.codes("wheat") == cropland.codes("spring-wheat") | cropland.codes("winter-wheat")
    assert 241 in cropland.codes("corn") and 241 in cropland.codes("soybean")  # double crops count for both
    assert cropland.codes("raspberry") == cropland.codes("blackberry") == {55}
    assert not {37, 59, 60, 176, 0, 81} & cropland.CULTIVATED and {1, 36, 61, 68, 250} <= cropland.CULTIVATED


def test_pixel_centres_find_the_same_cells_as_exact_projection(tmp_path):
    """The build's bilinear lattice puts every pixel in the cell exact projection does (the raster's classes are
    set by exact projection), so a cell of one class counts nothing else."""
    classes = np.arange(1, 10, dtype=np.uint8).reshape(3, 3) + 100
    raster = cropland.open_rasters({2025: cdl_raster(tmp_path / "a.tif", WINDOW, classes)})
    counts = cropland.count_block(rasters=tuple(raster), block=WINDOW)
    per_class = counts["classes"][0]
    for y in range(3):
        for x in range(3):
            assert per_class[y, x].sum() == counts["pixels"][y, x] == per_class[y, x, classes[y, x]]
    assert 6000 < counts["pixels"].mean() < 7000  # ~2.37 km square cells at 43° N in 30 m pixels


def _years(tmp_path: Path, rotations=ROTATIONS, shift: dict[int, float] | None = None) -> dict[int, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return {
        2021 + k: cdl_raster(tmp_path / f"{2021 + k}.tif", WINDOW, rotations[k], shift_m=(shift or {}).get(2021 + k, 0))
        for k in range(len(rotations))
    }


def test_statistics_over_a_five_year_rotation(tmp_path):
    rasters = cropland.open_rasters(_years(tmp_path))
    s = cropland.block_shares(cropland.count_block(rasters=tuple(rasters), block=WINDOW))
    assert s["corn_mean"][0, 0] == pytest.approx(0.2) and s["corn_any"][0, 0] == 1.0
    assert s["soybean_mean"][0, 0] == pytest.approx(0.8) and s["soybean_any"][0, 0] == 1.0
    assert s["corn_mean"][0, 1] == s["soybean_mean"][0, 1] == 1.0  # a double crop for both
    assert s["wheat_mean"][0, 2] == 1.0 and s["wheat_any"][0, 2] == 1.0  # a union, not a sum
    assert s["spring-wheat_mean"][0, 2] == pytest.approx(0.6) and s["winter-wheat_any"][0, 2] == 1.0
    assert s["observed"][1, 0] == 0 and np.isnan(s["corn_mean"][1, 0]) and np.isnan(s["cultivated"][1, 0])
    assert s["observed"][1, 1] == pytest.approx(0.8) and s["corn_mean"][1, 1] == 1.0  # of the years observed
    assert s["cultivated"][1, 2] == 1.0 and s["cultivated"][2, 0] == 0.0 and s["cultivated"][2, 1] == 1.0
    assert s["alfalfa_any"][1, 2] == 0.0  # other hay isn't alfalfa
    assert s["potato_mean"][2, 2] == 1.0 and s["corn_any"][2, 2] == 0.0
    packed = cropland.pack(s["corn_mean"])
    assert packed[0, 0] == 2000 and packed[1, 0] == cropland.MISSING
    np.testing.assert_array_equal(cropland.unpack(packed), np.round(s["corn_mean"], 4))


def test_a_cell_half_observed_keeps_its_shares_and_under_half_goes_missing(tmp_path):
    rotations = np.full((1, 3, 3), CORN, dtype=np.uint8)
    rasters = cropland.open_rasters({2025: cdl_raster(tmp_path / "a.tif", WINDOW, rotations[0])})
    counts = cropland.count_block(rasters=tuple(rasters), block=WINDOW)
    classes = counts["classes"]
    n = counts["pixels"][0, 0]
    classes[0, 0, 0, CORN], classes[0, 0, 0, 0] = n // 2 - 1, n - n // 2 + 1  # just over half Canada
    s = cropland.block_shares(counts)
    assert s["observed"][0, 0] < 0.5 and np.isnan(s["corn_mean"][0, 0])
    classes[0, 0, 0, CORN], classes[0, 0, 0, 0] = n - n // 2, n // 2  # half: kept
    assert cropland.block_shares(counts)["corn_mean"][0, 0] == 1.0


def test_years_off_the_lattice_are_refused(tmp_path):
    rasters = cropland.open_rasters(_years(tmp_path, shift={2024: 10.0}))
    with pytest.raises(cropland.Misaligned, match="2024"):
        cropland.check_aligned(rasters)
    whole = cropland.open_rasters(_years(tmp_path / "whole", shift={2024: 30.0}))
    cropland.check_aligned(whole)  # a whole pixel off is the same lattice, a different extent


def test_zips_unpack_only_the_raster(tmp_path):
    for year, raster in _years(tmp_path / "src").items():
        cdl_zip(tmp_path, year, raster)
    assert cropland.missing_years(tmp_path, cropland.YEARS) == []
    assert cropland.missing_years(tmp_path, [2026]) == [2026]
    out = cropland.extract(tmp_path, 2025)
    assert [p.name for p in cropland.extracted(tmp_path).iterdir()] == ["2025_30m_cdls.tif"]
    stamp = out.stat().st_mtime_ns
    assert cropland.extract(tmp_path, 2025).stat().st_mtime_ns == stamp  # once
    assert cropland.delete_extracted(tmp_path) > 0 and not cropland.extracted(tmp_path).exists()
    assert cropland.zip_path(tmp_path, 2025).exists()


class _Response:
    def __init__(self, body: bytes, start: int, status: int):
        self.body, self.status_code = body[start:], status
        self.headers = {"Content-Length": str(len(self.body))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        import requests

        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)  # type: ignore[arg-type]

    def iter_content(self, chunk_size: int):
        for k in range(0, len(self.body), 4):
            yield self.body[k : k + 4]


def test_a_fetch_resumes_a_part_file_with_a_range(tmp_path, monkeypatch):
    import requests

    body = b"0123456789abcdef"
    asked = []

    def get(url, headers, stream, timeout):
        asked.append(headers.get("Range"))
        start = int(headers["Range"][6:-1]) if "Range" in headers else 0
        return _Response(body, start, 206 if start else 200)

    monkeypatch.setattr(requests, "get", get)
    dest = tmp_path / "cdl" / cropland.zip_name(2025)
    dest.parent.mkdir()
    dest.with_name(dest.name + ".part").write_bytes(body[:6])
    seen = []
    assert cropland.fetch(2025, dest, progress=lambda done, total: seen.append((done, total))) == len(body)
    assert dest.read_bytes() == body and asked == ["bytes=6-"] and seen[-1] == (16, 16)
    assert not dest.with_name(dest.name + ".part").exists()

    def short(url, headers, stream, timeout):
        response = _Response(body, 0, 200)
        response.headers["Content-Length"] = "99"
        return response

    answers = iter([500, 200])

    def flaky(url, headers, stream, timeout):
        return _Response(body, 0, next(answers))

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(cropland, "RETRY_WAIT_S", 0)
    assert cropland.fetch(2023, tmp_path / "cdl" / cropland.zip_name(2023)) == len(body)  # a 500 is tried again

    monkeypatch.setattr(requests, "get", short)
    with pytest.raises(OSError, match="rerun to resume"):
        cropland.fetch(2024, tmp_path / "cdl" / cropland.zip_name(2024), tries=1)


def test_a_build_reads_back_and_says_when_it_is_stale(tmp_path, monkeypatch):
    paths = _years(tmp_path / "src")
    covered = np.ones(WINDOW.shape, dtype=bool)
    covered[2, 2] = False  # outside the coverage: missing
    assert cropland.status(tmp_path, WINDOW, cropland.YEARS) == "missing"
    summary = cropland.build(tmp_path, WINDOW, covered, paths)
    assert summary == {"covered_cells": 8, "observed_cells": 7, "cultivated_share": pytest.approx(0.8571, abs=1e-4)}
    assert cropland.status(tmp_path, WINDOW, cropland.YEARS) is None
    assert cropland.stored_years(tmp_path) == cropland.YEARS
    assert (
        cropland.status(tmp_path, WINDOW, range(2022, 2027)) == "out of date: built from [2021, 2022, 2023, 2024, 2025]"
    )
    assert cropland.status(tmp_path, Window(j0=900, j1=904, i0=1400, i1=1403), cropland.YEARS) == (
        "out of date: the service box changed"
    )
    monkeypatch.setattr(cropland, "VERSION", cropland.VERSION + 1)
    assert cropland.status(tmp_path, WINDOW, cropland.YEARS) == "out of date: the code changed"
    found = cropland.load(tmp_path)
    assert found is not None and found.years == cropland.YEARS
    assert found.share("corn", "mean", WINDOW)[0, 0] == pytest.approx(0.2)
    assert np.isnan(found.share("potato", "mean", WINDOW)[2, 2])  # outside the coverage
    assert found.share(None, "cultivated", WINDOW)[1, 2] == 1.0
    wider = Window(j0=899, j1=901, i0=1402, i1=1404)  # padded outside the store
    padded = found.share("corn", "any", wider)
    assert np.isnan(padded[0]).all() and np.isnan(padded[:, 1]).all() and padded[1, 0] == 0.0
    with pytest.raises(KeyError):
        found.share("oak", "mean", WINDOW)
    assert cropland.load(tmp_path) is found  # read once


def test_a_stopped_build_keeps_the_store(tmp_path):
    paths = _years(tmp_path / "src")
    covered = np.ones(WINDOW.shape, dtype=bool)
    assert cropland.build(tmp_path, WINDOW, covered, paths) is not None
    before = (cropland.path(tmp_path) / "zarr.json").read_bytes()
    assert cropland.build(tmp_path, WINDOW, covered, paths, stopping=lambda: True) is None
    assert (cropland.path(tmp_path) / "zarr.json").read_bytes() == before
    assert not cropland.path(tmp_path).with_name("cropland.zarr.part").exists()


def test_a_misaligned_year_stops_the_build(tmp_path):
    paths = _years(tmp_path / "src", shift={2025: 15.0})
    with pytest.raises(cropland.Misaligned):
        cropland.build(tmp_path, WINDOW, np.ones(WINDOW.shape, dtype=bool), paths)
    assert cropland.load(tmp_path) is None


@pytest.mark.network
@pytest.mark.enable_socket
def test_nass_serves_the_five_years():
    import requests

    for year in cropland.YEARS:
        response = requests.head(cropland.url(year), timeout=30)
        assert response.status_code == 200 and int(response.headers["Content-Length"]) > 1e9, year
