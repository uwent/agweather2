"""Colorado Potato Beetle (Adults), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="colorado-potato-beetle-adults",
    name="Colorado Potato Beetle (Adults)",
    crops=("Eggplant", "Potato", "Tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=(
        (275, 690, 1090),
        (1090, 1690, 2500),
    ),
    topic="colorado-potato-beetle",
)
