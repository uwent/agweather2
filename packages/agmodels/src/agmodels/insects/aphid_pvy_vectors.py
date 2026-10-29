"""Aphid PVY Vectors, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Citation

INSECT = Insect(
    id="aphid-pvy-vectors",
    name="Aphid PVY Vectors",
    crops=("Potato",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    generations=((1838, 2515, 3228),),
    citations=(
        Citation(text="VDIFN (UW–Madison Vegetable Entomology)."),
        Citation(text="Bradford, B. Z. and Groves, R. L. Vegetable Entomology Lab, UW–Madison, unpublished analysis."),
    ),
)
