"""Writes the NBM fixtures for test_nbm.py from a real run (needs the network).

uv run python packages/agdata/tests/fixtures/make_nbm_fixtures.py

- nbm_f024.idx: the 2026-10-28 13z run's f024 inventory (every field, with std dev and probability messages)
- nbm_f049.idx: the same run's f049, a precip-only hour of a long run
"""

from datetime import UTC, datetime
from pathlib import Path

import requests

from agdata.sources import nbm

HERE = Path(__file__).parent
cycle = datetime(2026, 10, 28, 13, tzinfo=UTC)
for lead in (24, 49):
    text = requests.get(nbm.url(cycle, lead) + ".idx", timeout=60).text
    (HERE / f"nbm_f{lead:03d}.idx").write_text(text)
print("wrote", sorted(p.name for p in HERE.glob("nbm_*")))
