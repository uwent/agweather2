"""Colorado Potato Beetle (Larvae), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="colorado-potato-beetle-larvae",
    name="Colorado Potato Beetle (Larvae)",
    crops=("Eggplant", "Potato", "Tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=((485, 905, 2500),),
    topic="colorado-potato-beetle",
)
