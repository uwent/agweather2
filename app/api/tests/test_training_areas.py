"""The map explorer's training-area outlines (`frontend/lib/map/training-areas.json`) follow the models' specs (D101)."""

import json
from pathlib import Path

from agmodels.registry import all_models

OUTLINES = Path(__file__).resolve().parents[3] / "frontend/lib/map/training-areas.json"
REBUILD = "Run scripts/make_training_areas.py (its docstring has the command) and commit the file."


def test_every_fitted_model_has_its_outline():
    built = json.loads(OUTLINES.read_text())
    expected = {
        m_id: [*m.SPEC.trained.states, *m.SPEC.trained.counties]
        for m_id, m in all_models().items()
        if m.SPEC.trained is not None
    }
    assert {m_id: entry["codes"] for m_id, entry in built.items()} == expected, REBUILD


def test_outlines_are_polygons_in_lat_lng():
    for m_id, entry in json.loads(OUTLINES.read_text()).items():
        geometry = entry["geometry"]
        assert geometry["type"] in ("Polygon", "MultiPolygon"), m_id
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        for ring in (ring for polygon in polygons for ring in polygon):
            assert ring[0] == ring[-1], m_id
            assert all(-125 < lng < -66 and 24 < lat < 50 for lng, lat in ring), m_id
