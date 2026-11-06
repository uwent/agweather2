import logging
from datetime import UTC, datetime, timedelta

from django.conf import settings
from procrastinate.contrib.django import app

from agdata import croptiers, pastyears, series
from agdata.store import DAILY
from ops.era5land import refresh_era5land
from ops.forecast import refresh_forecast, restitch_current
from ops.ifs import refresh_ifs
from ops.ingest import refresh_recent
from ops.jobruns import JOB_MIDDLEWARE
from ops.locks import WriteLocked, write_lock

logger = logging.getLogger(__name__)

# The jobs whose work is a slow download (ERA5-Land's CDS queue, IFS's read) wait this long for the write lock to
# write it, rather than throw it away.
DOWNLOAD_LOCK_WAIT_S = 900
# The hourly ingest and forecast wait this long, then skip a turn (the next run catches up). A backfill takes the
# lock politely (`ops.locks`), so they get it between its blocks, within a block's write (about a minute).
JOB_LOCK_WAIT_S = 600


def _waiting_lock(label: str):
    return lambda: write_lock(settings.DATA_DIR, wait=DOWNLOAD_LOCK_WAIT_S, label=label)


@app.periodic(cron="40 * * * *")  # after RTMA's hour is usually published
@app.task(queue="ingest", queueing_lock="ingest_recent", task_middleware=JOB_MIDDLEWARE)
def ingest_recent(timestamp: int) -> None:
    """Keeps the archive current: the last week's missing and RTMA-only hours, then their days and totals, then the
    published forecast run's stitch to them."""
    try:
        with write_lock(settings.DATA_DIR, wait=JOB_LOCK_WAIT_S, label="job ingest_recent"):
            records = refresh_recent(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
            if records:
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_recent skipped: %s", error)


@app.periodic(cron="15,45 * * * *")  # cheap when nothing's new; picks up late and missed runs
@app.task(queue="ingest", queueing_lock="ingest_forecast", task_middleware=JOB_MIDDLEWARE)
def ingest_forecast(timestamp: int) -> None:
    """Builds and publishes the newest long NBM run (D38) once it's complete, if it isn't current already."""
    try:
        with write_lock(settings.DATA_DIR, wait=JOB_LOCK_WAIT_S, label="job ingest_forecast"):
            refresh_forecast(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
    except WriteLocked as error:
        logger.warning("ingest_forecast skipped: %s", error)


@app.periodic(cron="20 */6 * * *")  # ERA5-Land publishes once a day; a run with nothing new asks nothing
@app.task(queue="ingest", queueing_lock="ingest_era5land", task_middleware=JOB_MIDDLEWARE)
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
            lock=_waiting_lock("job ingest_era5land"),
        )
        if spans:
            with _waiting_lock("job ingest_era5land")():
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_era5land skipped: %s", error)


@app.periodic(cron="50 * * * *")  # reads only Open-Meteo's metadata unless a new IFS run is out (every 6 hours)
@app.task(queue="ingest", queueing_lock="ingest_ifs", task_middleware=JOB_MIDDLEWARE)
def ingest_ifs(timestamp: int) -> None:
    """Reads a new IFS run's soil and snow (D52): the archive's provisional hours, and the forecast's (taken by the
    next forecast build); then restitches the published forecast."""
    try:
        if refresh_ifs(
            settings.DATA_DIR,
            settings.SERVICE_BOX,
            datetime.fromtimestamp(timestamp, UTC),
            settings.COPERNICUS_API_KEY,
            lock=_waiting_lock("job ingest_ifs"),
        ):
            with _waiting_lock("job ingest_ifs")():
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_ifs skipped: %s", error)


@app.periodic(cron="30 3 * * 1")  # Mondays: a past year settles once ERA5-Land has caught up (~5 days)
@app.task(queue="maintenance", queueing_lock="build_past_years", task_middleware=JOB_MIDDLEWARE)
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


@app.periodic(cron="55 * * * *")  # after the hour's ingest (:40) and the forecast's (:45)
@app.task(queue="maintenance", queueing_lock="update_crop_tiers", task_middleware=JOB_MIDDLEWARE)
def update_crop_tiers(timestamp: int) -> None:
    """Crop stages per planting tier (`agdata.croptiers`, D66, D70) through the archive's last day
    and the forecast run's, while a crop is in season. Its own job (~15 s over Wisconsin, ~10× on the launch box),
    so the ingest's lock isn't held for it: computed outside the lock, written inside."""
    try:
        stores = series.Stores(["air_temperature_min"])
        years = series.archive_years(settings.DATA_DIR)
        if not years:
            return
        store = stores.get(settings.DATA_DIR, DAILY, years[-1])
        if store is None:
            return
        done = croptiers.refresh(
            settings.DATA_DIR,
            store.window,
            datetime.fromtimestamp(timestamp, UTC).date(),
            lock=_waiting_lock("job update_crop_tiers"),
        )
        if done:
            logger.info("crop tiers written: %s", {where: len(names) for where, names in done.items()})
    except WriteLocked as error:
        logger.warning("update_crop_tiers skipped: %s", error)


@app.periodic(cron="52 * * * *")  # after the hour's ingest (:40) and forecast (:45)
@app.task(queue="maintenance", queueing_lock="render_default_maps", task_middleware=JOB_MIDDLEWARE)
def render_default_maps(timestamp: int) -> None:
    """Draws the default static maps (`api.routes.maps.DEFAULT_MAPS`, D60) for the latest data, so an embedded link
    ("Today's growing degree day map") answers at once; a map whose data hasn't changed is already drawn."""
    from api.routes import maps

    drawn = {layer: ms for layer, ms in maps.render_default_maps().items() if ms}
    if drawn:
        logger.info("maps drawn: %s", {layer: f"{ms:.0f} ms" for layer, ms in drawn.items()})


@app.periodic(cron="0 5 * * 1")  # Mondays, after the past-years copies: past years settle, this year's is weekly
@app.task(queue="maintenance", queueing_lock="build_downloads", task_middleware=JOB_MIDDLEWARE)
def build_downloads(timestamp: int) -> None:
    """Builds the yearly NetCDF downloads that are missing or out of date (`ops.downloads`, D69)."""
    from ops import downloads

    built = downloads.build_wanted(settings.DATA_DIR, datetime.now(UTC))
    if built:
        logger.info("downloads: %d files built (%.0f MB)", len(built), sum(e.bytes for e in built) / 1e6)


@app.periodic(cron="10 4 * * *")
@app.task(queue="maintenance", queueing_lock="prune_api_usage", task_middleware=JOB_MIDDLEWARE)
def prune_api_usage(timestamp: int) -> None:
    """Deletes the API's usage counts (`ops.models.ApiUsage`, D69) older than a week."""
    from ops.models import ApiUsage

    deleted, _ = ApiUsage.objects.filter(minute__lt=datetime.now(UTC) - timedelta(days=7)).delete()
    if deleted:
        logger.info("API usage: %d rows older than a week deleted", deleted)


# The order `manage.py jobs run all` and `jobs start` use: the archive first, then soil (IFS's provisional hours, then
# ERA5-Land's over them), then the forecast, which stitches to all of it.
CATCH_UP = (
    ingest_recent,
    ingest_ifs,
    ingest_era5land,
    ingest_forecast,
    update_crop_tiers,
    render_default_maps,
    prune_api_usage,
)
