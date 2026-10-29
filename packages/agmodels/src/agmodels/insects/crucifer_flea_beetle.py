"""Flea Beetle (Crucifer), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "crucifer-flea-beetle",
    "Flea Beetle (Crucifer)",
    ("Cole Crops",),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    criteria=(
        "Adult flea beetles are most damaging with two generations typical in Wisconsin. First generation adults "
        "develop around 820 FDD and feed through around 1155 FDD. Second generation adults emerge around 1640 FDD"
        " and feed through around 1975 FDD."
    ),
    generations=(
        (820, 965, 1155),
        (1640, 1785, 1975),
    ),
)
