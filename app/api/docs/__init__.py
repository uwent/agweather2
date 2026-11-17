"""The API's public documentation (`/api/v2/docs`), kept apart from the code's own docstrings.

The text here is for the public, and follows CLAUDE.md's "Writing for the public"; the docstrings in `api.routes`
stay notes for developers. `apply` fills an OpenAPI schema from the files beside this module:

- `intro.md`: the API's front page (`info.description`).
- `<operation>.md`, one per endpoint, named by its operation id (`weather_daily.md`): a `# Title` line, which
  becomes the summary, and the description below it.
- `parameters.toml`: `[shared]` holds the text of parameters that mean the same thing everywhere; `[<operation>]`
  tables hold an endpoint's own parameters and any shared one whose meaning differs there. `[tags]` describes
  each group of endpoints, `[schemas]` the response schemas shown on the page; other schemas lose the docstring
  Pydantic gave them.
- `fields.toml`: a `[<Schema>]` table per response schema, the text of each of its fields. `_inherits` names the
  table of a schema it extends (`ModelDetail` → `ModelSummary`), whose text it takes for the fields it doesn't
  describe itself.

The components are listed in reading order (`reading_order`). The public schema leaves out components no operation
reaches: the query groups, which Ninja spreads into
parameters (described above). `export_types` keeps them (`public=False`).

`test_docs` checks that every operation, parameter and tag has its text and that every entry is used.
"""

import tomllib
from functools import cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent


@cache
def parameters() -> dict[str, dict[str, str]]:
    with (HERE / "parameters.toml").open("rb") as f:
        return tomllib.load(f)


@cache
def fields() -> dict[str, dict[str, str]]:
    with (HERE / "fields.toml").open("rb") as f:
        return tomllib.load(f)


def endpoint(operation_id: str) -> tuple[str, str] | None:
    """(summary, description) from `<operation_id>.md`, or None if there is no file."""
    path = HERE / f"{operation_id}.md"
    if not path.exists():
        return None
    title, _, body = path.read_text().partition("\n")
    if not title.startswith("# "):
        raise ValueError(f"{path.name} must start with a '# Title' line")
    return title[2:].strip(), body.strip()


def intro() -> str:
    return (HERE / "intro.md").read_text().strip()


def apply(schema: dict[str, Any], *, public: bool = True) -> dict[str, Any]:
    """Fill `schema` (an OpenAPI dict, changed in place and returned) with the public text; `public` drops the
    components no operation reaches."""
    text = parameters()
    shared = text.get("shared", {})
    schema["info"]["description"] = intro()
    for ops in schema.get("paths", {}).values():
        for op in ops.values():
            op_id = op["operationId"]
            found = endpoint(op_id)
            if found is not None:
                op["summary"], op["description"] = found
            own = text.get(op_id, {})
            for param in op.get("parameters", []):
                name = param["name"]
                description = own.get(name) or shared.get(name)
                if description:
                    param["description"] = description
                    param.get("schema", {}).pop("description", None)
    tags = text.get("tags", {})
    schema["tags"] = [{"name": name, "description": description} for name, description in tags.items()]
    schemas = text.get("schemas", {})
    components = schema.get("components", {}).get("schemas", {})
    for name, component in components.items():
        if name in schemas:
            component["description"] = schemas[name]
        else:
            component.pop("description", None)
        own = field_text(name)
        for field, prop in component.get("properties", {}).items():
            if field in own:
                prop["description"] = own[field]
    if public:
        keep = reached(schema)
        for name in list(components):
            if name not in keep:
                del components[name]
    order = reading_order(schema)
    rest = [name for name in components if name not in order]
    schema.setdefault("components", {})["schemas"] = {name: components[name] for name in [*order, *rest]}
    return schema


ENVELOPE = ("TableResponse", "ErrorResponse")


def reading_order(schema: dict[str, Any]) -> list[str]:
    """The components in the order the docs page lists them (Swagger keeps the schema's order and can't sort them):
    the envelope first, then each endpoint's in the order the page shows endpoints (by tag, then path), each
    schema before the parts it refers to, those in field order. A schema shared by several endpoints stays with the
    first."""
    components = schema.get("components", {}).get("schemas", {})
    found: list[str] = []

    def visit(name: str) -> None:
        if name in found or name not in components:
            return
        found.append(name)
        for ref in _refs_in_order(components[name]):
            visit(ref)

    for name in ENVELOPE:
        visit(name)
    tags = [t["name"] for t in schema.get("tags", [])]
    operations = [op for ops in schema.get("paths", {}).values() for op in ops.values()]
    first_tag = lambda op: tags.index(op["tags"][0]) if op.get("tags") and op["tags"][0] in tags else len(tags)  # noqa: E731
    for op in sorted(operations, key=first_tag):  # stable: paths keep their order within a tag
        for ref in _refs_in_order({"body": op.get("requestBody"), "responses": op.get("responses")}):
            visit(ref)
    return found


def _refs_in_order(node: Any) -> list[str]:
    """The components `node` refers to, in the order they appear."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        own = [ref.rpartition("/")[2]] if isinstance(ref, str) else []
        return own + [r for v in node.values() for r in _refs_in_order(v)]
    if isinstance(node, list):
        return [r for v in node for r in _refs_in_order(v)]
    return []


def field_text(name: str) -> dict[str, str]:
    """`fields.toml`'s text for schema `name`, with what it inherits."""
    table = dict(fields().get(name, {}))
    parent = table.pop("_inherits", None)
    return {**(field_text(parent) if parent else {}), **table}


def reached(schema: dict[str, Any]) -> set[str]:
    """The components the operations refer to, directly or through other components."""
    components = schema.get("components", {}).get("schemas", {})
    found: set[str] = set()
    pending = _refs(schema.get("paths", {}))
    while pending:
        name = pending.pop()
        if name not in found and name in components:
            found.add(name)
            pending |= _refs(components[name])
    return found


def _refs(node: Any) -> set[str]:
    if isinstance(node, dict):
        ref = node.get("$ref")
        own = {ref.rpartition("/")[2]} if isinstance(ref, str) else set()
        return own.union(*(_refs(v) for v in node.values()))
    if isinstance(node, list):
        return set().union(*(_refs(v) for v in node))
    return set()
