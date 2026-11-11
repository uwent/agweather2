"""gridMET's years on the archive's basis (`agdata.climatestore`, D84): the fit's pooling, smoothing and limits,
the adjustment and its clamps, and a year derived from kept files and read back at a cell."""

import os
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from agdata import climatestore, climatology
from agdata.catalog import DAILY_VARIABLES
from agdata.climatology import SLOTS, layout
from agdata.grid import Window
from agdata.sources import gridmet
from agdata.store import DAILY, GridStore

WINDOW = Window(j0=1000, j1=1006, i0=1400, i1=1405)  # inland Wisconsin: no water
# gridMET's packing per variable: (scale, offset), and a plausible field in our units
PACKING = {"tmmx": (0.1, 210.0), "tmmn": (0.1, 210.0)}


def _days(year: int) -> int:
    return (date(year + 1, 1, 1) - date(year, 1, 1)).days


def gridmet_fields(year: int, shape: tuple[int, int]) -> dict[str, np.ndarray]:
    """Each gridMET variable's days (days, ny, nx) in our units, varying by day and cell."""
    n = _days(year)
    t = np.arange(n)[:, None, None]
    cells = np.linspace(0, 1, shape[0] * shape[1]).reshape(shape)[None]
    season = np.sin(2 * np.pi * (t - 100) / 365)
    return {
        "air_temperature_max": 10 + 15 * season + 2 * cells,
        "air_temperature_min": 0 + 12 * season + 2 * cells,
        "precipitation_sum": np.where((t % 3) == 0, 4.0 + cells, 0.0),
        "relative_humidity_max": np.full((n, *shape), 90.0) + 0 * cells,
        "relative_humidity_min": 45 + 10 * season + 0 * cells,
        "shortwave_radiation_sum": 15 + 10 * season + cells,
        "wind_speed_mean": 4 + cells + 0 * t,
        "et0_sum": 2 + 1.5 * season + 0 * cells,
    }


def write_kept(data_dir: Path, year: int, fields: dict[str, np.ndarray], lat: np.ndarray, lon: np.ndarray) -> None:
    """Kept files as gridMET writes them: packed uint16, Kelvin and W/m², rows north to south."""
    for source in gridmet.SOURCES:
        v = fields[source.daily].astype(np.float64)
        if source.name in ("tmmx", "tmmn"):
            v = v + 273.15
        if source.name == "srad":
            v = v / 0.0864
        scale, offset = PACKING.get(source.name, (0.1, 0.0))
        packed = np.round((v - offset) / scale).astype(np.uint16)[:, ::-1]
        gridmet.write(
            gridmet.path(data_dir, source.name, year),
            name=source.name,
            values=packed,
            day=np.array([(date(year, 1, 1) - date(1900, 1, 1)).days + k for k in range(v.shape[0])], dtype=float),
            lat=lat[::-1],
            lon=lon,
            attrs={"scale_factor": np.array([scale]), "add_offset": np.array([offset])},
            fill=np.uint16(32767),
        )


def source_grid(window: Window) -> tuple[np.ndarray, np.ndarray]:
    box = gridmet.extent(window)
    lat = np.arange(np.floor(box.south * 24), np.ceil(box.north * 24) + 1) / 24
    lon = np.arange(np.floor(box.west * 24), np.ceil(box.east * 24) + 1) / 24
    return lat, lon


def write_archive(data_dir: Path, year: int, values: dict[str, np.ndarray]) -> None:
    store = GridStore.create(
        data_dir, DAILY, year, WINDOW, [DAILY_VARIABLES[n] for n in values], chunks=(_days(year), *WINDOW.shape)
    )  # a chunk for the year: a chunk a day would cost ~1 ms each (CLAUDE.md)
    store.write(date(year, 1, 1), values, source=None)


# --- The fit's pieces --------------------------------------------------------------------------------------------


def test_pooled_sums_a_centered_window_wrapping_the_year():
    values = np.random.default_rng(1).random((SLOTS, 2))
    got = climatestore._pooled(values)
    half = climatestore.POOL_DAYS // 2
    for s in (0, 5, 180, 365):
        idx = [(s + d) % SLOTS for d in range(-half, half + 1)]
        np.testing.assert_allclose(got[s], values[idx].sum(axis=0))


def test_smooth_averages_the_neighbours_that_have_values():
    field = np.full((7, 7), 3.0)
    field[3, 3] = np.nan
    np.testing.assert_allclose(climatestore.smooth(field), 3.0)  # a hole takes its neighbours'
    lone = np.full((7, 7), np.nan)
    lone[0, 0] = 2.0
    got = climatestore.smooth(lone)
    assert got[0, 0] == got[2, 2] == 2.0 and np.isnan(got[3, 3])  # reaches two cells, no further
    stepped = np.zeros((1, 5, 10))
    stepped[..., 5:] = 1.0
    got = climatestore.smooth(stepped)[0, 2]
    assert got[0] == 0 and got[-1] == 1 and 0 < got[4] < got[5] < 1  # a step blurred across 5 cells


def fit_of(name: str, archive, gm, years=(2017, 2018)) -> np.ndarray:
    return climatestore.fit_one(name, lambda y: archive(y), lambda y: gm(y), list(years))


def test_fit_adds_the_mean_difference():
    g = lambda y: np.random.default_rng(y).normal(10, 5, (_days(y), 3, 4))  # noqa: E731
    got = fit_of("air_temperature_min", lambda y: g(y) + 1.25, g)
    assert got.shape == (SLOTS, 3, 4)
    np.testing.assert_allclose(got, 1.25, atol=1e-5)


def test_fit_takes_a_ratio_of_totals_capped_and_1_when_dry():
    rain = lambda y: np.where(np.arange(_days(y))[:, None, None] % 2 == 0, 6.0, 0.0) * np.ones((1, 3, 4))  # noqa: E731
    np.testing.assert_allclose(fit_of("precipitation_sum", lambda y: 0.9 * rain(y), rain), 0.9, atol=1e-5)
    np.testing.assert_allclose(fit_of("precipitation_sum", lambda y: 5 * rain(y), rain), 2.0)  # capped
    dry = lambda y: np.zeros((_days(y), 3, 4))  # noqa: E731
    np.testing.assert_allclose(fit_of("precipitation_sum", lambda y: dry(y) + 0.1, dry), 1.0)  # no total to scale


def test_fit_needs_half_the_pairs_in_a_pool():
    g = lambda y: np.full((_days(y), 3, 4), 10.0)  # noqa: E731

    def sparse(y):
        a = g(y) + 2.0
        a[:200] = np.nan  # January to mid-July missing in the archive
        return a

    got = fit_of("air_temperature_max", sparse, g)
    assert np.isnan(got[60]).all() and np.allclose(got[300], 2.0)


def test_adjust_follows_the_calendar_and_clamps():
    table = np.zeros((SLOTS, 1, 1), dtype=np.float32)
    table[60] = 5.0  # March 1's slot
    days = np.full((365, 1, 1), 10.0)
    got = climatestore.adjust("air_temperature_max", days, 2001, table)
    assert got[59, 0, 0] == 15.0 and got[58, 0, 0] == 10.0  # March 1 is day 59 of a common year
    rh = climatestore.adjust("relative_humidity_max", np.full((365, 1, 1), 97.0), 2001, table + 5.0)
    assert rh.max() == 100.0
    pairs = {"air_temperature_min": np.array([5.0, 9.0]), "air_temperature_max": np.array([8.0, 8.0])}
    climatestore._pairs(pairs)
    np.testing.assert_array_equal(pairs["air_temperature_min"], [5.0, 8.0])


# --- Fit, derive, read --------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _built(tmp_path_factory):
    """Kept gridMET files for 1999 and the overlap 2016–2017; the archive's 2016–2017 warmer by 1.5 °C in the
    maximum, 0.9 of the rain, 0.85 of the shortwave, 0.64 of the wind and 0.83 of ET0."""
    tmp_path = tmp_path_factory.mktemp("kept")
    lat, lon = source_grid(WINDOW)
    for year in (1999, 2016, 2017):
        write_kept(tmp_path, year, gridmet_fields(year, (lat.size, lon.size)), lat, lon)
    for year in (2016, 2017):
        g = {s.daily: gridmet.regrid(gridmet.read(gridmet.path(tmp_path, s.name, year), s.name), WINDOW)
             for s in gridmet.SOURCES}  # fmt: skip
        write_archive(
            tmp_path,
            year,
            {
                "air_temperature_max": g["air_temperature_max"] + 1.5,
                "air_temperature_min": g["air_temperature_min"],
                "relative_humidity_max": g["relative_humidity_max"],
                "relative_humidity_min": g["relative_humidity_min"],
                "precipitation_sum": 0.9 * g["precipitation_sum"],
                "shortwave_radiation_sum": 0.85 * g["shortwave_radiation_sum"],
                "wind_speed_mean": 0.64 * g["wind_speed_mean"],
                "et0_sum": 0.83 * g["et0_sum"],
            },
        )
    return tmp_path


@pytest.fixture
def kept(_built, tmp_path):
    shutil.copytree(_built, tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_a_derived_year_is_on_the_archives_basis(kept):
    climatestore.fit(kept, WINDOW, [2016, 2017])
    assert climatestore.status(kept, 1999) == "missing"
    names = climatestore.derive(kept, 1999, WINDOW)
    assert set(names) == {s.daily for s in gridmet.SOURCES}
    assert climatestore.status(kept, 1999) is None
    j, i = 1003, 1402
    got = climatestore.reader(kept).read(j, i, date(1999, 1, 1), date(1999, 12, 31), names)
    assert got is not None
    g = {s.daily: gridmet.regrid(gridmet.read(gridmet.path(kept, s.name, 1999), s.name), WINDOW)
         for s in gridmet.SOURCES}  # fmt: skip
    y, x = WINDOW.local(j, i)
    np.testing.assert_allclose(got["air_temperature_max"], g["air_temperature_max"][:, y, x] + 1.5, atol=0.06)
    np.testing.assert_allclose(got["air_temperature_min"], g["air_temperature_min"][:, y, x], atol=0.06)
    rainy = g["precipitation_sum"][:, y, x] > 0
    np.testing.assert_allclose(got["precipitation_sum"][rainy] / g["precipitation_sum"][rainy, y, x], 0.9, atol=0.01)
    np.testing.assert_allclose(got["shortwave_radiation_sum"], 0.85 * g["shortwave_radiation_sum"][:, y, x], atol=0.02)
    np.testing.assert_allclose(got["wind_speed_mean"], 0.64 * g["wind_speed_mean"][:, y, x], atol=0.06)
    np.testing.assert_allclose(got["et0_sum"], 0.83 * g["et0_sum"][:, y, x], atol=0.02)
    assert len(got["air_temperature_max"]) == 365


def test_a_year_goes_out_of_date_when_the_fit_or_its_files_change(kept):
    climatestore.fit(kept, WINDOW, [2016, 2017])
    climatestore.derive(kept, 1999, WINDOW)
    climatestore.fit(kept, WINDOW, [2016, 2017])
    assert climatestore.status(kept, 1999) == "out of date: the fit changed"
    climatestore.derive(kept, 1999, WINDOW)
    file = gridmet.path(kept, "pr", 1999)
    os.utime(file, (file.stat().st_atime, file.stat().st_mtime + 10))
    assert climatestore.status(kept, 1999) == "out of date: gridMET's files changed"


def test_without_a_fit_a_year_is_derived_as_gridmet_gives_it(kept):
    climatestore.derive(kept, 1999, WINDOW)
    got = climatestore.reader(kept).read(1003, 1402, date(1999, 7, 1), date(1999, 7, 1), ["air_temperature_max"])
    g = gridmet.regrid(gridmet.read(gridmet.path(kept, "tmmx", 1999), "tmmx"), WINDOW)
    assert got is not None
    assert got["air_temperature_max"][0] == pytest.approx(g[181, *WINDOW.local(1003, 1402)], abs=0.06)


def test_values_left_out_are_missing_in_their_years(kept, monkeypatch):
    monkeypatch.setattr(climatestore, "LEFT_OUT", {"air_temperature_max": (1999,)})
    climatestore.derive(kept, 1999, WINDOW)
    names = ["air_temperature_max", "air_temperature_min"]
    got = climatestore.reader(kept).read(1003, 1402, date(1999, 7, 1), date(1999, 7, 31), names)
    assert got is not None
    assert np.isnan(got["air_temperature_max"]).all() and np.isfinite(got["air_temperature_min"]).all()
    assert climatestore.LEFT_OUT  # the real table is in force otherwise
    assert climatestore.status(kept, 1999) is None


def test_a_fit_from_another_window_is_refused(kept):
    climatestore.fit(kept, WINDOW, [2016, 2017])
    other = Window(j0=1000, j1=1005, i0=1400, i1=1405)
    with pytest.raises(ValueError, match="another window"):
        climatestore.derive(kept, 1999, other)


def test_kept_years_skip_netcdf3(tmp_path):
    lat, lon = source_grid(WINDOW)
    write_kept(tmp_path, 2001, gridmet_fields(2001, (lat.size, lon.size)), lat, lon)
    old = gridmet.path(tmp_path, "pr", 2002)
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"CDF\x01")
    assert climatestore.kept_years(tmp_path) == {2001: [s.name for s in gridmet.SOURCES]}


def test_normals_read_years_before_the_archive_from_gridmet(kept):
    climatestore.fit(kept, WINDOW, [2016, 2017])
    climatestore.derive(kept, 1999, WINDOW)
    assert climatology.available_years(kept) == [1999, 2016, 2017]
    got = climatology.read_point(kept, 1003, 1402, [1999], ["air_temperature_max", "air_temperature_mean"])
    direct = climatestore.reader(kept).read(1003, 1402, date(1999, 1, 1), date(1999, 12, 31), ["air_temperature_max"])
    assert got["air_temperature_max"].shape == (1, SLOTS) and direct is not None
    np.testing.assert_array_equal(got["air_temperature_max"][0], layout(direct["air_temperature_max"], 1999))
    assert np.isnan(got["air_temperature_mean"]).all()  # gridMET has no daily mean: missing, not 0
