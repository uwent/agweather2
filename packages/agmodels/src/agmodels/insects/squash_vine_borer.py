"""Squash Vine Borer, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="squash-vine-borer",
    name="Squash Vine Borer",
    crops=("cucumber", "melon", "pumpkin-squash"),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=((750, 900, 1000),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at every total tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/squash-vine-borer.md#against-vdifn",
        ),
    ),
)
