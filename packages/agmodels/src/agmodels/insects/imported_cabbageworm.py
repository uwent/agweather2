"""Imported Cabbageworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="imported-cabbageworm",
    name="Imported Cabbageworm",
    crops=("cole-crops",),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=(
        (150, 240, 630),
        (830, 1030, 2000),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's two risk windows, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/imported-cabbageworm.md#against-vdifn",
        ),
    ),
)
