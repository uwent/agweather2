"""The write lock says who holds it, waiters leave a marker, and a polite writer (a backfill taking the lock block
after block) lets them go first."""

import os
import threading
import time

import pytest

from ops import locks
from ops.locks import WriteLocked, hold_write_lock, parse_holder, waiting, write_lock
from ops.status import lock_holder


def test_the_lock_names_its_holder_and_what_it_is(tmp_path):
    with write_lock(tmp_path, label="backfill --start 2023-01-01"):
        holder = lock_holder(tmp_path)
        assert holder is not None and holder.startswith(f"pid {os.getpid()} (backfill --start 2023-01-01, since ")
        with pytest.raises(WriteLocked) as raised:
            hold_write_lock(tmp_path)
        assert raised.value.holder == str(os.getpid())
        assert "backfill --start 2023-01-01" in raised.value.description
    assert lock_holder(tmp_path) is None


def test_a_lock_file_from_before_labels_is_a_bare_pid():
    assert str(parse_holder("477213")) == "pid 477213"
    assert str(parse_holder("")) == "pid ?"


def test_a_waiter_leaves_a_marker_while_it_waits_and_removes_it(tmp_path):
    holder = hold_write_lock(tmp_path, label="the holder")
    seen = []

    def waiter():
        with write_lock(tmp_path, wait=5, poll=0.05, label="job ingest_recent"):
            seen.append("got it")

    thread = threading.Thread(target=waiter)
    thread.start()
    deadline = time.monotonic() + 2
    while not waiting(tmp_path) and time.monotonic() < deadline:
        time.sleep(0.02)
    (marker,) = waiting(tmp_path)
    assert marker.label == "job ingest_recent"
    holder.close()
    thread.join()
    assert seen == ["got it"] and waiting(tmp_path) == []


def test_a_polite_writer_lets_a_waiter_go_first(tmp_path):
    order = []
    holder = hold_write_lock(tmp_path, label="block 1")
    waiter_started = threading.Event()

    def waiter():
        waiter_started.set()
        with write_lock(tmp_path, wait=5, poll=0.05, label="job"):
            order.append("job")
            time.sleep(0.1)

    thread = threading.Thread(target=waiter)
    thread.start()
    waiter_started.wait()
    while not waiting(tmp_path):
        time.sleep(0.01)
    holder.close()  # block 1 written; the backfill comes straight back for block 2, politely
    with write_lock(tmp_path, wait=5, poll=0.05, label="block 2", polite=True):
        order.append("block 2")
    thread.join()
    assert order == ["job", "block 2"]


def test_a_dead_processes_marker_is_cleared(tmp_path):
    folder = tmp_path / "write.waiting"
    folder.mkdir()
    (folder / "999999999.1").write_text("999999999\told\t")
    assert waiting(tmp_path) == []
    assert not any(folder.iterdir())


def test_a_polite_writer_does_not_wait_forever_on_a_stuck_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(locks, "POLITE_MAX_S", 0.1)
    monkeypatch.setattr(locks, "_alive", lambda pid: True)
    folder = tmp_path / "write.waiting"
    folder.mkdir()
    (folder / "12345.1").write_text("12345\tstuck\t")
    with write_lock(tmp_path, polite=True, poll=0.02):
        pass
