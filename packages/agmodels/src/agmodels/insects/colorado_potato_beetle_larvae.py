"""Colorado Potato Beetle (Larvae), from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Citation

INSECT = Insect(
    id="colorado-potato-beetle-larvae",
    name="Colorado Potato Beetle (Larvae)",
    crops=("Eggplant", "Potato", "Tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=((485, 905, 2500),),
    topic="colorado-potato-beetle",
    citations=(
        Citation(text="VDIFN (UW–Madison Vegetable Entomology)."),
        Citation(text="Bradford, B. Z. and Groves, R. L. Vegetable Entomology Lab, UW–Madison, unpublished analysis."),
    ),
)
