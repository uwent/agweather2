"""Rendering Inertia pages with typed props, and the validation-error round trip.

Page props are Pydantic models (subclasses of `Props`), so `manage.py export_types` can generate their
TypeScript types for the Svelte pages. inertia-django leaves validation errors to the app: a failed form
redirects back with `redirect_with_errors`, and `SharedPropsMiddleware` hands them to the next page as
`errors` (keyed exactly as the form's input names, each a list of messages).
"""

from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from inertia import InertiaResponse, defer
from inertia import render as inertia_render
from pydantic import BaseModel, ConfigDict

ERRORS_SESSION_KEY = "_inertia_errors"


class Props(BaseModel):
    """Base for page and shared props; every subclass gets a generated TypeScript type."""

    model_config = ConfigDict(extra="forbid")


def render(
    request: HttpRequest,
    component: str,
    props: Props | None = None,
    deferred: dict[str, Callable[[], Props | None]] | None = None,
) -> InertiaResponse:
    """Render `frontend/pages/{component}.svelte` with `props`. Each of `deferred` (a field of `props`, declared
    with a default) is left out of the first response and computed when the page asks for it after it shows
    (Inertia's deferred props): for a prop slow to compute that the page can show without at first."""
    data = props.model_dump(mode="json") if props else {}
    for key, make in (deferred or {}).items():
        data[key] = defer(lambda make=make: _dumped(make()))
    return inertia_render(request, component, data)


def _dumped(value: Props | None) -> Any:
    return None if value is None else value.model_dump(mode="json")


def redirect_with_errors(request: HttpRequest, to: str, errors: dict[str, list[str]]) -> HttpResponseRedirect:
    request.session[ERRORS_SESSION_KEY] = errors
    return redirect(to)


def pop_errors(request: HttpRequest) -> dict[str, Any]:
    return request.session.pop(ERRORS_SESSION_KEY, {}) if hasattr(request, "session") else {}
