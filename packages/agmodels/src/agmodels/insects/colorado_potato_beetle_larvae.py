"""Colorado Potato Beetle (Larvae), from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check, Citation

INSECT = Insect(
    id="colorado-potato-beetle-larvae",
    name="Colorado Potato Beetle (Larvae)",
    crops=("eggplant", "potato", "tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=((485, 905, 2500),),
    topic="colorado-potato-beetle",
    citations=(
        Citation(text="VDIFN (UW–Madison Vegetable Entomology)."),
        Citation(text="Bradford, B. Z. and Groves, R. L. Vegetable Entomology Lab, UW–Madison, unpublished analysis."),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's risk window, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/colorado-potato-beetle-larvae.md#against-vdifn",
        ),
    ),
)
