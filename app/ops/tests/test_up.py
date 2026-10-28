import pytest


@pytest.mark.django_db
def test_up_reports_ok(client):
    response = client.get("/up")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "dev", "database": "ok"}


def test_heartbeat_task_is_periodic():
    from procrastinate.contrib.django import app

    from ops import tasks

    assert tasks.heartbeat.name == "ops.tasks.heartbeat"
    assert any(p.task.name == tasks.heartbeat.name for p in app.periodic_registry.periodic_tasks.values())
