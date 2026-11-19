"""Western Bean Cutworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="western-bean-cutworm",
    name="Western Bean Cutworm",
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
        "potato",
        "tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="05-01",
    generations=((1320, 1420, 1535),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/western-bean-cutworm.md#against-vdifn",
        ),
    ),
)
