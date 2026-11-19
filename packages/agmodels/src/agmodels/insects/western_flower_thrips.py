"""Western Flower Thrips, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="western-flower-thrips",
    name="Western Flower Thrips",
    crops=("cucumber", "eggplant", "pepper", "tomato"),
    base_f=45,
    upper_f=None,
    biofix="01-01",
    generations=(
        (340, 675, 1010),
        (1010, 1350, 1685),
        (1685, 2025, 2360),
        (2360, 2700, 3375),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at every total tested, including across this insect's own four generations, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/western-flower-thrips.md#against-vdifn",
        ),
    ),
)
