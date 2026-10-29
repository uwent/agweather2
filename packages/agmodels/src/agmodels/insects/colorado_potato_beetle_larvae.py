"""Colorado Potato Beetle (Larvae), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "colorado-potato-beetle-larvae",
    "Colorado Potato Beetle (Larvae)",
    ("Eggplant", "Potato", "Tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "Our Colorado potato beetle larval abundance model was derived from 10 years of scouting data in the "
        "Central Sands and uses a base 50°F degree day model. First egg hatch is typically around 485 FDD with "
        "peak larval populations reached during the first generation at around 905 FDD. Larval populations then "
        "decline steadily through the end of the season (around 2500 FDD)."
    ),
    generations=((485, 905, 2500),),
    topic="colorado-potato-beetle",
)
