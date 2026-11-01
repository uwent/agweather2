"""A JSON client for outside services: optional response caching by key, a pause after each live request (some
services are throttled or are production servers), and retries with backoff on throttling, server errors and
bodies that aren't JSON."""

import json
import time
from pathlib import Path
from typing import Any

import requests


class JsonClient:
    def __init__(
        self,
        base_url: str,
        cache_dir: Path | str | None = None,
        pause_s: float = 0.0,
        timeout_s: float = 60,
        attempts: int = 4,
        backoff_s: float = 10,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.pause_s = pause_s
        self.timeout_s = timeout_s
        self.attempts = attempts
        self.backoff_s = backoff_s
        self.session = session or requests.Session()

    def get(self, path: str, params: dict | None = None, cache_key: str | None = None, refresh: bool = False) -> Any:
        """The JSON response, from the cache if it has `cache_key` (unless `refresh`)."""
        return self._cached(
            cache_key, lambda: self.session.get(self._url(path), params=params, timeout=self.timeout_s), refresh
        )

    def post(self, path: str, body: Any, cache_key: str | None = None) -> Any:
        return self._cached(cache_key, lambda: self.session.post(self._url(path), json=body, timeout=self.timeout_s))

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _cached(self, cache_key: str | None, send, refresh: bool = False) -> Any:
        path = self.cache_dir / cache_key if self.cache_dir is not None and cache_key else None
        if path is not None and path.exists() and not refresh:
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                path.unlink()  # a truncated or foreign file: fetch it again
        text = self._send(send)
        data = json.loads(text)  # parsed before it's cached, so a body that isn't JSON is never kept
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(path.name + ".part")
            partial.write_text(text)
            partial.replace(path)  # atomic: a crash mid-write leaves no truncated entry
        return data

    def _send(self, send) -> str:
        for attempt in range(1, self.attempts + 1):
            try:
                response = send()
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
                response.raise_for_status()
                if self.pause_s:
                    time.sleep(self.pause_s)
                json.loads(response.text)  # Open-Meteo can answer 200 with a plain-text error mid-stream
                return response.text
            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.HTTPError,
                requests.exceptions.ChunkedEncodingError,
                json.JSONDecodeError,
            ) as error:
                retryable = not isinstance(error, requests.HTTPError) or (
                    error.response is not None
                    and (error.response.status_code == 429 or error.response.status_code >= 500)
                )
                if not retryable or attempt == self.attempts:
                    raise
                time.sleep(self.backoff_s * attempt)
        raise AssertionError("unreachable")
