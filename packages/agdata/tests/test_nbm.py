import itertools
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import requests

from agdata import interpolate
from agdata.gaps import clear_sky_shortwave_w_m2
from agdata.grid import NDFD, Window
from agdata.sources import nbm
from agdata.sources.grib import decode, parse_idx

FIXTURES = Path(__file__).parent / "fixtures"
CYCLE = datetime(2026, 10, 28, 13, tzinfo=UTC)


def test_url_and_long_cycles():
    assert nbm.url(CYCLE, 24) == (
        "https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.20261028/13/core/blend.t13z.core.f024.co.grib2"
    )
    # At 14:00Z the 13z run isn't out yet (it publishes ~65 minutes after its cycle)
    assert nbm.long_cycles_before(datetime(2026, 10, 28, 14, 0, tzinfo=UTC)) == [
        datetime(2026, 10, 28, 7, tzinfo=UTC),
        datetime(2026, 10, 28, 1, tzinfo=UTC),
    ]
    assert nbm.long_cycles_before(datetime(2026, 10, 28, 14, 10, tzinfo=UTC))[0] == CYCLE
    assert nbm.long_cycles_before(datetime(2026, 10, 28, 0, 30, tzinfo=UTC))[0] == datetime(
        2026, 10, 27, 19, tzinfo=UTC
    )


def test_only_plain_values_are_read():
    refs = parse_idx((FIXTURES / "nbm_f024.idx").read_text())
    chosen = {nbm.wanted(ref, 24): ref for ref in refs if nbm.wanted(ref, 24)}
    assert set(chosen) == {
        "air_temperature",
        "dew_point",
        "wind_speed",
        "wind_gust",
        "wind_direction",
        "cloud_cover",
        "shortwave_radiation",
        "precipitation",
    }
    assert all(ref.extra == "" for ref in chosen.values())
    assert chosen["precipitation"].detail == "23-24 hour acc fcst"  # the hour, not the 6- or 12-hour totals
    # The std dev message has the same name, level and time
    tmp = [r for r in refs if r.key == ("TMP", "2 m above ground")]
    assert [r.extra for r in tmp] == ["", "ens std dev"]
    assert {nbm.wanted(r, 24) for r in tmp} == {"air_temperature", None}


def test_a_precip_only_hour():
    refs = parse_idx((FIXTURES / "nbm_f049.idx").read_text())
    assert [nbm.wanted(ref, 49) for ref in refs] == ["precipitation"]


def test_fetch_step_converts_and_places(monkeypatch):
    field = decode((FIXTURES / "urma_tmp_small.grb2").read_bytes())  # 40 x 50 cells at NDFD (900, 1400), K
    refs = parse_idx((FIXTURES / "nbm_f024.idx").read_text())

    class FakeGrib:
        def __init__(self, url, session=None):
            assert url == nbm.url(CYCLE, 24)

        def fields_where(self, predicate):
            return [(ref, field) for ref in refs if predicate(ref) and ref.key == ("TMP", "2 m above ground")]

    monkeypatch.setattr(nbm, "RemoteGrib", FakeGrib)
    window = Window(j0=910, j1=915, i0=1410, i1=1420)
    values = nbm.fetch_step(CYCLE, 24, window)
    assert list(values) == ["air_temperature"]  # the std dev message was skipped
    np.testing.assert_allclose(values["air_temperature"], field.values[10:15, 10:20] - 273.15, atol=0.01)


def test_fetch_run_fills_the_hours_it_gets():
    window = Window(j0=900, j1=902, i0=1400, i1=1403)

    def step(cycle, lead, window, session):
        if lead == 7:
            raise requests.ConnectionError("down")
        values = {"precipitation": np.full(window.shape, 0.5)}
        if lead <= 36 or lead % 3 == 2:
            values["air_temperature"] = np.full(window.shape, float(lead))
        return values

    run = nbm.fetch_run(CYCLE, window, step=step, workers=4)
    assert run.failed == [7]
    assert run.valid_times[0] == CYCLE + timedelta(hours=1) and len(run.valid_times) == 264
    t = run.values["air_temperature"][:, 0, 0]
    assert t[0] == 1 and np.isnan(t[6]) and t[49] == 50 and np.isnan(t[50])
    assert np.isnan(run.values["precipitation"][6]).all() and run.values["precipitation"][7, 0, 0] == 0.5


def test_pchip_keeps_the_steps_and_never_overshoots():
    steps = np.arange(0, 25, 3)
    truth = 10 + 8 * np.sin(2 * np.pi * (np.arange(25) - 9) / 24)
    values = np.full((25, 2), np.nan)
    values[steps] = truth[steps, None]
    values[:, 1] = np.where(np.isnan(values[:, 1]), np.nan, 5.0)  # a flat cell stays flat
    out, filled = interpolate.pchip(values)
    np.testing.assert_array_equal(out[steps, 0], truth[steps])
    assert filled[1, 0] and not filled[3, 0]
    assert np.abs(out[:, 0] - truth).max() < 0.35  # a 3-hourly diurnal cycle
    np.testing.assert_array_equal(out[:, 1], 5.0)
    for a, b in itertools.pairwise(steps):  # each segment stays within its two steps
        seg = out[a : b + 1, 0]
        assert seg.min() >= min(seg[0], seg[-1]) - 1e-9 and seg.max() <= max(seg[0], seg[-1]) + 1e-9


def test_pchip_leaves_long_gaps_and_the_ends():
    values = np.array([np.nan, 1.0, np.nan, 3.0] + [np.nan] * 7 + [5.0, np.nan])
    out, filled = interpolate.pchip(values)
    assert np.isnan(out[0]) and np.isnan(out[-1])  # before the first step and after the last
    assert 1.0 < out[2] < 3.0
    assert np.isnan(out[4:11]).all()  # 7 missing hours: longer than a 6-hourly step's gap
    assert filled.sum() == 1


def test_direction_through_north():
    values = np.array([350.0, np.nan, 10.0, np.nan, np.nan, 100.0])
    out, filled = interpolate.direction_deg(values)
    assert out[1] == pytest.approx(0.0, abs=1e-6) or out[1] == pytest.approx(360.0)
    assert 10 < out[3] < out[4] < 100
    assert filled.tolist() == [False, True, False, True, True, False]


def test_shortwave_follows_each_days_clearness():
    cell = NDFD.cell_of(43.07, -89.40)
    assert cell is not None
    lat, lon = NDFD.latlon(*cell)
    times = np.datetime64("2026-07-01T01:00:00") + np.arange(96) * np.timedelta64(3600, "s")  # UTC
    rso = clear_sky_shortwave_w_m2(times, lat, lon, 98.0)
    day = interpolate.solar_day(times, lon)
    clearness = np.where(day == day[30], 0.5, 0.9)  # a cloudy day between clear ones
    samples = np.full(96, np.nan)
    samples[2::3] = (clearness * rso)[2::3]  # 3-hourly samples of the truth
    out, estimated = interpolate.shortwave_hourly_w_m2(times, samples, lat, lon, 98.0)
    full_days = [d for d in np.unique(day) if (day == d).sum() == 24]
    for d in full_days:
        k = day == d
        np.testing.assert_allclose(out[k], (clearness * rso)[k], rtol=1e-9)
    assert estimated[rso > 0].all()
    # A day without enough samples has no daylight values; its night is still 0
    samples[day == day[30]] = np.nan
    out, _ = interpolate.shortwave_hourly_w_m2(times, samples, lat, lon, 98.0)
    k = day == day[30]
    assert np.isnan(out[k & (rso > 0)]).all() and (out[k & (rso == 0)] == 0).all()


def test_to_hourly_keeps_dew_point_below_temperature_and_precip_unfilled():
    shape = (264, 1, 2)
    t = np.full(shape, np.nan)
    td = np.full(shape, np.nan)
    precip = np.full(shape, 0.2)
    precip[100] = np.nan
    for n in [*range(0, 48), *range(49, 192, 3), *range(196, 264, 6)]:  # indices: leads n + 1
        t[n] = 10 + 6 * np.sin(n / 3)
        td[n] = t[n] - (0.0 if n % 2 else 2.0)  # saturated at some steps
    run = nbm.Run(
        cycle=CYCLE,
        values={
            "air_temperature": t,
            "dew_point": td,
            "wind_speed": np.full(shape, 3.0),
            "wind_gust": np.full(shape, 5.0),
            "wind_direction": np.full(shape, 180.0),
            "cloud_cover": np.full(shape, 50.0),
            "shortwave_radiation": np.full(shape, np.nan),
            "precipitation": precip,
        },
    )
    lat, lon = np.full((1, 2), 43.0), np.full((1, 2), -89.4)
    hourly = nbm.to_hourly(run, lat, lon, 98.0)
    v = hourly.values
    assert (
        np.isfinite(v["air_temperature"][:263]).all() and np.isnan(v["air_temperature"][263]).all()
    )  # after the last step
    assert (v["dew_point"] <= v["air_temperature"])[np.isfinite(v["dew_point"])].all()
    assert np.isnan(v["precipitation"][100]).all() and not hourly.filled["precipitation"].any()
    assert hourly.filled["air_temperature"][48].all() and not hourly.filled["air_temperature"][47].any()


@pytest.mark.network
@pytest.mark.enable_socket
def test_a_real_long_run_over_wisconsin():
    from agdata.grid import service_window

    window = service_window("wisconsin")
    cycle = nbm.latest_complete_cycle(datetime.now(UTC))
    assert cycle is not None and cycle.hour in nbm.LONG_CYCLES
    full = nbm.fetch_step(cycle, 24, window)
    assert set(full) == {name for name, _ in nbm.FIELDS.values()} | {"precipitation"}
    assert -40 < np.nanmean(full["air_temperature"]) < 45 and np.isfinite(full["air_temperature"]).mean() > 0.95
    assert list(nbm.fetch_step(cycle, 49, window)) == ["precipitation"]


@pytest.mark.network
@pytest.mark.enable_socket
def test_a_real_hrrr_soil_forecast():
    from agdata.sources import hrrr

    cell = NDFD.cell_of(43.07, -89.40)
    assert cell is not None
    window = Window(j0=cell[0], j1=cell[0] + 2, i0=cell[1], i1=cell[1] + 2)
    run = hrrr.latest_forecast_run(datetime.now(UTC))
    assert run is not None
    times = [run + timedelta(hours=h) for h in (1, 48, 49)]
    soil = hrrr.fetch_soil_forecast(run, times, window)
    assert np.isfinite(soil["soil_temperature_10cm"][:2]).all() and np.isnan(soil["soil_temperature_10cm"][2]).all()
