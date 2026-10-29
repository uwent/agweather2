"""Colorado Potato Beetle (Adults), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="colorado-potato-beetle-adults",
    name="Colorado Potato Beetle (Adults)",
    crops=("Eggplant", "Potato", "Tomato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "Our Colorado potato beetle adult abundance model was derived from 10 years of scouting data in the "
        "Central Sands and uses a base 50°F degree day model. First adult colonization of crops is typically "
        "around 275 FDD with peak first-generation adults observed around 690 FDD. Adult populations decline to a"
        " low at 1090 FDD although larval feeding remains a significant threat if not controlled. Second "
        "generation adult populations peak around 1695 FDD and decline through the end of the season (around 2500"
        " FDD)."
    ),
    generations=(
        (275, 690, 1090),
        (1090, 1690, 2500),
    ),
    topic="colorado-potato-beetle",
)
