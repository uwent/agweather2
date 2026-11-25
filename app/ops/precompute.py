"""The maps computed ahead of visitors (Phase 6 step 7 D5; Ben, 2026-11-25): every model's layer and the main weather
layers, under their default settings, so anyone's first map is a read from the disk cache (`api.layermaps`); a reader
who changes a setting may wait for it (~0.3–2 s over the launch box).

This is the one list of what's precomputed. The job (`ops.tasks.precompute_maps`) runs after the crop stages and
stored seasons that follow each update and each new forecast run, and asks for each map through the API's own tile
route in process, so a map is kept under exactly the key a visitor's request looks up.
"""

import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.test import Client

from agdata import coverage
from agdata.grid import NDFD
from agdata.layers import LAYERS
from agmodels.registry import all_models
from ops.latency import tile_of

logger = logging.getLogger(__name__)

# The weather maps a reader opens first: each day's temperatures, moisture, rain, sun, ET0, soil and snow, and the
# season's growing degree days and rain
WEATHER = (
    "air_temperature_min",
    "air_temperature_max",
    "air_temperature_mean",
    "dew_point_mean",
    "relative_humidity_mean",
    "wind_speed_mean",
    "precipitation_sum",
    "shortwave_radiation_sum",
    "et0_sum",
    "soil_temperature_10cm_mean",
    "snow_depth_mean",
    "dd_modified_50_86",
    "precipitation_total",
)
# The days of each: the latest. Phase 7 (the map explorer's day steps): add the next 7 forecast days here.
DAYS = ("latest",)


def layers() -> list[str]:
    """The layers precomputed: WEATHER, then every model in use (not retired) that has a map layer."""
    models = sorted(m for m, found in all_models().items() if found.SPEC.status != "retired" and m in LAYERS)
    return [*WEATHER, *models]


@dataclass(kw_only=True)
class Done:
    maps: int = 0
    seconds: float = 0.0
    failed: dict[str, int] = field(default_factory=dict)  # `layer/day`: the status code


def run() -> Done:
    """Asks for one tile of every layer and day in the lists (computing and keeping each map); returns what it did."""
    client = Client(HTTP_HOST=_host())
    extent = coverage.of(settings.SERVICE_BOX).extent
    lat, lng = NDFD.latlon((extent.j0 + extent.j1) // 2, (extent.i0 + extent.i1) // 2)
    z, x, y = tile_of(float(lat), float(lng))
    done = Done()
    started = time.perf_counter()
    for layer in layers():
        for day in DAYS:
            response = client.get(f"/api/v2/tiles/{layer}/{day}/{z}/{x}/{y}.png")
            if response.status_code == 200:
                done.maps += 1
            else:
                done.failed[f"{layer}/{day}"] = response.status_code
    done.seconds = time.perf_counter() - started
    return done


def _host() -> str:
    """A host the app accepts, for the in-process requests (production lists only its own names)."""
    for host in settings.ALLOWED_HOSTS:
        if host not in ("*", "") and "*" not in host:
            return host.lstrip(".")
    return "localhost"
