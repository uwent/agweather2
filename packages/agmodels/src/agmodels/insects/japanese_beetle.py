"""Japanese Beetle, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="japanese-beetle",
    name="Japanese Beetle",
    crops=(
        "asparagus",
        "beans",
        "beet",
        "blackberry",
        "cole-crops",
        "eggplant",
        "hops",
        "horseradish",
        "leafy-greens",
        "melon",
        "mint",
        "pea",
        "pepper",
        "potato",
        "pumpkin-squash",
        "raspberry",
        "tomato",
    ),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=((970, 1600, 2150),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/japanese-beetle.md#against-vdifn",
        ),
    ),
)
