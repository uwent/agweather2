"""Asparagus Beetle (Common), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="common-asparagus-beetle",
    name="Asparagus Beetle (Common)",
    crops=("Asparagus",),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "Egg hatch begins around 105 FDD, with peak larvae around 250 FDD and last larvae around 405 FDD. Peak "
        "adults around 570 FDD."
    ),
    generations=((105, 250, 405),),
)
