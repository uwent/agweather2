"""`manage.py climatology`'s plan (`ops.climatology`): which gridMET years the trailing 30 need, when to fit again,
what to derive and what to drop. Files are made empty or with a netCDF-4 header; nothing is downloaded."""

from contextlib import nullcontext
from datetime import date
from pathlib import Path

from agdata.grid import Window
from agdata.progress import Reporter
from agdata.sources import gridmet
from ops import climatology

WINDOW = Window(j0=1000, j1=1006, i0=1400, i1=1405)
TODAY = date(2026, 11, 11)
HDF = b"\x89HDF\r\n\x1a\n"


def archive(data_dir: Path, years) -> None:
    for year in years:
        (data_dir / "daily" / f"{year}.zarr").mkdir(parents=True)


def keep(data_dir: Path, years, header: bytes = HDF) -> None:
    for year in years:
        for s in gridmet.SOURCES:
            file = gridmet.path(data_dir, s.name, year)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(header)


def test_the_period_splits_into_gridmet_years_and_the_overlap(tmp_path):
    archive(tmp_path, range(2016, 2027))
    p = climatology.plan(tmp_path, TODAY, WINDOW)
    assert p.period == tuple(range(1996, 2026))
    assert p.normal == list(range(1996, 2016)) and p.overlap == list(range(2016, 2026))  # not 2026, not complete
    assert len(p.fetch) == 30 * len(gridmet.SOURCES)
    assert p.refit == "none yet" and sorted(p.derive) == list(range(1996, 2016))
    assert climatology.describe(p)[0] == (
        "30-year period 1996–2025: 1996–2015 from gridMET, 2016–2025 from the archive (and the fit's overlap)"
    )


def test_netcdf3_files_are_fetched_again_and_old_years_dropped(tmp_path):
    archive(tmp_path, range(2016, 2027))
    keep(tmp_path, range(1996, 2026))
    keep(tmp_path, [2020], header=b"CDF\x01")  # D2's subsetting-service files
    keep(tmp_path, [1995])
    (tmp_path / "climate" / "gridmet" / "1995.zarr").mkdir(parents=True)
    p = climatology.plan(tmp_path, TODAY, WINDOW)
    assert {y for _, y in p.fetch} == {2020}
    assert sorted({f.parent.name for f in p.drop_files}) == sorted(s.name for s in gridmet.SOURCES)
    assert {f.stem for f in p.drop_files} == {"1995"} and p.drop_years == [1995]


def test_a_new_year_moves_the_period(tmp_path):
    archive(tmp_path, range(2016, 2028))
    keep(tmp_path, range(1996, 2026))
    p = climatology.plan(tmp_path, date(2027, 1, 5), WINDOW)
    assert p.period[0] == 1997 and p.overlap[-1] == 2026
    assert {y for _, y in p.fetch} == {2026}
    assert {f.stem for f in p.drop_files} == {"1996"}


def test_a_run_reports_years_whose_files_are_missing(tmp_path):
    archive(tmp_path, range(2016, 2027))
    p = climatology.plan(tmp_path, TODAY, WINDOW)
    p.fetch = []  # as if every download failed
    report = Reporter(quiet=True)
    derived = climatology.run(tmp_path, WINDOW, p, report=report, lock=nullcontext)
    assert derived == 0
    assert {f.split(":")[0] for f in report.failures} >= {"fit", "derive 1996"}


def test_describe_runs_of_years():
    assert climatology._years([1996, 1997, 1998, 2001, 2003, 2004]) == "1996–1998, 2001, 2003–2004"
    assert climatology._years([]) == "none"


def test_a_fit_of_other_variables_is_fitted_again(tmp_path, monkeypatch):
    from agdata import climatestore

    archive(tmp_path, range(2016, 2027))
    keep(tmp_path, range(1996, 2026))
    fitted = {"version": climatestore.FIT_VERSION, "fitted": "x", "years": list(range(2016, 2026))}
    fitted |= {"window": climatestore._window_attrs(WINDOW), "names": ["air_temperature_max"]}
    monkeypatch.setattr(climatestore, "fit_attrs", lambda data_dir: fitted)
    assert climatology.plan(tmp_path, TODAY, WINDOW).refit == "the variables adjusted changed"
    fitted["names"] = sorted(climatestore.ADJUST)
    assert climatology.plan(tmp_path, TODAY, WINDOW).refit is None
