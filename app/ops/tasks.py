import logging
from datetime import UTC, datetime

from django.conf import settings
from procrastinate.contrib.django import app

from ops.era5land import refresh_era5land
from ops.forecast import refresh_forecast, restitch_current
from ops.ifs import refresh_ifs
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


@app.periodic(cron="20 */6 * * *")  # ERA5-Land publishes once a day; a run with nothing new asks nothing
@app.task(queue="ingest", queueing_lock="ingest_era5land")
def ingest_era5land(timestamp: int) -> None:
    """Writes ERA5-Land's soil and snow (D52) over the days that don't have it yet, then rolls them up and
    restitches the published forecast. Downloads run outside the write lock."""
    if not settings.COPERNICUS_API_KEY:
        logger.info("ingest_era5land skipped: COPERNICUS_API_KEY isn't set")
        return
    try:
        spans = refresh_era5land(
            settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC), settings.COPERNICUS_API_KEY
        )
        if spans:
            with write_lock(settings.DATA_DIR):
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.info("ingest_era5land skipped: %s", error)


@app.periodic(cron="50 * * * *")  # reads only Open-Meteo's metadata unless a new IFS run is out (every 6 hours)
@app.task(queue="ingest", queueing_lock="ingest_ifs")
def ingest_ifs(timestamp: int) -> None:
    """Reads a new IFS run's soil and snow (D52): the archive's provisional hours, and the forecast's (taken by the
    next forecast build); then restitches the published forecast."""
    try:
        if refresh_ifs(
            settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC), settings.COPERNICUS_API_KEY
        ):
            with write_lock(settings.DATA_DIR):
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.info("ingest_ifs skipped: %s", error)
