"""Open-Meteo's daily values for many locations (25 a request), for checks against other sources. The archive's
own Open-Meteo path is hourly (`agdata.sources.openmeteo`, cached in Postgres); this caches responses as files."""

from datetime import date

from agdata.clients.http import JsonClient
from agdata.sources.openmeteo import HOSTS

BATCH = 25


class OpenMeteoDaily(JsonClient):
    def __init__(self, endpoint: str = "historical", api_key: str | None = None, cache_dir=None, **kwargs):
        host, path = HOSTS[endpoint]
        kwargs.setdefault("timeout_s", 120)
        super().__init__(f"https://{'customer-' if api_key else ''}{host}", cache_dir=cache_dir, **kwargs)
        self.path, self.api_key, self.endpoint = path, api_key, endpoint

    def daily(
        self,
        locations: list[tuple[float, float]],
        first: date,
        last: date,
        variables: list[str],
        model: str | None = None,
        timezone: str = "America/Chicago",
    ) -> list[dict[str, list]]:
        """Each location's `daily` block ({time, variable: [...]}), in order, a batch of 25 per request."""
        out: list[dict[str, list]] = []
        for k in range(0, len(locations), BATCH):
            batch = locations[k : k + BATCH]
            params = {
                "latitude": ",".join(f"{lat:.4f}" for lat, _ in batch),
                "longitude": ",".join(f"{lon:.4f}" for _, lon in batch),
                "start_date": str(first),
                "end_date": str(last),
                "daily": ",".join(variables),
                "timezone": timezone,
            }
            if model:
                params["models"] = model
            key = "_".join(
                ["openmeteo", self.endpoint, model or "default", ",".join(variables), str(first), str(last)]
                + [f"{lat:.4f},{lon:.4f}" for lat, lon in batch[:1]]
                + [f"n{len(batch)}"]
            )
            body = self.get(
                self.path, params=params | ({"apikey": self.api_key} if self.api_key else {}), cache_key=key + ".json"
            )
            bodies = body if isinstance(body, list) else [body]  # one location comes back as an object
            out += [b["daily"] for b in bodies]
        return out
