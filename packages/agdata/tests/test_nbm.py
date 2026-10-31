import itertools
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import requests

from agdata import calibration, interpolate
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

        def iter_fields_where(self, predicate):
            return iter([(ref, field) for ref in refs if predicate(ref) and ref.key == ("TMP", "2 m above ground")])

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
    assert estimated[
        (rso > 0) & np.isin(day, full_days)
    ].all()  # the first hours are the evening of a day without samples
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


def test_tmax_messages_are_read_for_their_window():
    from agdata.sources.grib import MessageRef

    def ref(detail, extra=""):
        return MessageRef(key=nbm.TMAX, detail=detail, extra=extra, offset=0, length=1)

    assert nbm.wanted(ref("23-35 hour max fcst"), 35) == "tmax_12h"
    assert nbm.wanted(ref("23-35 hour max fcst", "ens std dev"), 35) is None
    assert nbm.wanted(ref("11-23 hour max fcst"), 35) is None


def test_the_days_hours_reach_nbms_max_without_moving_the_windows_edges():
    from agdata import interpolate

    hours = np.arange(48, dtype=float)
    temp = 15 + 8 * np.sin(2 * np.pi * (hours - 9) / 24)  # max 23 °C at 15h
    targets = np.full(48, np.nan)
    targets[23] = 25.0  # the window ending at index 23 (hours 12..23)
    out = interpolate.reach_window_max(temp[:, None], targets[:, None])[:, 0]
    assert out[12:24].max() == pytest.approx(25.0)
    assert out[12] == temp[12] and out[23] == temp[23]  # its ends stay
    np.testing.assert_array_equal(out[:12], temp[:12])
    np.testing.assert_array_equal(out[24:], temp[24:])
    assert np.argmax(out[12:24]) == np.argmax(temp[12:24])  # the day keeps its shape


def test_a_cooler_max_lowers_the_warm_hours_only():
    from agdata import interpolate

    hours = np.arange(24, dtype=float)
    temp = 15 + 8 * np.sin(2 * np.pi * (hours - 11) / 24)  # the window (12..23) starts and ends cool
    targets = np.full(24, np.nan)
    targets[23] = 20.0
    out = interpolate.reach_window_max(temp[:, None], targets[:, None])[:, 0]
    assert out[12:24].max() == pytest.approx(20.0)
    assert out[12] == temp[12] and out[23] == temp[23]


def test_a_nights_coldest_hours_reach_a_lower_min():
    hours = np.arange(24, dtype=float)
    temp = 10 - 6 * np.cos(2 * np.pi * (hours - 6) / 24)  # min 4 °C at 6h, inside the window (0..11)
    targets = np.full(24, np.nan)
    targets[11] = temp[:12].min() - 1.5
    out = interpolate.reach_window_min(temp[:, None], targets[:, None])[:, 0]
    assert out[:12].min() == pytest.approx(targets[11])
    assert out[0] == temp[0] and out[11] == temp[11]
    assert np.argmin(out[:12]) == np.argmin(temp[:12])
    np.testing.assert_array_equal(out[12:], temp[12:])


def test_forecast_nights_are_lowered_by_the_bias_for_their_lead():
    from agdata import forecast

    cycle = datetime(2025, 7, 5, 13, tzinfo=UTC)
    times = [cycle + (n + 1) * timedelta(hours=1) for n in range(nbm.HORIZON_HOURS)]
    utc_hour = np.array([t.hour for t in times], dtype=float)
    temp = (20 + 6 * np.sin(2 * np.pi * (utc_hour - 15) / 24))[:, None, None]  # coldest at 09Z
    values = {"air_temperature": temp, "dew_point": temp - 0.2, "shortwave_radiation": np.zeros_like(temp)}
    hourly = nbm.HourlyRun(cycle=cycle, values=values, filled={})
    bias = {"lead_hours": [23, 47], "warm_bias_c": [0.5, 1.0]}
    adjustments = calibration.Adjustments(night_min=bias)
    out = forecast.adjust_hours(hourly, np.array([[43.0]]), np.array([[-89.4]]), 97.0, adjustments).values
    t, td = out["air_temperature"][:, 0, 0], out["dew_point"][:, 0, 0]
    night = lambda k: slice(k - 11, k + 1)  # noqa: E731
    first, second, last = 22, 46, 238  # 12Z on Jul 6, 7 and 15 (23, 47 and 239 hours from the cycle)
    assert t[night(first)].min() == pytest.approx(temp[night(first), 0, 0].min() - 0.5)
    assert t[night(second)].min() == pytest.approx(temp[night(second), 0, 0].min() - 1.0)
    assert t[night(last)].min() == pytest.approx(temp[night(last), 0, 0].min() - 1.0)  # held past the last lead
    days = utc_hour > 12  # 13–23Z: the windows' insides are night only
    np.testing.assert_array_equal(t[days], temp[days, 0, 0])
    assert (td <= t).all()


def test_the_max_target_is_lowered_by_the_seasons_offset():
    table = {"day_of_year": [15, 105, 196, 288], "offset_c": [-0.4, 0.3, 0.6, 0.4]}
    times = [
        datetime(2025, 7, 15, 0, tzinfo=UTC),
        datetime(2025, 1, 15, 0, tzinfo=UTC),
        datetime(2025, 12, 31, tzinfo=UTC),
    ]
    targets = calibration.max_targets(times, np.array([[30.0], [0.0], [np.nan]]), table)
    assert targets[0, 0] == pytest.approx(29.4)
    assert targets[1, 0] == pytest.approx(0.4)
    assert np.isnan(targets[2, 0])  # no TMAX at that hour
    # Around the year's end: Dec 31 (day 365) lies between Oct 15 (288) and Jan 15 (15 + 365)
    expected = 0.4 + (-0.4 - 0.4) * (365 - 288) / (380 - 288)
    assert calibration.max_offset_c([datetime(2025, 12, 31, tzinfo=UTC)], table)[0] == pytest.approx(expected)


def rh_table(maps):
    return {
        "season_day_of_year": [15, 105, 196, 288],
        "lead_group_ends": [72, 144],
        "lead_hours": [36, 108, 204],
        "rh_grid": list(range(101)),
        "map": maps.tolist(),
    }


def test_an_identity_rh_map_changes_nothing():
    grid = np.arange(101, dtype=float)
    table = rh_table(np.broadcast_to(grid, (4, 3, 24, 101)))
    cycle = datetime(2025, 7, 5, 13, tzinfo=UTC)
    times = [cycle + (n + 1) * timedelta(hours=1) for n in range(48)]
    rh = np.linspace(20, 100, 48 * 6).reshape(48, 2, 3)
    rh[3, 0, 0] = np.nan
    out = calibration.map_rh(cycle, times, np.full((2, 3), -89.4), rh, table)
    np.testing.assert_allclose(out, rh)  # NaN stays NaN


def test_rh_maps_blend_across_solar_hours_seasons_and_leads():
    grid = np.arange(101, dtype=float)
    maps = np.empty((4, 3, 24, 101))
    for s, g, h in itertools.product(range(4), range(3), range(24)):
        maps[s, g, h] = np.minimum(grid + h + 10 * s + 100 * g, 1000)  # a different shift for each map
    table = rh_table(maps)
    cycle = datetime(2025, 7, 15, 0, tzinfo=UTC)  # day 196: summer's middle
    # 36 h out (lead group 0's middle), on the meridian where the hour ending 12Z is solar noon's end
    valid = cycle + timedelta(hours=36)
    out = calibration.map_rh(cycle, [valid], np.array([0.0, -7.5]), np.array([[50.0, 50.0]]), table)[0]
    summer = 20 + 10 * (197.5 - 196) / (288 - 196)  # Jul 16 12Z is day 197.5: a little of fall (s = 3)
    # Longitude 0: solar hour 12, halfway between bins 11 and 12 (centred on 11.5 and 12.5); 7.5° W: 11.5, bin 11
    assert out[0] == pytest.approx(50 + 11.5 + summer)
    assert out[1] == pytest.approx(50 + 11.0 + summer)
    # Halfway between lead 36 and 108 the two groups mix equally
    valid = cycle + timedelta(hours=72)
    out = calibration.map_rh(cycle, [valid], np.array([0.0]), np.array([[50.0]]), table)[0]
    assert out[0] == pytest.approx(50 + 11.5 + 20 + 10 * (199 - 196) / (288 - 196) + 50)  # Jul 18 00Z
    # On New Year's Eve, between mid-October (s = 3) and mid-January (s = 0), weighted by days
    cycle = datetime(2025, 12, 30, 12, tzinfo=UTC)
    valid = cycle + timedelta(hours=36)  # Jan 1 00Z: day 1, 78 days past mid-October of 92 to mid-January
    out = calibration.map_rh(cycle, [valid], np.array([0.0]), np.array([[50.0]]), table)[0]
    w_jan = (366 - 288) / (380 - 288)
    assert out[0] == pytest.approx(50 + (23 + 0) / 2 + 30 * (1 - w_jan))  # 00Z is solar 0 at 0°: bins 23 and 0
