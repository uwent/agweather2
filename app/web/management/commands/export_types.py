import json

from django.core.management.base import BaseCommand
from django.utils.module_loading import autodiscover_modules
from pydantic.json_schema import models_json_schema

from web.inertia import Props


def all_props() -> list[type[Props]]:
    found: list[type[Props]] = []
    pending = list(Props.__subclasses__())
    while pending:
        cls = pending.pop()
        found.append(cls)
        pending.extend(cls.__subclasses__())
    return sorted(found, key=lambda cls: cls.__name__)


def api_schemas() -> dict:
    """The API's OpenAPI components (every request and response schema), with refs as JSON Schema `$defs`, and the
    envelope's shared schemas (`api.schemas`) whether or not an endpoint uses them yet."""
    from api import schemas
    from api.api import api

    text = json.dumps(api.get_openapi_schema()["components"]["schemas"])
    found = json.loads(text.replace("#/components/schemas/", "#/$defs/"))
    shared = [(schemas.TableResponse, "serialization"), (schemas.ErrorResponse, "serialization")]
    _, envelope = models_json_schema(shared, ref_template="#/$defs/{model}")
    return {**envelope.get("$defs", {}), **found}


class Command(BaseCommand):
    help = "Print the JSON Schema of every page's props (each app's props.py), or with --api the API's, for bin/types"

    def add_arguments(self, parser):
        parser.add_argument("--api", action="store_true", help="the API's schemas (from its OpenAPI) instead")

    def handle(self, *args, **options):
        if options["api"]:
            defs, title = api_schemas(), "ApiSchemas"
        else:
            autodiscover_modules("props")
            _, schema = models_json_schema(
                [(cls, "serialization") for cls in all_props()], ref_template="#/$defs/{model}"
            )
            defs, title = schema.get("$defs", {}), "PageProps"
        # json-schema-to-typescript emits one type per definition; the root lists them so none are dropped
        root = {
            "title": title,
            "type": "object",
            "properties": {name: {"$ref": f"#/$defs/{name}"} for name in sorted(defs)},
            "additionalProperties": False,
            "$defs": defs,
        }
        self.stdout.write(json.dumps(root, indent=2))
