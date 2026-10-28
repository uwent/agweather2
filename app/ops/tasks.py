import logging

from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


@app.periodic(cron="*/15 * * * *")
@app.task(queue="ops")
def heartbeat(timestamp: int) -> None:
    """Shows the worker and its scheduler are running; replaced by the health check in Phase 2."""
    logger.info("heartbeat %s", timestamp)
