"""Flea Beetle (Mint), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "mint-flea-beetle",
    "Flea Beetle (Mint)",
    ("Mint",),
    base_f=41,
    upper_f=None,
    biofix="01-01",
    criteria=(
        "Mint flea beetle adults emerge around 1475 FDD, with activity peaking around 1675 FDD and ending around "
        "1880 FDD."
    ),
    generations=((1475, 1675, 1880),),
)
