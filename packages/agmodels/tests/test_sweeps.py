"""Sweep snapshots: each model over its sweep, saved with its version (CLAUDE.md: a deliberate change to a model's
output bumps its version and adds a changelog line). A change in output with the same version fails; after bumping,
rewrite with `uv run pytest packages/agmodels --update-snapshots`. The same sweeps feed the model pages."""

import itertools
import json
import math
from pathlib import Path

import pytest

from agmodels.registry import all_models

SNAPSHOTS = Path(__file__).parent / "snapshots"


def run_sweep(model) -> list[dict]:
    sweep = model.SPEC.sweep
    names = list(sweep)
    rows = []
    for values in itertools.product(*(sweep[n] for n in names)):
        inputs = dict(zip(names, values, strict=True))
        outputs = {k: None if math.isnan(v) else round(v, 9) for k, v in model.explore(**inputs).items()}
        rows.append({"inputs": inputs, "outputs": outputs})
    return rows


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_sweep_matches_its_snapshot(model_id, update_snapshots):
    model = all_models()[model_id]
    assert model.SPEC.sweep, f"{model_id} has no sweep"
    current = {"version": model.SPEC.version, "rows": run_sweep(model)}
    path = SNAPSHOTS / f"{model_id}.json"
    if update_snapshots or not path.exists():
        SNAPSHOTS.mkdir(exist_ok=True)
        rows = ",\n".join(json.dumps(row, separators=(",", ":")) for row in current["rows"])
        path.write_text(f'{{"version": {json.dumps(current["version"])}, "rows": [\n{rows}\n]}}\n')  # a row per line
        return
    saved = json.loads(path.read_text())
    if current["rows"] != saved["rows"]:
        assert current["version"] != saved["version"], (
            f"{model_id}'s outputs changed but its version is still {saved['version']}: if intended, bump the version, "
            "add a changelog line and run with --update-snapshots"
        )
        pytest.fail(f"{model_id} is version {current['version']} now: run with --update-snapshots to save its sweep")
    assert current["version"] == saved["version"], f"{model_id}'s version changed: run with --update-snapshots"
