"""Wisconet (https://api.wisconet.wisc.edu/docs; OpenAPI at /openapi.json): Wisconsin's mesonet, ~80 stations
since 2023–2024. Throttled, so requests pause between them and responses are best cached.

- `stations/`: id, name, latitude, longitude, elevation, `station_timezone`, `earliest_api_date`, …
- `fields/`: every measure's `standard_name` and numeric `id` (e.g. 157 `daily_solar_radiation_mj_tot`,
  155 `60min_solar_radiation_w_avg`).
- `stations/{id}/measures?start_time=&end_time=&fields=`: rows of `collection_time` (unix seconds) and
  `measures` ([[field id, value], …]). A daily total is stamped at the local midnight that closes its day (06Z in
  CST, 05Z in CDT; checked 2026-10-30 against v2's days: r 0.95, 0.66–0.69 a day either way).
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from agdata.clients.http import JsonClient

API = "https://api.wisconet.wisc.edu/api/v1"
CENTRAL = ZoneInfo("America/Chicago")


class Wisconet(JsonClient):
    def __init__(self, cache_dir: Path | str | None = None, pause_s: float = 3.0, **kwargs):
        kwargs.setdefault("timeout_s", 120)
        kwargs.setdefault("backoff_s", 30)
        super().__init__(API, cache_dir=cache_dir, pause_s=pause_s, **kwargs)

    def stations(self) -> list[dict]:
        return self.get("stations/", cache_key="stations.json")

    def fields(self) -> list[dict]:
        return self.get("fields/", cache_key="fields.json")

    def field_id(self, standard_name: str) -> int:
        for field in self.fields():
            if field["standard_name"] == standard_name:
                return int(field["id"])
        raise KeyError(standard_name)

    def measures(
        self, station_id: str, start: datetime, end: datetime, fields: list[str], cache_key: str | None = None
    ) -> list[dict]:
        params = {"start_time": int(start.timestamp()), "end_time": int(end.timestamp()), "fields": ",".join(fields)}
        return self.get(f"stations/{station_id}/measures", params=params, cache_key=cache_key).get("data", [])

    def daily(self, station_id: str, field: str, year: int) -> dict[date, float]:
        """A daily field's values for a year at a station, by the local day each closes (cached per station-year)."""
        start = datetime(year, 1, 1, tzinfo=CENTRAL) + timedelta(hours=1)
        end = datetime(year + 1, 1, 1, tzinfo=CENTRAL) + timedelta(hours=1)
        rows = self.measures(station_id, start, end, [field], cache_key=f"{station_id}_{year}_{field}.json")
        wanted = self.field_id(field)
        out: dict[date, float] = {}
        for row in rows:
            stamp = datetime.fromtimestamp(row["collection_time"], CENTRAL)
            for field_id, value in row["measures"]:
                if field_id == wanted and value is not None:
                    out[(stamp - timedelta(hours=1)).date()] = float(value)
        return out
