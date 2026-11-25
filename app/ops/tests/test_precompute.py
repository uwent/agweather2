"""The maps precomputed after each update (`ops.precompute`, step 7 D5), on the fixture archive."""

import pytest

from api import layermaps
from ops import precompute


@pytest.mark.django_db
def test_every_default_map_is_computed_into_the_disk_cache(archive, settings, tmp_path):
    settings.MAP_CACHE_DIR = tmp_path / "computed"
    layermaps._maps.clear()
    done = precompute.run()
    assert done.failed == {}, done.failed
    assert done.maps == len(precompute.layers()) * len(precompute.DAYS)
    assert len(list(settings.MAP_CACHE_DIR.glob("*.map"))) == done.maps
    layermaps._maps.clear()  # a web worker's first request is now a read
    assert precompute.run().maps == done.maps


def test_the_list_is_the_main_weather_layers_then_every_model_in_use():
    from agdata.layers import LAYERS
    from agmodels.registry import all_models

    found = precompute.layers()
    assert found[: len(precompute.WEATHER)] == list(precompute.WEATHER)
    assert all(layer in LAYERS for layer in found)
    models = {m for m, spec in all_models().items() if spec.SPEC.status != "retired"}
    assert set(found[len(precompute.WEATHER) :]) == models & set(LAYERS)
