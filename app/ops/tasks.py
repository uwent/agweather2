import logging
from datetime import UTC, datetime

from django.conf import settings
from procrastinate.contrib.django import app

from ops.forecast import refresh_forecast, restitch_current
from ops.ingest import refresh_recent
from ops.locks import WriteLocked, write_lock

logger = logging.getLogger(__name__)


@app.periodic(cron="40 * * * *")  # after RTMA's hour is usually published
@app.task(queue="ingest", queueing_lock="ingest_recent")
def ingest_recent(timestamp: int) -> None:
    """Keeps the archive current: the last week's missing and RTMA-only hours, then their days and totals, then the
    published forecast run's stitch to them."""
    try:
        with write_lock(settings.DATA_DIR):
            records = refresh_recent(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
            if records:
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.info("ingest_recent skipped: %s", error)


@app.periodic(cron="15,45 * * * *")  # cheap when nothing's new; picks up late and missed runs
@app.task(queue="ingest", queueing_lock="ingest_forecast")
def ingest_forecast(timestamp: int) -> None:
    """Builds and publishes the newest long NBM run (D38) once it's complete, if it isn't current already."""
    try:
        with write_lock(settings.DATA_DIR):
            refresh_forecast(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
    except WriteLocked as error:
        logger.info("ingest_forecast skipped: %s", error)
