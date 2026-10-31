"""Keeping the forecast current (PLAN.md Phase 4 F): the newest long NBM run built, published and recorded, and the
published run restitched whenever the archive gains hours."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.utils import timezone

from agdata import forecast
from agdata.grid import service_window
from agdata.sources import ifs, nbm
from ops.models import IngestRecord

logger = logging.getLogger(__name__)

MAX_RUN_AGE_HOURS = 9  # a long run every 6 hours, published ~65 minutes after its cycle


def refresh_forecast(
    data_dir: Path,
    box: str,
    now: datetime,
    find_cycle: Callable[[datetime], datetime | None] = nbm.latest_complete_cycle,
    build: Callable[..., Path] = forecast.build_run,
) -> IngestRecord | None:
    """Builds and publishes the newest complete long run unless it's already current; None when there's nothing
    new. The caller holds the write lock."""
    cycle = find_cycle(now)
    if cycle is None:
        logger.warning("no complete NBM run found before %s", now)
        return None
    current = forecast.current_run(data_dir)
    if current is not None and forecast.run_info(current)["cycle"] == cycle.isoformat():
        return None
    window = service_window(box)
    started = timezone.now()
    try:
        latest = ifs.latest_path(data_dir)
        path = build(data_dir, window, cycle, soil=lambda times, w: ifs.latest_at(latest, times, w))
    except Exception as error:
        logger.exception("building the %s run failed", cycle)
        return IngestRecord.objects.create(
            kind=IngestRecord.Kind.FORECAST,
            status=IngestRecord.Status.FAILED,
            box=box,
            first_hour=cycle + timedelta(hours=1),
            hours=nbm.HORIZON_HOURS,
            started_at=started,
            finished_at=timezone.now(),
            error=repr(error),
        )
    forecast.publish(data_dir, path)
    info = forecast.run_info(path)
    failed = info.get("failed_leads", [])
    logger.info("published the %s NBM run (%d leads failed)", cycle, len(failed))
    return IngestRecord.objects.create(
        kind=IngestRecord.Kind.FORECAST,
        status=IngestRecord.Status.PARTIAL if failed else IngestRecord.Status.OK,
        box=box,
        first_hour=datetime.fromisoformat(info["first_hour"]),
        hours=nbm.HORIZON_HOURS,
        started_at=started,
        finished_at=timezone.now(),
        failed_hours=[(cycle + timedelta(hours=lead)).isoformat() for lead in failed],
        sources={"last_observed": info.get("last_observed")},
    )


def restitch_current(data_dir: Path, box: str) -> datetime | None:
    """Copies the archive's newer hours into the published run and rolls up its days again; the last observed
    hour, or None when there's no published run. The caller holds the write lock."""
    current = forecast.current_run(data_dir)
    if current is None:
        return None
    return forecast.stitch(data_dir, current, service_window(box))


def forecast_health(data_dir: Path, now: datetime) -> tuple[dict[str, Any], list[str]]:
    """The forecast section of `/up` and its problems; no run yet is "not started", as for the archive."""
    current = forecast.current_run(data_dir)
    if current is None:
        return {"state": "not started"}, []
    info = forecast.run_info(current)
    cycle = datetime.fromisoformat(info["cycle"])
    age = round((now - cycle) / timedelta(hours=1), 1)
    body = {
        "cycle": info["cycle"],
        "age_hours": age,
        "last_hour": info["last_hour"],
        "last_observed": info.get("last_observed"),
        "failed_leads": len(info.get("failed_leads", [])),
    }
    problems = [f"forecast run more than {MAX_RUN_AGE_HOURS} h old"] if age > MAX_RUN_AGE_HOURS else []
    return body, problems
