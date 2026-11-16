"""The parameters each endpoint takes, and `meta.params`: each with the value used (Ben, 2026-11-06; D90).

`meta.request` is what the answer was computed for, after defaults and normalization; `meta.params` lists every
parameter the endpoint takes, so a reader sees the defaults and what else they could send. Each value is, in order:
the value in `meta.request` (a model's options from its `options` and its crop model's), the value as given (parsed
by its field's type, or as sent if it doesn't parse), the schema's default, or null. An error response has the same
list without the first source, since nothing was computed.

The names are the operation's query schemas' fields in their declared order (the shared groups first, as each
endpoint lists them), then what the endpoint reads from the query itself: the options of the model or models asked
for (a model layer's map leaves out those it refuses, `layermaps.POINT_ONLY` and `modelgrid.PLACE_OPTIONS`), the
fields a POSTed CSV body takes from the query, and any unit given for one variable (`precipitation=mm`). v1's names
for a point (`latitude`, `long`, …) count as the canonical `lat` and `lng`.

`api.strict` sets `request.api_takes` before the endpoint runs; `api.envelope` writes `meta.params` from it.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from typing import Any

from django.http import HttpRequest
from ninja.operation import Operation
from pydantic import TypeAdapter, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from agmodels.registry import all_models
from agmodels.registry import model as find_model

# What a request may send in place of a canonical name (`api.params.ALIASES`, the other way round)
GIVEN_AS = {"lat": ("lat", "latitude"), "lng": ("lng", "lon", "long", "longitude")}


@dataclass(frozen=True, kw_only=True)
class Param:
    name: str
    default: Any = None
    adapter: TypeAdapter | None = None  # parses a value as given; None keeps it as sent
    many: bool = False  # a list: every value given for the name, not only the last

    def parse(self, given: list[str]) -> Any:
        raw: Any = given if self.many else given[-1]
        if self.adapter is None:
            return raw
        try:
            return self.adapter.validate_python(raw)
        except (ValidationError, TypeError, ValueError):
            return raw


@dataclass(frozen=True, kw_only=True)
class Takes:
    """What one request's endpoint takes: its declared parameters, then those it reads itself."""

    params: tuple[Param, ...]

    def names(self) -> frozenset[str]:
        return frozenset(p.name for p in self.params)


def declared(operation: Operation) -> tuple[Param, ...]:
    """The query parameters an operation's schemas declare, in order, with their defaults."""
    found: list[Param] = []
    for model in operation.models:
        if getattr(model, "__ninja_param_source__", None) != "query":
            continue
        for name, field in model.model_fields.items():
            inner = getattr(field.annotation, "model_fields", None)
            fields = inner.items() if inner is not None else [(name, field)]
            found += [_param(sub.alias or sub_name, sub) for sub_name, sub in fields]
    return tuple(found)


def _param(name: str, field: FieldInfo) -> Param:
    default = field.get_default(call_default_factory=True)
    many = _is_list(field.annotation)
    try:
        adapter = TypeAdapter(field.annotation) if field.annotation is not None else None
    except Exception:  # an annotation pydantic can't adapt alone (a forward reference): keep values as sent
        adapter = None
    return Param(name=name, default=None if default is PydanticUndefined else default, adapter=adapter, many=many)


def _is_list(annotation: Any) -> bool:
    origin = getattr(annotation, "__origin__", None)
    if origin in (list, tuple, set, frozenset):
        return True
    return any(_is_list(a) for a in getattr(annotation, "__args__", ()) if a is not type(None))


def for_request(base: tuple[Param, ...], path: str, post: bool, kwargs: dict[str, Any], request: HttpRequest) -> Takes:
    """What this request's endpoint takes: `base` (its declared parameters) and what it reads from the query."""
    known = {p.name for p in base}
    extra: list[Param] = []
    if post and "/models/" in f"/{path}":
        from api.routes.models import POST_FIELDS

        extra += [Param(name=n) for n in POST_FIELDS]
    extra += _options(path, kwargs, request)
    from api.envelope import find_variable

    for name in request.GET:  # a unit for one variable
        try:
            find_variable(name)
        except KeyError:
            continue
        extra.append(Param(name=name))
    seen = set(known)
    added = []
    for p in extra:
        if p.name not in seen:
            seen.add(p.name)
            added.append(p)
    return Takes(params=(*base, *added))


def _options(path: str, kwargs: dict[str, Any], request: HttpRequest) -> list[Param]:
    """The model options this request's endpoint reads: its model's (and its crop model's), or every model's asked
    for; on a model layer, those a map takes."""
    if "model_id" in kwargs:
        model_id = kwargs["model_id"]
        return list(_model_options(model_id)) if model_id in all_models() else []
    if path.lstrip("/") in ("models/run", "risk"):
        asked = [m.strip() for m in request.GET.get("models", "all").split(",") if m.strip()]
        if "all" in asked or not asked:
            asked = sorted(all_models())
        return _merged(_model_options(m) for m in asked if m in all_models())
    if "layer" in kwargs:
        return list(_layer_options(kwargs["layer"]))
    return []


@cache
def _model_options(model_id: str) -> tuple[Param, ...]:
    """A model's options and its crop model's, with their defaults (`api.runs.plan` reads both)."""
    from agdata.planting import planting_crop

    spec = find_model(model_id).SPEC
    found = [Param(name=o.name, default=o.default) for o in spec.options]
    crop = planting_crop(spec)
    if crop is not None and crop[0] != spec.id:
        names = {p.name for p in found}
        found += [
            Param(name=o.name, default=o.default) for o in find_model(crop[0]).SPEC.options if o.name not in names
        ]
    return tuple(found)


def _merged(groups: Iterable[tuple[Param, ...]]) -> list[Param]:
    """Several models' options, by name; an option whose default differs between them has none."""
    by_name: dict[str, Param] = {}
    for group in groups:
        for p in group:
            held = by_name.get(p.name)
            if held is None:
                by_name[p.name] = p
            elif held.default != p.default:
                by_name[p.name] = Param(name=p.name)
    return [by_name[n] for n in sorted(by_name)]


@cache
def _layer_options(layer_id: str) -> tuple[Param, ...]:
    from agdata.layers import LAYERS
    from agdata.modelgrid import PLACE_OPTIONS
    from api.layermaps import POINT_ONLY

    layer = LAYERS.get(layer_id)
    if layer is None or layer.source != "model":
        return ()
    refused = {*POINT_ONLY, *PLACE_OPTIONS}
    return tuple(p for p in _model_options(layer_id) if p.name not in refused)


def values(request: HttpRequest, computed: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """`meta.params`: each parameter the request's endpoint takes, with the value used (see the module's
    docstring); None if the request never reached an endpoint (an unknown path, a refusal before it ran)."""
    takes: Takes | None = getattr(request, "api_takes", None)
    if takes is None:
        return None
    found = _computed(computed or {})
    out: dict[str, Any] = {}
    for p in takes.params:
        if p.name in found:
            out[p.name] = found[p.name]
            continue
        given = [v for name in GIVEN_AS.get(p.name, (p.name,)) for v in request.GET.getlist(name)]
        out[p.name] = p.parse(given) if given else p.default
    return out


def _computed(computed: dict[str, Any]) -> dict[str, Any]:
    """`meta.request`'s values by parameter name: its own keys, and a model's options (`options`, and its crop
    model's under `crop`) as the parameters they came from."""
    found = dict(computed)
    crop = computed.get("crop")
    for options in (computed.get("options"), crop.get("options") if isinstance(crop, dict) else None):
        if isinstance(options, dict):
            for name, value in options.items():
                found.setdefault(name, value)
    return found
