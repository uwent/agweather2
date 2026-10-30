"""The old AgWeather API (`../ag-weather`, https://agweather.cals.wisc.edu/api): daily grids on its 0.1° points,
keyed "[lat, lon]". It's a production server, so requests go one at a time with a pause.

Grids (each `?date=YYYY-MM-DD`, with `lat_range`/`lng_range` bounds):
- `weather/grid`: per point {min_temp, max_temp, avg_temp, …} (°F), from RTMA.
- `precips/grid` (`units=mm`): daily precip.
- `evapotranspirations/grid` (`units=mm`): its own ET (Diak et al. 1998), not FAO-56.
- `insolations/grid`: SSEC's GOES satellite insolation, MJ/m² per day.
"""

from datetime import date
from pathlib import Path

from agdata.clients.http import JsonClient

API = "https://agweather.cals.wisc.edu/api"

Bounds = tuple[float, float, float, float]  # south, north, west, east (degrees)


class AgWeatherV1(JsonClient):
    def __init__(self, cache_dir: Path | str | None = None, pause_s: float = 0.5, **kwargs):
        super().__init__(API, cache_dir=cache_dir, pause_s=pause_s, **kwargs)

    def grid(self, path: str, day: date, bounds: Bounds | None = None, **params: str) -> dict:
        """One grid's `data` for a day: "[lat, lon]" → value (or a dict of values). Cached by the query without its
        bounds (the cache names `scripts/compare_legacy.py` has always used)."""
        query = "&".join([f"date={day}", *(f"{k}={v}" for k, v in params.items())])
        key = f"{path}?{query}".replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-") + ".json"
        full = dict(date=str(day), **params)
        if bounds is not None:
            south, north, west, east = bounds
            full |= {"lat_range": f"{south:.1f},{north:.1f}", "lng_range": f"{west:.1f},{east:.1f}"}
        return self.get(path, params=full, cache_key=key)["data"]

    def weather(self, day: date, bounds: Bounds | None = None) -> dict:
        return self.grid("weather/grid", day, bounds)

    def precipitation_mm(self, day: date, bounds: Bounds | None = None) -> dict:
        return self.grid("precips/grid", day, bounds, units="mm")

    def evapotranspiration_mm(self, day: date, bounds: Bounds | None = None) -> dict:
        return self.grid("evapotranspirations/grid", day, bounds, units="mm")

    def insolation_mj_m2(self, day: date, bounds: Bounds | None = None) -> dict:
        """SSEC's daily insolation."""
        return self.grid("insolations/grid", day, bounds)


def point_key(latitude: float, longitude: float) -> str:
    """The old API's key for the 0.1° point nearest a location."""
    return f"[{round(latitude, 1):.1f}, {round(longitude, 1):.1f}]"
