"""Every model under `agmodels.models`, by id."""

import importlib
import pkgutil
from functools import cache
from typing import cast

from agmodels import models
from agmodels.spec import Model


@cache
def all_models() -> dict[str, Model]:
    found: dict[str, Model] = {}
    for info in pkgutil.iter_modules(models.__path__):
        module = cast(Model, importlib.import_module(f"{models.__name__}.{info.name}"))
        spec = module.SPEC
        if spec.id in found:
            raise ValueError(f"two models have the id {spec.id!r}")
        found[spec.id] = module
    return found


def model(model_id: str) -> Model:
    try:
        return all_models()[model_id]
    except KeyError:
        raise ValueError(f"unknown model {model_id!r}") from None
