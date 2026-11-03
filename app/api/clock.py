"""The API's idea of now, in one place so tests can set it (the fixture archive's days are in 2025)."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)
