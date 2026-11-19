"""Stalk Borer, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="stalk-borer",
    name="Stalk Borer",
    crops=("corn", "sweet-corn"),
    base_f=41,
    upper_f=86,
    biofix="01-01",
    generations=((1110, 1400, 1700),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at every total tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/stalk-borer.md#against-vdifn",
        ),
    ),
)
