"""Records small Open-Meteo responses for test_openmeteo.py (needs the network; the free hosts, no key).

uv run python packages/agdata/tests/fixtures/make_openmeteo_fixtures.py

openmeteo_{endpoint}_{model}.json: three days of June 2025 (historical-forecast: NBM, best_match, ECMWF IFS soil)
and two of June 2015 (the ERA5 archive) at the O1280 cell over Stillwater, OK, as `openmeteo.fetch` asks for them.
"""

import json
from datetime import date
from pathlib import Path
from unittest import mock

import requests

from agdata.sources import openmeteo

HERE = Path(__file__).parent
cell = openmeteo.cell_for(36.12, -97.07)
real_get = requests.Session.get


def record(endpoint):
    def get(self, address, params=None, **kwargs):
        response = real_get(self, address, params=params, **kwargs)
        name = f"openmeteo_{endpoint}_{params.get('models', 'era5')}.json"
        (HERE / name).write_text(json.dumps(response.json(), separators=(",", ":")))
        return response

    return get


with mock.patch.object(requests.Session, "get", record("historical")):
    openmeteo.fetch("historical", cell, date(2025, 6, 1), date(2025, 6, 3))
with mock.patch.object(requests.Session, "get", record("archive")):
    openmeteo.fetch("archive", cell, date(2015, 6, 1), date(2015, 6, 2))
print("wrote", sorted(p.name for p in HERE.glob("openmeteo_*.json")), "for", cell)
