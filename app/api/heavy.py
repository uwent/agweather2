"""A per-process limit on the API's heavy computations: those that can hold gigabytes while they run.

The time limit (`api.timelimit`) answers a request after 30 seconds but can't stop its thread, and single-flight in
`layermaps.cached` (D109) stops two requests computing the same map, not different ones. A map computed on request
over the launch box took 3.0 GB (apple scab) and 5.0 GB (fire blight) at peak, for 3–4 minutes; the web container has
`WEB_MEMORY` (12 GB) over its uvicorn workers, so three such maps at once could get it killed. So a computation that
can take that much waits for one of `API_HEAVY_SLOTS` slots in its process, and a request that can't get one within
`API_HEAVY_WAIT` seconds is answered 503 (`busy`, with `Retry-After`) rather than starting beside the others. One
slot by default: two web workers then hold at most two such maps (~10 GB at the worst measured), under the 12 GB.

What counts as heavy (`layermaps.compute`, Phase 6 step 7's launch-box profile):
- a model computed on request past its stored season (`agdata.modelgrid.ON_REQUEST` over more than one block;
  `modelgrid.model_map`'s `on_request`), which reads a season of days from each cell's biofix;
- any other map whose read is HEAVY_VALUES cell-steps or more: the window's cells times the days or hours asked for
  (the running totals' two days for a degree-day sum they serve; a projection's earlier seasons counted as
  PROJECTED_STEPS). Over the launch box's 983,040 cells that's a range past ~50 days or ~50 hours (a float32 copy of
  it ~200 MB, and a statistic makes several), a season's custom degree days (1.9 GB, 0.3–1.4 s) and a projection;
  over Wisconsin's 57,820 cells no plain range reaches it (366 days are 21 million values).
Small and quick requests (a day's map, a tile from a kept map, points) never wait.

A slot is taken inside the map's single-flight lock, never the other way round, so a request waiting for another's
computation of the same map holds no slot, and a computation holding a slot never waits on a map's lock; nested gates
in one computation (a projection of a model computed on request) take one slot. `API_HEAVY_SLOTS=None` turns the
limit off: the precompute job (`ops.precompute`) runs with it off, since it computes maps one after another in the
worker and must not be refused.
"""

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings

from api.errors import ApiError

logger = logging.getLogger(__name__)

HEAVY_VALUES = 50_000_000  # cell-steps read: ~200 MB a float32 array
PROJECTED_STEPS = 366 * 10  # a projection reads each earlier season (up to ten) to its end
RETRY_AFTER_SECONDS = 30
BUSY = "We're computing several large maps at the moment, so we can't start this one now. Please try again in a minute or two; a request for a smaller area or a shorter period may not need to wait."

_lock = threading.Lock()
_semaphore: tuple[int, threading.BoundedSemaphore] | None = None
_held: ContextVar[bool] = ContextVar("api_heavy_held", default=False)


class Busy(ApiError):
    """No slot for a heavy computation within `API_HEAVY_WAIT` seconds: a 503 with `Retry-After`."""

    def __init__(self, what: str):
        super().__init__(code="busy", message=BUSY, status=503, retry_after=RETRY_AFTER_SECONDS)
        self.what = what


def is_heavy(cells: int, steps: int) -> bool:
    """Whether reading `steps` days or hours over `cells` cells is heavy enough to wait for a slot."""
    return cells * steps >= HEAVY_VALUES


def _slots(n: int) -> threading.BoundedSemaphore:
    global _semaphore
    with _lock:
        if _semaphore is None or _semaphore[0] != n:  # made again if the setting changes (tests)
            _semaphore = (n, threading.BoundedSemaphore(n))
        return _semaphore[1]


@contextmanager
def slot(what: str) -> Iterator[None]:
    """Runs the block holding one of the process's `API_HEAVY_SLOTS` slots, waiting up to `API_HEAVY_WAIT` seconds
    for one; raises `Busy` if none frees. `what` names the computation for the log. A no-op if the limit is off or
    this computation already holds a slot."""
    n = settings.API_HEAVY_SLOTS
    if n is None or _held.get():
        yield
        return
    semaphore = _slots(n)
    if not semaphore.acquire(timeout=settings.API_HEAVY_WAIT):
        raise Busy(what)
    token = _held.set(True)
    try:
        yield
    finally:
        _held.reset(token)
        semaphore.release()
