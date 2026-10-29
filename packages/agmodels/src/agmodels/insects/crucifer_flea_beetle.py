"""Flea Beetle (Crucifer), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="crucifer-flea-beetle",
    name="Flea Beetle (Crucifer)",
    crops=("Cole Crops",),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    generations=(
        (820, 965, 1155),
        (1640, 1785, 1975),
    ),
)
