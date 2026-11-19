"""Onion Maggot, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="onion-maggot",
    name="Onion Maggot",
    crops=("onion",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    generations=(
        (510, 680, 850),
        (1460, 1950, 2435),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/onion-maggot.md#against-vdifn",
        ),
    ),
)
