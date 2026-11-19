"""Tarnished Plant Bug (Lygus Bug), from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="tarnished-plant-bug",
    name="Tarnished Plant Bug (Lygus Bug)",
    crops=("beans", "celery", "leafy-greens", "pepper", "potato", "raspberry", "tomato"),
    base_f=52,
    upper_f=None,
    biofix="01-01",
    generations=((275, 1000, 2000),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at every total tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/tarnished-plant-bug.md#against-vdifn",
        ),
    ),
)
