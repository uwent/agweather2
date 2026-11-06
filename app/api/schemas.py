"""The envelope's shape for OpenAPI and the frontend's generated types (`bin/types` → `@/types/api`). The responses
themselves are built by `api.envelope`; these describe them."""

from typing import Any

from ninja import Schema

Value = float | int | str | bool | None


class ErrorItem(Schema):
    code: str
    param: str | None
    message: str


class ErrorMeta(Schema):
    request: dict[str, str | None]
    api_version: str
    generated_at: str
    compute_ms: int


class ErrorResponse(Schema):
    meta: ErrorMeta
    errors: list[ErrorItem]


class Cell(Schema):
    j: int
    i: int
    lat: float
    lng: float


class Location(Schema):
    lat: float
    lng: float
    cell: Cell | None
    in_box: bool
    timezone: str | None
    county: str | None
    state: str | None


class Meta(Schema):
    request: dict[str, Any]
    location: Location | None = None
    locations: list[Location] | None = None
    units: dict[str, str]
    summary: dict[str, Any]
    sources: list[str]
    warnings: list[str]
    attribution: str
    api_version: str
    generated_at: str
    compute_ms: int


class TableResponse(Schema):
    """A table: columns (default) or rows (`orient=records`)."""

    meta: Meta
    data: dict[str, list[Value]] | list[dict[str, Value]]


def responses(ok: type[Schema]) -> dict[int, type[Schema]]:
    """An endpoint's documented responses: `ok` and the error envelope (503: data being rebuilt, or Open-Meteo
    unreachable)."""
    return {200: ok, 404: ErrorResponse, 422: ErrorResponse, 500: ErrorResponse, 503: ErrorResponse}
