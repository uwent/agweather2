"""Black Cutworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="black-cutworm",
    name="Black Cutworm",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "carrot",
        "celery",
        "corn",
        "sweet-corn",
        "cucumber",
        "hops",
        "melon",
        "mint",
        "pea",
        "potato",
        "tomato",
    ),
    base_f=50,
    upper_f=86,
    biofix="05-15",
    generations=((300, 700, 1000),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's risk window, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/black-cutworm.md#against-vdifn",
        ),
    ),
)
