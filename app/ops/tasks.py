import logging
from datetime import UTC, datetime

from django.conf import settings
from procrastinate.contrib.django import app

from ops.ingest import refresh_recent
from ops.locks import WriteLocked, write_lock

logger = logging.getLogger(__name__)


@app.periodic(cron="40 * * * *")  # after RTMA's hour is usually published
@app.task(queue="ingest", queueing_lock="ingest_recent")
def ingest_recent(timestamp: int) -> None:
    """Keeps the archive current: the last week's missing and RTMA-only hours, then their days and totals."""
    try:
        with write_lock(settings.DATA_DIR):
            refresh_recent(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
    except WriteLocked as error:
        logger.info("ingest_recent skipped: %s", error)
