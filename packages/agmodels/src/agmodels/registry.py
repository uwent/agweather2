"""Every model by id: the modules under `agmodels.models` and the insects under `agmodels.insects`.

Each model's page is the Markdown file beside its module (D35).
"""

import importlib
import pkgutil
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import cast

from agmodels import insects, models
from agmodels.phenology import Insect, InsectModel
from agmodels.spec import Model


def _modules(package: ModuleType) -> Iterator[ModuleType]:
    for info in pkgutil.iter_modules(package.__path__):
        yield importlib.import_module(f"{package.__name__}.{info.name}")


@cache
def _found() -> dict[str, tuple[Model, Path]]:
    found: dict[str, tuple[Model, Path]] = {}
    pairs = [(cast(Model, m), m.__file__) for m in _modules(models)]
    pairs += [(cast(Model, InsectModel(m.INSECT)), m.__file__) for m in _modules(insects)]
    for found_model, source in pairs:
        if found_model.SPEC.id in found:
            raise ValueError(f"two models have the id {found_model.SPEC.id!r}")
        found[found_model.SPEC.id] = (found_model, Path(cast(str, source)))
    return found


@cache
def all_models() -> dict[str, Model]:
    return {model_id: m for model_id, (m, _) in _found().items()}


def all_insects() -> tuple[Insect, ...]:
    return tuple(m.insect for m in all_models().values() if isinstance(m, InsectModel))


def model(model_id: str) -> Model:
    try:
        return _found()[model_id][0]
    except KeyError:
        raise ValueError(f"unknown model {model_id!r}") from None


def page_path(model_id: str) -> Path:
    """The model's Markdown page (prose, with front matter id, status and sources), beside its module."""
    model(model_id)
    return _found()[model_id][1].with_suffix(".md")
