"""The per-process limit on heavy computations (`api.heavy`): a few slots, a 503 `busy` past a short wait, none held
while waiting for another request's computation of the same map, and none for the precompute job."""

import logging
import threading
import time

import pytest

from agdata import tiles
from agdata.grid import service_window
from api import heavy, layermaps
from api.tests.fixture_archive import POINT
from ops import precompute

LAT, LNG = POINT
Z = 8
X, Y = tiles.tile_of(LNG, LAT, Z)


def _held_elsewhere(release: threading.Event) -> threading.Thread:
    """A thread holding the process's one slot until `release` is set."""
    taken = threading.Event()

    def hold():
        with heavy.slot("held by the test"):
            taken.set()
            release.wait(10)

    thread = threading.Thread(target=hold)
    thread.start()
    assert taken.wait(5)
    return thread


def test_what_is_heavy():
    launch = service_window("upper_midwest").size
    wisconsin = service_window("wisconsin").size
    assert heavy.is_heavy(cells=launch, steps=51) and not heavy.is_heavy(cells=launch, steps=50)
    assert heavy.is_heavy(cells=launch, steps=744)  # a month of hours
    assert not heavy.is_heavy(cells=wisconsin, steps=366) and not heavy.is_heavy(cells=wisconsin, steps=744)


def test_a_slot_is_waited_for_then_refused(settings):
    settings.API_HEAVY_SLOTS = 1
    settings.API_HEAVY_WAIT = 0.1
    release = threading.Event()
    thread = _held_elsewhere(release)
    try:
        started = time.perf_counter()
        with pytest.raises(heavy.Busy) as refused, heavy.slot("second"):
            pass
        assert 0.1 <= time.perf_counter() - started < 1
        assert refused.value.status == 503 and refused.value.retry_after == heavy.RETRY_AFTER_SECONDS
        assert refused.value.what == "second"
    finally:
        release.set()
        thread.join()
    with heavy.slot("now free"):
        pass


def test_a_computation_holding_a_slot_takes_no_second_and_off_means_no_limit(settings):
    settings.API_HEAVY_SLOTS = 1
    settings.API_HEAVY_WAIT = 0.1
    with heavy.slot("outer"), heavy.slot("a projection of a model computed on request"):
        pass
    settings.API_HEAVY_SLOTS = None
    release = threading.Event()
    thread = _held_elsewhere(release)
    try:
        with heavy.slot("unlimited"):
            pass
    finally:
        release.set()
        thread.join()


def test_a_heavy_map_is_refused_while_the_slots_are_taken(client, archive, settings, monkeypatch, caplog):
    settings.API_HEAVY_SLOTS = 1
    settings.API_HEAVY_WAIT = 0.1
    monkeypatch.setattr(heavy, "HEAVY_VALUES", 1)  # the fixture's few cells count as heavy
    caplog.set_level(logging.WARNING, logger="api.heavy")
    path = "/api/v2/grids/air_temperature_max"
    release = threading.Event()
    thread = _held_elsewhere(release)
    try:
        response = client.get(path, {"date": "2025-07-05"})
    finally:
        release.set()
        thread.join()
    assert response.status_code == 503
    assert response["Retry-After"] == str(heavy.RETRY_AFTER_SECONDS)
    (error,) = response.json()["errors"]
    assert error == {"code": "busy", "param": None, "message": heavy.BUSY}
    (logged,) = [r.getMessage() for r in caplog.records if r.name == "api.heavy"]
    assert "no slot" in logged and f"{path}?date=2025-07-05" in logged and "air_temperature_max" in logged
    assert client.get(path, {"date": "2025-07-05"}).status_code == 200  # once the slot is free


def test_a_request_waiting_for_the_same_map_holds_no_slot(client, archive, settings, monkeypatch):
    """The second request waits on the map's own lock (D109) for longer than API_HEAVY_WAIT, and takes the first's
    map: had it taken a slot first, or the first waited on a slot while holding the map's lock, one would be refused."""
    settings.API_HEAVY_SLOTS = 1
    settings.API_HEAVY_WAIT = 0.1
    settings.MAP_CACHE_DIR = None
    layermaps._maps.clear()
    monkeypatch.setattr(heavy, "HEAVY_VALUES", 1)
    compute = layermaps._compute
    calls: list[float] = []

    def slow(*args, **kwargs):
        calls.append(time.perf_counter())
        time.sleep(0.5)
        return compute(*args, **kwargs)

    monkeypatch.setattr(layermaps, "_compute", slow)
    path = f"/api/v2/tiles/air_temperature_max/2025-07-05/{Z}/{X}/{Y}.png"
    statuses: list[int] = []
    first = threading.Thread(target=lambda: statuses.append(client.get(path).status_code))
    first.start()
    for _ in range(100):
        if calls:
            break
        time.sleep(0.01)
    statuses.append(client.get(path).status_code)
    first.join()
    assert statuses == [200, 200] and len(calls) == 1


def test_the_precompute_job_runs_without_the_limit(settings, monkeypatch):
    settings.API_HEAVY_SLOTS = 1
    seen: list[object] = []
    monkeypatch.setattr(precompute, "_run", lambda: seen.append(settings.API_HEAVY_SLOTS) or precompute.Done())
    precompute.run()
    assert seen == [None]
