import logging
from datetime import UTC, datetime, timedelta

from django.conf import settings
from procrastinate import exceptions as procrastinate_errors
from procrastinate.contrib.django import app

from agdata import croptiers, pastyears, seasonmaps, series
from agdata.store import DAILY
from ops.era5land import refresh_era5land
from ops.forecast import refresh_forecast, restitch_current
from ops.ifs import refresh_ifs
from ops.ingest import refresh_recent, update_if_due
from ops.jobruns import JOB_MIDDLEWARE
from ops.locks import WriteLocked, write_lock
from ops.models import IngestRecord

logger = logging.getLogger(__name__)

# The jobs whose work is a slow download (ERA5-Land's CDS queue, IFS's read) wait this long for the write lock to
# write it, rather than throw it away.
DOWNLOAD_LOCK_WAIT_S = 900
# The hourly ingest and forecast wait this long, then skip a turn (the next run catches up). A backfill takes the
# lock politely (`ops.locks`), so they get it between its blocks, within a block's write (about a minute).
JOB_LOCK_WAIT_S = 600


def _waiting_lock(label: str):
    return lambda: write_lock(settings.DATA_DIR, wait=DOWNLOAD_LOCK_WAIT_S, label=label)


def queue_next(task, timestamp: int) -> bool:
    """Queues a follow-on job, unless a run of it is already waiting (its queueing lock): that run reads the data as
    it is when it starts, so it covers this one. Without this, the ingest or forecast job that finished its work
    failed on `AlreadyEnqueued` when both queued the crop stages close together."""
    try:
        task.defer(timestamp=timestamp)
    except procrastinate_errors.AlreadyEnqueued:
        logger.info("%s already queued", task.name)
        return False
    return True


@app.periodic(cron="40 * * * *")  # after RTMA's hour is usually published
@app.task(queue="ingest", queueing_lock="ingest_recent", task_middleware=JOB_MIDDLEWARE)
def ingest_recent(timestamp: int) -> None:
    """Keeps the archive current: the last week's missing and RTMA-only hours every hour; when an update is due
    (a day just over, or hours waiting six hours: D108), their days, totals and ingredients, the published forecast
    run's stitch to them, and then the crop stages."""
    now = datetime.fromtimestamp(timestamp, UTC)
    try:
        with write_lock(settings.DATA_DIR, wait=JOB_LOCK_WAIT_S, label="job ingest_recent"):
            refresh_recent(settings.DATA_DIR, settings.SERVICE_BOX, now)
            updated = update_if_due(settings.DATA_DIR, settings.SERVICE_BOX, now)
            if updated:
                restitch_current(settings.DATA_DIR, settings.SERVICE_BOX)
    except WriteLocked as error:
        logger.warning("ingest_recent skipped: %s", error)
        return
    if updated:
        queue_next(update_crop_tiers, timestamp=timestamp)


@app.periodic(cron="15,45 * * * *")  # cheap when nothing's new; picks up late and missed runs
@app.task(queue="ingest", queueing_lock="ingest_forecast", task_middleware=JOB_MIDDLEWARE)
def ingest_forecast(timestamp: int) -> None:
    """Builds and publishes the newest long NBM run (D38) once it's complete, if it isn't current already, after
    rolling up any days behind their hours (D108); then the crop stages."""
    try:
        with write_lock(settings.DATA_DIR, wait=JOB_LOCK_WAIT_S, label="job ingest_forecast"):
            record = refresh_forecast(settings.DATA_DIR, settings.SERVICE_BOX, datetime.fromtimestamp(timestamp, UTC))
    except WriteLocked as error:
        logger.warning("ingest_forecast skipped: %s", error)
        return
    if record is not None and record.status != IngestRecord.Status.FAILED:
        queue_next(update_crop_tiers, timestamp=timestamp)


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
    next forecast build). It doesn't restitch the published forecast: the run carries its own IFS soil on from the
    archive's last hour of it (`forecast.stitch`), and the next update or run takes the new hours (within six hours,
    D108), rather than six minutes of the write lock every six hours for a small change to past soil."""
    try:
        refresh_ifs(
            settings.DATA_DIR,
            settings.SERVICE_BOX,
            datetime.fromtimestamp(timestamp, UTC),
            settings.COPERNICUS_API_KEY,
            lock=_waiting_lock("job ingest_ifs"),
        )
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


@app.periodic(cron="0 6 15 * *")  # monthly; in January the 30 years roll forward (gridMET's December is in by then)
@app.task(queue="maintenance", queueing_lock="update_climatology", task_middleware=JOB_MIDDLEWARE)
def update_climatology(timestamp: int) -> None:
    """Keeps the 30-year normal's gridMET years and every period's normal maps (`ops.climatology`, D82, D84, D85):
    in January, fetches the new overlap year and drops the oldest, fits again, derives and rebuilds the maps; other
    months, retries anything a run left undone (a plan with
    nothing to do costs a directory listing). Not in the catch-up: a whole period's download takes hours."""
    from agdata.grid import service_window
    from agdata.progress import Reporter
    from ops import climatology

    window = service_window(settings.SERVICE_BOX)
    p = climatology.plan(settings.DATA_DIR, datetime.fromtimestamp(timestamp, UTC).date(), window)
    if p.nothing:
        return
    for line in climatology.describe(p):
        logger.info("climatology: %s", line)
    report = Reporter(quiet=True)
    derived = climatology.run(settings.DATA_DIR, window, p, report=report, lock=_waiting_lock("job update_climatology"))
    for failure in report.failures:
        logger.warning("climatology: %s", failure)
    logger.info("climatology: %d files fetched, %d years derived", len(p.fetch), derived)


@app.task(queue="maintenance", queueing_lock="update_crop_tiers", task_middleware=JOB_MIDDLEWARE)
def update_crop_tiers(timestamp: int) -> None:
    """Crop stages per planting tier (`agdata.croptiers`, D66, D70) and apple scab's and fire blight's seasons
    (`agdata.seasonmaps`, D109) through the archive's last day and the forecast run's, while in season. Queued by the ingest after it rolls up days and by the forecast after
    it publishes a run (D108); its own job (~15 s over Wisconsin, ~8 min on the launch box), so their lock isn't
    held for it: computed outside the lock, written inside (in waves of blocks)."""
    try:
        stores = series.Stores(["air_temperature_min"])
        years = series.archive_years(settings.DATA_DIR)
        if not years:
            return
        store = stores.get(settings.DATA_DIR, DAILY, years[-1])
        if store is None:
            return
        today = datetime.fromtimestamp(timestamp, UTC).date()
        lock = _waiting_lock("job update_crop_tiers")
        done = croptiers.refresh(settings.DATA_DIR, store.window, today, lock=lock)
        if done:
            logger.info("crop tiers written: %s", {where: len(names) for where, names in done.items()})
        seasons = seasonmaps.refresh(settings.DATA_DIR, store.window, today, lock=lock)
        if seasons:
            logger.info("disease seasons written: %s", {where: len(names) for where, names in seasons.items()})
    except WriteLocked as error:
        logger.warning("update_crop_tiers skipped: %s", error)
    queue_next(precompute_maps, timestamp=timestamp)  # the maps read what it wrote


@app.task(queue="maintenance", queueing_lock="precompute_maps", task_middleware=JOB_MIDDLEWARE)
def precompute_maps(timestamp: int) -> None:
    """The default maps of every model and the main weather layers (`ops.precompute`, step 7 D5), computed into the
    disk cache so a visitor's first map is a read. Queued after the crop stages; reads only, so no write lock."""
    from ops import precompute

    done = precompute.run()
    logger.info("precomputed %d maps in %.0f s", done.maps, done.seconds)
    if done.failed:
        logger.warning("maps not precomputed: %s", done.failed)


@app.periodic(cron="0 5 * * 1")  # Mondays, after the past-years copies: past years settle, this year's is weekly
@app.task(queue="maintenance", queueing_lock="build_downloads", task_middleware=JOB_MIDDLEWARE)
def build_downloads(timestamp: int) -> None:
    """Builds the yearly NetCDF downloads that are missing or out of date (`ops.downloads`, D69)."""
    from ops import downloads

    built = downloads.build_wanted(settings.DATA_DIR, datetime.now(UTC))
    if built:
        logger.info("downloads: %d files built (%.0f MB)", len(built), sum(e.bytes for e in built) / 1e6)


@app.periodic(cron="10 4 * * *")
@app.task(queue="maintenance", queueing_lock="housekeeping", task_middleware=JOB_MIDDLEWARE)
def housekeeping(timestamp: int) -> None:
    """Daily cleanup: deletes the API's usage counts (`ops.models.ApiUsage`, D69) older than a week, and the kept
    static map images (`api.routes.maps`, D60) unused for two weeks, with any temporary files left by a crash; then
    Open-Meteo's usage (`open_meteo_housekeeping`, D115)."""
    from api import layermaps
    from api.routes import maps
    from ops.models import ApiUsage

    deleted, _ = ApiUsage.objects.filter(minute__lt=datetime.now(UTC) - timedelta(days=7)).delete()
    if deleted:
        logger.info("API usage: %d rows older than a week deleted", deleted)
    stale = maps.prune_stale()
    if stale:
        logger.info("maps: %d unused images deleted", stale)
    old = layermaps.prune_disk()
    if old:
        logger.info("maps: %d computed maps kept over %d days deleted", old, layermaps.DISK_KEEP_DAYS)
    open_meteo_housekeeping(datetime.now(UTC))


def open_meteo_housekeeping(now: datetime) -> None:
    """Open-Meteo's usage counts (D115): rows older than two years deleted, and a warning a day while the billing
    month's use is past `OPEN_METEO_WARN_SHARE` of the plan or on pace to pass it."""
    from ops import openmeteo_usage
    from ops.models import OpenMeteoUsage

    deleted, _ = OpenMeteoUsage.objects.filter(day__lt=now.date() - timedelta(days=2 * 365)).delete()
    if deleted:
        logger.info("Open-Meteo usage: %d rows older than two years deleted", deleted)
    for warning in openmeteo_usage.warnings_for(openmeteo_usage.period_usage(now)):
        logger.warning("%s", warning)


@app.periodic(cron="25 14 * * *")  # yesterday's grid day closed at 06Z, and URMA's hours are in by now
@app.task(queue="maintenance", queueing_lock="score_forecasts", task_middleware=JOB_MIDDLEWARE)
def score_forecasts(timestamp: int) -> None:
    """Scores the kept forecast runs' days the archive has closed, and again those it has rewritten since
    (`ops.verification`, D113). Reads the stores and writes Postgres, so no write lock."""
    from ops import verification

    done = verification.score(settings.DATA_DIR, datetime.fromtimestamp(timestamp, UTC))
    if done.days:
        logger.info("verification: %d days scored (%d rows)", done.days, done.rows)


# The order `manage.py jobs run all` and `jobs start` use: the archive first, then soil (IFS's provisional hours, then
# ERA5-Land's over them), then the forecast, which stitches to all of it.
CATCH_UP = (
    ingest_recent,
    ingest_ifs,
    ingest_era5land,
    ingest_forecast,
    update_crop_tiers,
    score_forecasts,
    housekeeping,
)
