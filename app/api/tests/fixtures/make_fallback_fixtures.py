"""Records Open-Meteo's answers for test_forecast_fallback.py (needs the network; the free hosts, no key).

uv run python app/api/tests/fixtures/make_fallback_fixtures.py

fallback_{model}.json: July 4-22, 2025 (the forecast endpoint's span when the fixture archive's clock reads July 11)
at the O1280 cell over the fixture archive's point, from the historical-forecast endpoint, which answers in the
forecast endpoint's form: NBM, best_match and ECMWF IFS's soil, as `openmeteo.fetch` asks for them. The tests serve
them for the forecast endpoint (D114: Open-Meteo in place of a stale run).
"""

import json
import sys
from datetime import date
from pathlib import Path
from unittest import mock

import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[2]))  # app/, for the fixture archive's point

from agdata.sources import openmeteo  # noqa: E402
from api.tests.fixture_archive import POINT  # noqa: E402

FIRST, LAST = date(2025, 7, 4), date(2025, 7, 22)
real_get = requests.Session.get


def record(self, address, params=None, **kwargs):
    response = real_get(self, address, params=params, **kwargs)
    response.raise_for_status()
    (HERE / f"fallback_{params['models']}.json").write_text(json.dumps(response.json(), separators=(",", ":")))
    return response


if __name__ == "__main__":
    cell = openmeteo.cell_for(*POINT)
    with mock.patch.object(requests.Session, "get", record):
        openmeteo.fetch("historical", cell, FIRST, LAST)
    print("wrote", sorted(p.name for p in HERE.glob("fallback_*.json")), "for", cell)
