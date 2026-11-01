"""Open-Meteo's daily or hourly values for many locations (25 a request), for checks against other sources. The
archive's own Open-Meteo path is `agdata.sources.openmeteo` (one cell at a time, cached in Postgres); this caches
responses as files."""

from datetime import date

from agdata.clients.http import JsonClient
from agdata.sources.openmeteo import HOSTS

BATCH = 25


class OpenMeteoPoints(JsonClient):
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
        return self._blocks("daily", locations, first, last, variables, model, timezone)

    def hourly(
        self,
        locations: list[tuple[float, float]],
        first: date,
        last: date,
        variables: list[str],
        model: str | None = None,
    ) -> list[dict[str, list]]:
        """Each location's `hourly` block for UTC days first..last (times in unix seconds, each hour stamped at
        its end), in order, a batch of 25 per request. Wind in m/s."""
        return self._blocks("hourly", locations, first, last, variables, model, "GMT")

    def _blocks(self, kind, locations, first, last, variables, model, timezone) -> list[dict[str, list]]:
        """The cache key names the batch's first location and its size (and the timezone if it isn't the default),
        not every location: each cached body is checked against the batch (one block per location, each near its
        point) and fetched again if it doesn't match."""
        out: list[dict[str, list]] = []
        for k in range(0, len(locations), BATCH):
            batch = locations[k : k + BATCH]
            params = {
                "latitude": ",".join(f"{lat:.4f}" for lat, _ in batch),
                "longitude": ",".join(f"{lon:.4f}" for _, lon in batch),
                "start_date": str(first),
                "end_date": str(last),
                kind: ",".join(variables),
                "timezone": timezone,
            }
            if kind == "hourly":
                params |= {"timeformat": "unixtime", "wind_speed_unit": "ms"}
            if model:
                params["models"] = model
            key = "_".join(
                [
                    "openmeteo",
                    self.endpoint,
                    *([] if kind == "daily" else [kind]),
                    model or "default",
                    ",".join(variables),
                    str(first),
                    str(last),
                ]
                + [f"{lat:.4f},{lon:.4f}" for lat, lon in batch[:1]]
                + [f"n{len(batch)}"]
                + ([] if timezone == DEFAULT_TIMEZONE[kind] else [timezone.replace("/", "-")])
            )
            send = params | ({"apikey": self.api_key} if self.api_key else {})
            body = self.get(self.path, params=send, cache_key=key + ".json")
            if not _matches(body, batch):
                body = self.get(self.path, params=send, cache_key=key + ".json", refresh=True)
                if not _matches(body, batch):
                    raise ValueError(f"Open-Meteo's answer doesn't match the {len(batch)} locations asked for")
            bodies = body if isinstance(body, list) else [body]  # one location comes back as an object
            out += [b[kind] for b in bodies]
        return out


DEFAULT_TIMEZONE = {"daily": "America/Chicago", "hourly": "GMT"}  # the keys cached before the timezone was in them
SNAP_DEG = 0.3  # Open-Meteo answers for its own cell's centre, a coastal point for a land cell (CLAUDE.md)


def _matches(body, batch: list[tuple[float, float]]) -> bool:
    """Whether a response holds one block per location of the batch, in order, each near its point."""
    bodies = body if isinstance(body, list) else [body]
    if len(bodies) != len(batch):
        return False
    for b, (lat, lon) in zip(bodies, batch, strict=True):
        if "latitude" not in b:
            continue  # older recorded fixtures carry no coordinates
        if abs(b["latitude"] - lat) > SNAP_DEG or abs(b["longitude"] - lon) > SNAP_DEG:
            return False
    return True
