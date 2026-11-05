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


def apply(schema: dict[str, Any]) -> dict[str, Any]:
    """Fill `schema` (an OpenAPI dict, changed in place and returned) with the public text."""
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
    for name, component in schema.get("components", {}).get("schemas", {}).items():
        if name in schemas:
            component["description"] = schemas[name]
        else:
            component.pop("description", None)
    return schema
