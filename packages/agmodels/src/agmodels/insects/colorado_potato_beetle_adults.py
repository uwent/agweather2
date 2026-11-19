"""Colorado Potato Beetle (Adults), from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Change, Check, Citation

INSECT = Insect(
    id="colorado-potato-beetle-adults",
    name="Colorado Potato Beetle (Adults)",
    crops=("eggplant", "potato", "tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=(
        (275, 690, 1090),
        (1090, 1690, 2500),
    ),
    topic="colorado-potato-beetle",
    status="retired",
    version="0.2",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Retired: `colorado-potato-beetle` now gives adults as one of its outputs, from the scouting fits on degree days 52/86 °F.",
        ),
    ),
    citations=(
        Citation(text="VDIFN (UW–Madison Vegetable Entomology)."),
        Citation(text="Bradford, B. Z. and Groves, R. L. Vegetable Entomology Lab, UW–Madison, unpublished analysis."),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's two risk windows, including at 1,090 degree days, where the two meet, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/colorado-potato-beetle-adults.md#against-vdifn",
        ),
    ),
)
