"""Aphid PVY Vectors, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="aphid-pvy-vectors",
    name="Aphid PVY Vectors",
    crops=("Potato",),
    base_f=39.2,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "The risk of PVY transmission by aphid vectors begins around 1838 FDD, peaks around 2515 FDD, and remains"
        " elevated through vine kill. PVY transmission risk is calculated from a combination of several aphid "
        "species, the relative abundance of each species in Wisconsin, and the estimated PVY transmission "
        "efficiency of each species. Aphid vectors include Soybean aphid, Bird cherry-oat aphid, Green peach "
        "aphid, Pea aphid, Corn leaf aphid, and Potato aphid."
    ),
    generations=((1838, 2515, 3228),),
)
