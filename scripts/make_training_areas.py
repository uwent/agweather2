"""Builds `frontend/lib/map/training-areas.json`: each fitted model's training area (D101) as one outline, for the map
explorer to draw over a model's map (Phase 7 track 2's increments).

From the Census Bureau's cartographic boundary files, 1:5,000,000 (public domain), as `scripts/make_outlines.py` reads
them (kept in `data/census/`). Each model's states and counties are merged into one shape, simplified to about 1 km
and rounded to 0.001°, so a group of counties shows as one area. `app/api/tests/test_training_areas.py` fails when a
model's area changes and this file isn't built again:

    uv run python scripts/make_training_areas.py data/census/cb_2023_us_state_5m.zip \
        data/census/cb_2023_us_county_5m.zip
"""

import json
import sys
from pathlib import Path

import shapefile  # pyshp
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from agdata.progress import Reporter
from agmodels.registry import all_models

OUT = Path(__file__).resolve().parents[1] / "frontend/lib/map/training-areas.json"
TOLERANCE = 0.01  # degrees, ~1 km


def shapes(path: str, key: str) -> dict[str, object]:
    """Each record's shape by its key field (STUSPS for states, GEOID for counties)."""
    with shapefile.Reader(path) as reader:
        return {
            record[key]: shape(s.__geo_interface__)
            for record, s in zip(reader.iterRecords(fields=[key]), reader.iterShapes(), strict=True)
        }


def rounded(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 3), round(coords[1], 3)]
    return [rounded(c) for c in coords]


def main(states_zip: str, counties_zip: str) -> int:
    report = Reporter()
    trained = {m_id: m.SPEC.trained for m_id, m in sorted(all_models().items()) if m.SPEC.trained is not None}
    report.step(f"Outlining the training areas of {len(trained)} models from {states_zip} and {counties_zip}")
    states = shapes(states_zip, "STUSPS")
    counties = shapes(counties_zip, "GEOID")
    out: dict[str, dict] = {}
    for m_id, t in trained.items():
        parts = []
        for code in (*t.states, *t.counties):
            found = states.get(code) if len(code) == 2 else counties.get(code)
            if found is None:
                report.fail(m_id, f"no outline for {code}")
                continue
            parts.append(found)
        area = unary_union(parts).simplify(TOLERANCE, preserve_topology=True)
        geometry = mapping(area)
        out[m_id] = {
            "codes": [*t.states, *t.counties],
            "geometry": {"type": geometry["type"], "coordinates": rounded(geometry["coordinates"])},
        }
        report.detail(f"{m_id}: {', '.join(out[m_id]['codes'])}")
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    return 0 if report.finish(f"wrote {OUT.name} ({OUT.stat().st_size / 1000:.0f} kB)") else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
