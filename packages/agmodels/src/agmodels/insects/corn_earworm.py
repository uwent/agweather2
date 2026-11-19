"""Corn Earworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="corn-earworm",
    name="Corn Earworm",
    crops=("beans", "corn", "sweet-corn"),
    base_f=55,
    upper_f=92,
    biofix="08-01",
    generations=((70, 275, 440),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's risk window, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/corn-earworm.md#against-vdifn",
        ),
    ),
)
