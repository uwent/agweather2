"""Variegated Cutworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="variegated-cutworm",
    name="Variegated Cutworm",
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
        "leafy-greens",
        "melon",
        "mint",
        "potato",
        "tomato",
    ),
    base_f=45,
    upper_f=80.1,
    biofix="05-01",
    generations=((900, 1450, 2100),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/variegated-cutworm.md#against-vdifn",
        ),
    ),
)
