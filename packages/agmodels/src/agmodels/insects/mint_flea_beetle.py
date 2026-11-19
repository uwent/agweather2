"""Flea Beetle (Mint), from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="mint-flea-beetle",
    name="Flea Beetle (Mint)",
    crops=("mint",),
    base_f=41,
    upper_f=None,
    biofix="01-01",
    generations=((1475, 1675, 1880),),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/mint-flea-beetle.md#against-vdifn",
        ),
    ),
)
