import logging
from datetime import UTC, datetime

from django.conf import settings
from procrastinate.contrib.django import app

from agdata import pastyears
from ops.era5land import refresh_era5land
from ops.forecast import refresh_forecast, restitch_current
from ops.ifs import refresh_ifs
from ops.ingest import refresh_recent
from ops.locks import WriteLocked, write_lock

logger = logging.getLogger(__name__)

# The jobs whose work is a slow download (ERA5-Land's CDS queue, IFS's read) wait this long for the write lock to
# write it, rather than throw it away; the hourly ingest and forecast skip a turn instead (the next run catches up).
DOWNLOAD_LOCK_WAIT_S = 900


def _waiting_lock():
    return write_lock(settings.DATA_DIR, wait=DOWNLOAD_LOCK_WAIT_S)


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
        logger.warning("ingest_recent skipped: %s", error)


@app.periodic(cron="15,45 * * * *")  # cheap when nothing's new; picks up late and missed runs
@app.task(queue="ingest", queueing_lock="ingest_forecast")
def ingest_forecast(timestamp: int) -> None:
    """Builds and publishes the newest long NBM run (D38) once it's complete, if it isn't current already."""
    try:
        with write_lock(settings.DATA_DIR):
            refresh_forecast(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
    except WriteLocked as error:
        logger.warning("ingest_forecast skipped: %s", error)


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
            settings.DATA_DIR,
            settings.SERVICE_BOX,
            datetime.fromtimestamp(timestamp, UTC),
            settings.COPERNICUS_API_KEY,
            lock=_waiting_lock,
        )
        if spans:
            with _waiting_lock():
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_era5land skipped: %s", error)


@app.periodic(cron="50 * * * *")  # reads only Open-Meteo's metadata unless a new IFS run is out (every 6 hours)
@app.task(queue="ingest", queueing_lock="ingest_ifs")
def ingest_ifs(timestamp: int) -> None:
    """Reads a new IFS run's soil and snow (D52): the archive's provisional hours, and the forecast's (taken by the
    next forecast build); then restitches the published forecast."""
    try:
        if refresh_ifs(
            settings.DATA_DIR,
            settings.SERVICE_BOX,
            datetime.fromtimestamp(timestamp, UTC),
            settings.COPERNICUS_API_KEY,
            lock=_waiting_lock,
        ):
            with _waiting_lock():
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_ifs skipped: %s", error)


@app.periodic(cron="30 3 * * 1")  # Mondays: a past year settles once ERA5-Land has caught up (~5 days)
@app.task(queue="maintenance", queueing_lock="build_past_years")
def build_past_years(timestamp: int) -> None:
    """Builds the copies of past years laid out for points (`agdata.pastyears`, D63) that are missing or older
    than their daily stores. Reads only, so no write lock; not in the catch-up (a backfill's years take minutes)."""
    year = datetime.fromtimestamp(timestamp, UTC).year
    for past, reason in pastyears.stale_years(settings.DATA_DIR, before=year).items():
        try:
            pastyears.build(settings.DATA_DIR, past)
            logger.info("built the past-years copy of %s (%s)", past, reason)
        except ValueError as error:
            logger.warning("past-years copy of %s not built: %s", past, error)


# The order `manage.py jobs run all` and `jobs start` use: the archive first, then soil (IFS's provisional hours, then
# ERA5-Land's over them), then the forecast, which stitches to all of it.
CATCH_UP = (ingest_recent, ingest_ifs, ingest_era5land, ingest_forecast)
