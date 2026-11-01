"""URMA, RTMA and HRRR hours read from files in a fake bucket (no network): units, naming eras, missing files."""

from datetime import UTC, datetime

import numpy as np
import pytest
import requests

from agdata.grid import Window
from agdata.sources import hrrr
from agdata.sources.rtma import RTMA
from agdata.sources.urma import URMA

WINDOW = Window(j0=900, j1=904, i0=1400, i1=1404)  # inside the fixture GRIB (NDFD rows 900-939, columns 1400-1449)
HOUR_18Z = datetime(2025, 7, 15, 18, tzinfo=UTC)
TMP = ("TMP", "2 m above ground")
DPT = ("DPT", "2 m above ground")
PRES = ("PRES", "surface")
APCP = ("APCP", "surface")


def analysis_url(when: datetime, suffix: str) -> str:
    return (
        f"https://noaa-urma-pds.s3.amazonaws.com/urma2p5.{when:%Y%m%d}/urma2p5.t{when:%H}z.2dvaranl_ndfd.grb2_{suffix}"
    )


def test_an_hour_comes_back_in_stored_units_on_the_window(bucket):
    gradient = 280 + np.arange(40)[:, None] * 0.5 + np.arange(50)[None, :] * 0.01  # K, rising to the north and east
    bucket.add(analysis_url(HOUR_18Z, "wexp"), [(TMP, "anl", gradient), (DPT, "anl", 275.15), (PRES, "anl", 98000.0)])
    window = Window(j0=902, j1=905, i0=1403, i1=1406)
    values = URMA.fetch_hour(HOUR_18Z, window, bucket, precip=False)  # type: ignore[arg-type]
    assert set(values) == {"air_temperature", "dew_point", "surface_pressure"}  # what the file holds, nothing else
    np.testing.assert_allclose(values["air_temperature"], gradient[2:5, 3:6] - 273.15, atol=0.01)  # K → °C
    np.testing.assert_allclose(values["dew_point"], 2.0, atol=0.01)
    np.testing.assert_allclose(values["surface_pressure"], 98.0, atol=0.01)  # Pa → kPa


def test_precipitation_comes_from_its_own_file_in_millimetres(bucket):
    bucket.add(analysis_url(HOUR_18Z, "wexp"), [(TMP, "anl", 293.15)])
    precip_url = "https://noaa-urma-pds.s3.amazonaws.com/urma2p5.20250715/urma2p5.2025071518.pcp_01h.wexp.grb2"
    values = URMA.fetch_hour(HOUR_18Z, WINDOW, bucket)  # type: ignore[arg-type]
    assert "precipitation" not in values  # not published yet: left out, not zero
    bucket.add(precip_url, [(APCP, "0-1 hour acc fcst", 1.5)])
    values = URMA.fetch_hour(HOUR_18Z, WINDOW, bucket)  # type: ignore[arg-type]
    np.testing.assert_allclose(values["precipitation"], 1.5, atol=0.01)
    assert URMA.fetch_precip(HOUR_18Z, WINDOW, bucket).shape == WINDOW.shape  # type: ignore[arg-type, union-attr]


def test_the_other_naming_is_tried_when_the_expected_one_is_not_there(bucket):
    bucket.add(analysis_url(HOUR_18Z, "ext"), [(TMP, "anl", 283.15)])  # a 2025 hour, filed under the old naming
    values = URMA.fetch_hour(HOUR_18Z, WINDOW, bucket, precip=False)  # type: ignore[arg-type]
    np.testing.assert_allclose(values["air_temperature"], 10.0, atol=0.01)
    assert bucket.gets[0].endswith("grb2_wexp.idx") and bucket.gets[-1].endswith("grb2_ext")


def test_an_unpublished_hour_raises_file_not_found_and_is_not_published(bucket):
    with pytest.raises(FileNotFoundError, match="no urma analysis for 2025-07-15 18Z"):
        URMA.fetch_hour(HOUR_18Z, WINDOW, bucket)  # type: ignore[arg-type]
    assert not URMA.has_hour(HOUR_18Z, bucket)  # type: ignore[arg-type]
    bucket.add(analysis_url(HOUR_18Z, "ext"), [(TMP, "anl", 283.15)])
    assert URMA.has_hour(HOUR_18Z, bucket)  # type: ignore[arg-type]


def test_a_server_error_is_not_taken_for_an_unpublished_hour(bucket):
    bucket.fail[analysis_url(HOUR_18Z, "wexp")] = 503
    with pytest.raises(requests.HTTPError):
        URMA.fetch_hour(HOUR_18Z, WINDOW, bucket)  # type: ignore[arg-type]


def test_a_product_without_hourly_precip_gives_none(bucket):
    december_2017 = datetime(2017, 12, 4, 23, tzinfo=UTC)  # URMA published 6-hour totals only until the 5th
    assert URMA.fetch_precip(december_2017, WINDOW, bucket) is None  # type: ignore[arg-type]
    assert bucket.gets == []  # no candidate files, so nothing was asked for


def test_rtma_precip_is_read_from_its_own_bucket(bucket):
    when = datetime(2016, 7, 1, 18, tzinfo=UTC)
    bucket.add(
        "https://noaa-rtma-pds.s3.amazonaws.com/rtma2p5.20160701/rtma2p5.2016070118.pcp.184.grb2", [(APCP, "", 0.8)]
    )
    np.testing.assert_allclose(RTMA.fetch_precip(when, WINDOW, bucket), 0.8, atol=0.01)  # type: ignore[arg-type]


SUBHOURLY = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.20250715/conus/hrrr.t18z.wrfsubhf01.grib2"
DSWRF = ("DSWRF", "surface")


@pytest.fixture
def hrrr_fields(monkeypatch):
    """HRRR's regridding is tested in test_regrid: here the mean of the chosen fields is what comes back."""
    monkeypatch.setattr(hrrr, "regrid", lambda values, grid, window: values[:2, :2])


def test_hrrr_shortwave_is_the_mean_of_the_four_15_minute_averages(bucket, hrrr_fields):
    averages = [
        (DSWRF, f"{a}-{a + 15} min ave fcst", w)
        for a, w in zip((0, 15, 30, 45), (100.0, 200.0, 300.0, 400.0), strict=True)
    ]
    bucket.add(SUBHOURLY, [(("TMP", "2 m above ground"), "15 min fcst", 280.0), *averages])
    values = hrrr.fetch_hour(datetime(2025, 7, 15, 19, tzinfo=UTC), WINDOW, bucket)  # the hour ending 19Z: run 18Z  # type: ignore[arg-type]
    assert set(values) == {"shortwave_radiation"}
    np.testing.assert_allclose(values["shortwave_radiation"], 250.0, rtol=1e-3)


def test_hrrr_2016_has_only_instantaneous_values_and_averages_win_when_both_exist(bucket, hrrr_fields):
    instant = [(DSWRF, f"{m} min fcst", w) for m, w in zip((15, 30, 45, 60), (0.0, 100.0, 200.0, 300.0), strict=True)]
    bucket.add(SUBHOURLY, instant)
    when = datetime(2025, 7, 15, 19, tzinfo=UTC)
    np.testing.assert_allclose(hrrr.fetch_shortwave(when, WINDOW, bucket), 150.0, rtol=1e-3)  # type: ignore[arg-type]
    both = [(DSWRF, f"{a}-{a + 15} min ave fcst", 1000.0) for a in (0, 15, 30, 45)]
    bucket.add(SUBHOURLY, instant + both)
    np.testing.assert_allclose(hrrr.fetch_shortwave(when, WINDOW, bucket), 1000.0, rtol=1e-3)  # type: ignore[arg-type]


def test_hrrr_refuses_a_file_without_four_quarter_hours(bucket, hrrr_fields):
    bucket.add(SUBHOURLY, [(DSWRF, "0-15 min ave fcst", 100.0), (DSWRF, "15-30 min ave fcst", 200.0)])
    with pytest.raises(ValueError, match="expected 4 quarter-hour DSWRF fields, found 2"):
        hrrr.fetch_shortwave(datetime(2025, 7, 15, 19, tzinfo=UTC), WINDOW, bucket)  # type: ignore[arg-type]


def test_hrrr_hour_without_a_file_has_no_shortwave(bucket):
    assert hrrr.fetch_hour(datetime(2025, 7, 15, 19, tzinfo=UTC), WINDOW, bucket) == {}  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="on the hour"):
        hrrr.fetch_hour(datetime(2025, 7, 15, 19, 30, tzinfo=UTC), WINDOW, bucket)  # type: ignore[arg-type]
