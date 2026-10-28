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


class Command(BaseCommand):
    help = "Print the JSON Schema of every page's props (each app's props.py), for bin/types"

    def handle(self, *args, **options):
        autodiscover_modules("props")
        _, schema = models_json_schema([(cls, "serialization") for cls in all_props()], ref_template="#/$defs/{model}")
        # json-schema-to-typescript emits one type per definition; the root lists them so none are dropped
        defs = schema.get("$defs", {})
        root = {
            "title": "PageProps",
            "type": "object",
            "properties": {name: {"$ref": f"#/$defs/{name}"} for name in sorted(defs)},
            "additionalProperties": False,
            "$defs": defs,
        }
        self.stdout.write(json.dumps(root, indent=2))
