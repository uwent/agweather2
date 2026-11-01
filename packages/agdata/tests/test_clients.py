"""The outside-service clients against recorded responses (trimmed from real ones)."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import requests

from agdata.clients.acis import Acis, precip_mm
from agdata.clients.agweather_v1 import AgWeatherV1, point_key
from agdata.clients.http import JsonClient
from agdata.clients.openmeteo_points import OpenMeteoPoints
from agdata.clients.wisconet import Wisconet

FIXTURES = Path(__file__).parent / "fixtures" / "clients"


class Response:
    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


class Recorded:
    """Serves fixture files by the first route found in the URL; keeps every request."""

    def __init__(self, routes: dict[str, object]):
        self.routes = routes
        self.calls: list[tuple[str, str, Any]] = []

    def _serve(self, method: str, url: str, payload) -> Response:
        self.calls.append((method, url, payload))
        for route, body in self.routes.items():
            if route in url:
                if isinstance(body, Response):
                    return body
                if isinstance(body, list) and body and isinstance(body[0], Response):
                    return body.pop(0)
                return Response(200, json.loads((FIXTURES / body).read_text()) if isinstance(body, str) else body)
        return Response(404, "{}")

    def get(self, url, params=None, timeout=None):
        return self._serve("GET", url, params)

    def post(self, url, json=None, timeout=None):
        return self._serve("POST", url, json)


def test_wisconet_days_are_the_days_each_stamp_closes(tmp_path):
    session = Recorded(
        {
            "/fields/": "wisconet_fields.json",
            "/measures": "wisconet_measures.json",
            "/stations/": "wisconet_stations.json",
        }
    )
    client = Wisconet(cache_dir=tmp_path, pause_s=0, session=session)  # type: ignore[arg-type]
    assert {s["station_id"] for s in client.stations()} == {"ANGO", "ALTN"}
    assert client.field_id("daily_solar_radiation_mj_tot") == 157
    days = client.daily("ANGO", "daily_solar_radiation_mj_tot", 2025)
    # Stamped 2025-01-02 06Z (midnight CST) and 2025-07-04 05Z (midnight CDT)
    assert days[date(2025, 1, 1)] == 1.5 and days[date(2025, 7, 3)] == 26.1
    measures = [c for c in session.calls if "/measures" in c[1]]
    assert measures[0][2]["fields"] == "daily_solar_radiation_mj_tot"
    # Cached: asking again sends nothing
    sent = len(session.calls)
    client.daily("ANGO", "daily_solar_radiation_mj_tot", 2025)
    assert len(session.calls) == sent
    assert (tmp_path / "ANGO_2025_daily_solar_radiation_mj_tot.json").exists()


def test_agweather_v1_grids_keep_the_cache_names_of_the_comparison_scripts(tmp_path):
    session = Recorded({"insolations/grid": "agweather_v1_insolations.json"})
    client = AgWeatherV1(cache_dir=tmp_path, pause_s=0, session=session)  # type: ignore[arg-type]
    grid = client.insolation_mj_m2(date(2025, 7, 1), bounds=(42.2, 47.6, -93.1, -85.7))
    assert grid[point_key(42.2, -93.04)] == 27.79
    params = session.calls[0][2]
    assert params == {"date": "2025-07-01", "lat_range": "42.2,47.6", "lng_range": "-93.1,-85.7"}
    assert (tmp_path / "insolations_grid_date-2025-07-01.json").exists()


def test_acis_precip_in_mm():
    session = Recorded({"MultiStnData": "acis_pcpn.json"})
    stations = Acis(session=session).precipitation_mm((-93, 42, -86, 47), date(2025, 1, 1), date(2025, 1, 4))  # type: ignore[arg-type]
    assert len(stations) == 2 and stations[0]["mm"].tolist() == [0, 0, 0, 0]  # traces are 0
    assert session.calls[0][2]["elems"] == [{"name": "pcpn"}]
    assert precip_mm("0.50") == pytest.approx(12.7) and precip_mm("1.00a") == pytest.approx(25.4)
    assert np.isnan(precip_mm("M")) and np.isnan(precip_mm("0.40A")) and np.isnan(precip_mm("S"))
    assert precip_mm("Ta") == 0 and np.isnan(precip_mm("")) and np.isnan(precip_mm("??"))


def test_open_meteo_daily_batches_locations_and_unwraps_one():
    body = {"daily": {"time": ["2025-07-01"], "shortwave_radiation_sum": [25.0]}}
    session = Recorded({"/v1/forecast": [Response(200, [body] * 25), Response(200, body)]})
    client = OpenMeteoPoints(session=session)  # type: ignore[arg-type]
    days = client.daily(
        [(43.0 + k / 100, -89.0) for k in range(26)],
        date(2025, 7, 1),
        date(2025, 7, 1),
        ["shortwave_radiation_sum"],
        model="ncep_nbm_conus",
    )
    assert len(days) == 26 and days[-1]["shortwave_radiation_sum"] == [25.0]
    assert [c[2]["latitude"].count(",") + 1 for c in session.calls] == [25, 1]
    assert session.calls[0][2]["models"] == "ncep_nbm_conus"


def test_open_meteo_hourly_asks_for_utc_unix_times_in_m_s():
    body = {"hourly": {"time": [1751328000], "shortwave_radiation": [0.0]}}
    session = Recorded({"/v1/forecast": [Response(200, body)]})
    client = OpenMeteoPoints(session=session)  # type: ignore[arg-type]
    hours = client.hourly([(43.0, -89.0)], date(2025, 7, 1), date(2025, 7, 1), ["shortwave_radiation"])
    assert hours[0]["time"] == [1751328000]
    params = session.calls[0][2]
    assert (params["timezone"], params["timeformat"], params["wind_speed_unit"]) == ("GMT", "unixtime", "ms")
    assert params["hourly"] == "shortwave_radiation"


def test_retries_on_throttling_then_gives_up_on_client_errors(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    session = Recorded(
        {"/a": [Response(429, "{}"), Response(503, "{}"), Response(200, {"ok": True})], "/b": [Response(404, "{}")]}
    )
    client = JsonClient("https://example.test", session=session)  # type: ignore[arg-type]
    assert client.get("/a") == {"ok": True} and len(session.calls) == 3
    with pytest.raises(requests.HTTPError):
        client.get("/b")
    assert len(session.calls) == 4  # a 404 isn't retried


def test_a_body_that_isnt_json_is_retried_and_never_cached(monkeypatch, tmp_path):
    monkeypatch.setattr("time.sleep", lambda s: None)
    error = "Unexpected error while streaming data: timeoutReached"  # Open-Meteo, with HTTP 200
    session = Recorded({"/a": [Response(200, error), Response(200, {"ok": True})], "/b": [Response(200, error)] * 4})
    client = JsonClient("https://example.test", cache_dir=tmp_path, session=session)  # type: ignore[arg-type]
    assert client.get("/a", cache_key="a.json") == {"ok": True} and len(session.calls) == 2
    assert json.loads((tmp_path / "a.json").read_text()) == {"ok": True}
    with pytest.raises(json.JSONDecodeError):
        client.get("/b", cache_key="b.json")
    assert not (tmp_path / "b.json").exists()


def test_a_truncated_cache_file_is_fetched_again_and_replaced(tmp_path):
    (tmp_path / "a.json").write_text('{"ok": tr')  # a crash mid-write by an older version
    session = Recorded({"/a": [Response(200, {"ok": True})]})
    client = JsonClient("https://example.test", cache_dir=tmp_path, session=session)  # type: ignore[arg-type]
    assert client.get("/a", cache_key="a.json") == {"ok": True} and len(session.calls) == 1
    assert json.loads((tmp_path / "a.json").read_text()) == {"ok": True}
    assert client.get("/a", cache_key="a.json") == {"ok": True} and len(session.calls) == 1  # now served from the file


def test_a_polite_client_pauses_after_each_answer(monkeypatch):
    pauses = []
    monkeypatch.setattr("time.sleep", pauses.append)
    session = Recorded({"/a": [Response(200, {"ok": True})]})
    JsonClient("https://example.test", pause_s=0.5, session=session).get("/a")  # type: ignore[arg-type]
    assert pauses == [0.5]


def test_agweather_v1_asks_for_millimetres_and_leaves_the_bounds_out_when_none_are_given(tmp_path):
    session = Recorded(
        {"precips/grid": "agweather_v1_insolations.json", "evapotranspirations/grid": "agweather_v1_insolations.json"}
    )
    client = AgWeatherV1(cache_dir=tmp_path, pause_s=0, session=session)  # type: ignore[arg-type]
    client.precipitation_mm(date(2025, 7, 1))
    client.evapotranspiration_mm(date(2025, 7, 1))
    assert [c[2] for c in session.calls] == [{"date": "2025-07-01", "units": "mm"}] * 2
    assert (tmp_path / "precips_grid_date-2025-07-01_units-mm.json").exists()


def test_a_wisconet_field_that_does_not_exist_is_an_error(tmp_path):
    client = Wisconet(cache_dir=tmp_path, pause_s=0, session=Recorded({"/fields/": "wisconet_fields.json"}))  # type: ignore[arg-type]
    with pytest.raises(KeyError, match="no_such_field"):
        client.field_id("no_such_field")


def hourly_blocks(*latitudes: float) -> list[dict]:
    """One block per latitude, its first time telling which latitude it was made for."""
    return [{"latitude": lat, "longitude": -89.0, "hourly": {"time": [int(lat * 100)]}} for lat in latitudes]


def test_open_meteo_points_ask_again_when_a_cached_answer_belongs_to_other_locations(tmp_path):
    session = Recorded(
        {"/v1/forecast": [Response(200, hourly_blocks(44.0, 44.5)), Response(200, hourly_blocks(43.0, 43.5))]}
    )
    client = OpenMeteoPoints(cache_dir=tmp_path, pause_s=0, session=session)  # type: ignore[arg-type]
    out = client.hourly([(43.0, -89.0), (43.5, -89.0)], date(2025, 7, 1), date(2025, 7, 1), ["temperature_2m"])
    assert [b["time"] for b in out] == [[4300], [4350]] and len(session.calls) == 2  # the first body was too far north


def test_open_meteo_points_accept_a_coastal_point_snapped_to_its_land_cell_but_not_the_wrong_count(tmp_path):
    close = Recorded({"/v1/forecast": [Response(200, hourly_blocks(43.25))]})
    client = OpenMeteoPoints(pause_s=0, session=close)  # type: ignore[arg-type]
    assert len(client.hourly([(43.0, -89.0)], date(2025, 7, 1), date(2025, 7, 1), ["temperature_2m"])) == 1
    assert len(close.calls) == 1  # 0.25° off: a snap, not a mix-up
    short = Recorded({"/v1/forecast": [Response(200, hourly_blocks(43.0)), Response(200, hourly_blocks(43.0))]})
    client = OpenMeteoPoints(cache_dir=tmp_path, pause_s=0, session=short)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="doesn't match the 2 locations"):
        client.hourly([(43.0, -89.0), (43.5, -89.0)], date(2025, 7, 1), date(2025, 7, 1), ["temperature_2m"])
