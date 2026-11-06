"""The API's public documentation (`api.docs`): every endpoint, parameter and tag has its text, every entry is
used, and the text keeps to CLAUDE.md's "Writing for the public"."""

import re

import pytest

from api import docs
from api.api import api

SCHEMA = api.get_openapi_schema()
OPERATIONS = {op["operationId"]: op for ops in SCHEMA["paths"].values() for op in ops.values()}

# Words that have no place in public text (CLAUDE.md, "Writing for the public"): internal names and references,
# and marketing words. Matched as whole words, case ignored.
INTERNAL = [
    r"D\d{1,3}",
    r"Q\d{1,3}",
    r"PLAN\.md",
    r"Phase \d",
    r"agdata",
    r"agmodels",
    r"layermaps",
    r"ingredients?",
    r"cubes?",
    r"payload",
    r"backend",
    r"pipeline",
    r"ingest",
]
MARKETING = [
    r"powerful",
    r"seamless(ly)?",
    r"robust",
    r"cutting-edge",
    r"leverag\w*",
    r"unlock\w*",
    r"empower\w*",
    r"insights?",
    r"state-of-the-art",
    r"best-in-class",
]
BANNED = re.compile(r"\b(" + "|".join(INTERNAL + MARKETING) + r")\b", re.IGNORECASE)


def _public_text() -> list[tuple[str, str]]:
    """(where, text) for every piece of public text in the schema, code samples left out."""
    found = [("intro", SCHEMA["info"]["description"])]
    for op_id, op in OPERATIONS.items():
        found.append((op_id, f"{op['summary']}\n{op['description']}"))
        found += [(f"{op_id}.{p['name']}", p["description"]) for p in op.get("parameters", [])]
    found += [(f"tag {t['name']}", t["description"]) for t in SCHEMA["tags"]]
    for name, component in SCHEMA["components"]["schemas"].items():
        found += [(f"schema {name}", component["description"])] if "description" in component else []
        fields = component.get("properties", {}).items()
        found += [(f"schema {name}.{f}", p["description"]) for f, p in fields if "description" in p]
    return [(where, re.sub(r"```.*?```|`[^`]*`", "", text, flags=re.DOTALL)) for where, text in found]


def test_every_operation_has_a_page():
    missing = [op_id for op_id in OPERATIONS if docs.endpoint(op_id) is None]
    assert not missing, f"no api/docs/<operation>.md for {missing}"
    pages = {p.stem for p in docs.HERE.glob("*.md")} - {"intro"}
    assert pages <= set(OPERATIONS), f"pages for no operation: {sorted(pages - set(OPERATIONS))}"


def test_every_parameter_is_described():
    missing = [
        f"{op_id}.{p['name']}"
        for op_id, op in OPERATIONS.items()
        for p in op.get("parameters", [])
        if not p.get("description")
    ]
    assert not missing, f"add these to api/docs/parameters.toml: {missing}"


def test_every_entry_is_used():
    text = docs.parameters()
    used_names = {p["name"] for op in OPERATIONS.values() for p in op.get("parameters", [])}
    assert set(text["shared"]) <= used_names, f"unused [shared]: {sorted(set(text['shared']) - used_names)}"
    for table, entries in text.items():
        if table in ("shared", "tags", "schemas"):
            continue
        assert table in OPERATIONS, f"[{table}] names no operation"
        names = {p["name"] for p in OPERATIONS[table].get("parameters", [])}
        assert set(entries) <= names, f"[{table}] describes parameters it doesn't take: {set(entries) - names}"
    used_tags = {t for op in OPERATIONS.values() for t in op.get("tags", [])}
    assert set(text["tags"]) == used_tags
    assert set(text["schemas"]) <= set(SCHEMA["components"]["schemas"])


def test_operation_ids_are_short():
    assert "weather_daily" in OPERATIONS
    assert not [op_id for op_id in OPERATIONS if op_id.startswith("api_")]


@pytest.mark.parametrize(("where", "text"), _public_text(), ids=lambda v: v if len(v) < 60 else None)
def test_public_text_keeps_the_style(where, text):
    found = sorted({m.group(0) for m in BANNED.finditer(text)})
    assert not found, f"{where}: {found} (CLAUDE.md, 'Writing for the public')"
    assert "!" not in text, f"{where}: no exclamation marks"


def test_docs_page_and_schema_are_served(client):
    assert client.get("/api/v2/docs").status_code == 200
    schema = client.get("/api/v2/openapi.json").json()
    assert schema["info"]["description"].startswith("The AgWeather API")
    assert schema["paths"]["/api/v2/weather/daily"]["get"]["summary"] == "Daily weather"


def test_the_style_check_catches_what_it_should():
    assert BANNED.search("as decided in D63")
    assert BANNED.search("A powerful way to leverage weather insights")
    assert not BANNED.search("Daily weather at one or more locations, through the forecast.")


def test_the_schema_has_no_repeated_keys_so_swagger_can_parse_it():
    # Swagger UI parses the schema as YAML, which refuses a key twice in one object; JSON doesn't. A response keyed
    # by the integer 200 and another by the string "200" (an `openapi_extra`) both serialize as "200".
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    repeated: list[list[str]] = []

    def unique(pairs: list[tuple[str, object]]) -> dict:
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            repeated.append(keys)
        return dict(pairs)

    json.loads(json.dumps(api.get_openapi_schema(), cls=DjangoJSONEncoder), object_pairs_hook=unique)
    assert repeated == []
