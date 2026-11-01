from datetime import UTC, datetime, timedelta

import pytest
from django.contrib import admin

from ops.admin import IngestRecordAdmin
from ops.models import IngestRecord


@pytest.fixture
def record():
    start = datetime(2025, 7, 1, 12, tzinfo=UTC)
    return IngestRecord(
        kind="hourly",
        status="partial",
        box="b",
        first_hour=start,
        hours=24,
        started_at=start,
        finished_at=start + timedelta(seconds=125),
        failed_hours=["a", "b", "c"],
    )


def test_the_list_shows_failed_hours_counted_and_the_run_time_in_seconds(record):
    model_admin = IngestRecordAdmin(IngestRecord, admin.site)
    assert model_admin.failed_count(record) == 3
    assert model_admin.duration(record) == "125 s"


def test_run_history_is_read_only(rf):
    model_admin = IngestRecordAdmin(IngestRecord, admin.site)
    request = rf.get("/")
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_change_permission(request, obj=IngestRecord()) is False
    assert set(model_admin.readonly_fields) >= {"status", "failed_hours", "finished_at"}
