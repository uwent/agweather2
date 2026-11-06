"""Unknown query parameters are an error (Ben, 2026-11-06), not silently dropped.

Ninja passes an endpoint only the parameters it declares and drops the rest, so a mistyped or v1-style name
(`start_date`) was ignored and the answer looked right but wasn't what was asked for. `install(api)` wraps every
operation so that, before it runs, each query parameter is checked against what the endpoint takes:

- what it declares (its query schemas' fields and aliases, read once per operation);
- what every endpoint takes: v1's names for a point (`lon`, `long`, `longitude`, `latitude`), a catalog variable's
  name to set its unit (`precipitation=mm`, `api.envelope.unit_overrides`), and `_`, the cache-buster some
  JavaScript libraries add;
- what it reads from `request.GET` itself: a model's options and its crop model's (`api.runs`), on a model layer's
  map the same plus those a map refuses with a pointer to the point endpoint (`layermaps.model_request`), and on a
  POST the fields a CSV body takes from the query (`routes.models.POST_FIELDS`).

Anything else is a 422 `unknown_parameter` per name, suggesting the nearest it takes (v1's names by their v2 ones).
An unknown model or layer is left to the endpoint, so its 404 comes first.
"""

import difflib
from collections.abc import Callable, Iterable
from functools import cache
from typing import Any

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.operation import Operation

from agmodels.registry import all_models
from agmodels.registry import model as find_model

ALWAYS = frozenset({"latitude", "lon", "long", "longitude", "_"})
# v1's names, and what a v1 caller means by them here
V1_NAMES = {"start_date": "start", "end_date": "end", "models": "dd", "base_temp": "base", "upper_temp": "upper"}


def install(api: NinjaAPI) -> None:
    """Check every operation's query parameters before it runs (call after the routers are added)."""
    # The routers as mounted: Ninja clones each router's operations when it binds them, and serves the clones
    for router in api._get_bound_routers():
        for view in router.path_operations.values():
            for operation in view.operations:
                operation.run = _checked(api, operation, operation.run)  # type: ignore[method-assign]


def _checked(api: NinjaAPI, operation: Operation, run: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    declared = _declared(operation)
    path = operation.path
    post = "POST" in operation.methods

    def checked(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        extra = _dynamic(path, post, kwargs)
        if extra is not None:
            unknown = [name for name in request.GET if name not in declared and not _taken(name, extra)]
            if unknown:
                from api.envelope import error_response

                takes = declared | extra
                return error_response(request, [_item(name, takes) for name in unknown], status=422)
        return run(request, *args, **kwargs)

    return checked


def _declared(operation: Operation) -> frozenset[str]:
    """The query names an operation's schemas declare, with their aliases."""
    names: set[str] = set()
    for model in operation.models:
        if getattr(model, "__ninja_param_source__", None) != "query":
            continue
        for name, field in model.model_fields.items():
            inner = getattr(field.annotation, "model_fields", None)
            fields = inner.items() if inner is not None else [(name, field)]
            for sub_name, sub in fields:
                names.add(sub.alias or sub_name)
    return frozenset(names)


def _taken(name: str, extra: frozenset[str]) -> bool:
    if name in ALWAYS or name in extra:
        return True
    from api.envelope import find_variable

    try:
        find_variable(name)  # a unit for one variable (`precipitation=mm`)
    except KeyError:
        return False
    return True


def _dynamic(path: str, post: bool, kwargs: dict[str, Any]) -> frozenset[str] | None:
    """What an endpoint reads from the query beyond what it declares; None to leave the request to the endpoint
    (an unknown model or layer, which it answers with a 404)."""
    if post and "/models/" in f"/{path}":
        from api.routes.models import POST_FIELDS

        model_id = kwargs.get("model_id")
        if model_id is not None and model_id not in all_models():
            return None
        options = _model_options(model_id) if model_id is not None else _every_option()
        return frozenset(POST_FIELDS) | options
    if "model_id" in kwargs:
        return None if kwargs["model_id"] not in all_models() else _model_options(kwargs["model_id"])
    if path.lstrip("/") in ("models/run", "risk"):
        return _every_option()
    if "layer" in kwargs:
        return _layer_options(kwargs["layer"])
    return frozenset()


@cache
def _model_options(model_id: str) -> frozenset[str]:
    """A model's options and its crop model's (`api.runs.plan` reads both)."""
    from agdata.planting import planting_crop

    spec = find_model(model_id).SPEC
    names = {o.name for o in spec.options}
    crop = planting_crop(spec)
    if crop is not None and crop[0] != spec.id:
        names |= {o.name for o in find_model(crop[0]).SPEC.options}
    return frozenset(names)


@cache
def _every_option() -> frozenset[str]:
    """Every model's options: requests for several models apply each option to the models that have it."""
    return frozenset(name for model_id in all_models() for name in _model_options(model_id))


@cache
def _layer_options(layer_id: str) -> frozenset[str] | None:
    from agdata.layers import LAYERS
    from agdata.modelgrid import PLACE_OPTIONS
    from api.layermaps import POINT_ONLY

    layer = LAYERS.get(layer_id)
    if layer is None:
        return None
    if layer.source != "model":
        return frozenset()
    return _model_options(layer_id) | frozenset(POINT_ONLY) | frozenset(PLACE_OPTIONS)


def _item(name: str, takes: Iterable[str]) -> dict[str, Any]:
    suggestion = V1_NAMES.get(name)
    if suggestion is None or suggestion not in takes:
        close = difflib.get_close_matches(name, sorted(takes), n=1, cutoff=0.75)
        suggestion = close[0] if close else None
    hint = f" Did you mean {suggestion}?" if suggestion else ""
    return {
        "code": "unknown_parameter",
        "param": name,
        "message": f"This request doesn't take a parameter named {name}.{hint} The parameters each request takes "
        "are listed at /api/v2/docs.",
    }
