"""Spotted Wing Drosophila, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="spotted-wing-drosophila",
    name="Spotted Wing Drosophila",
    crops=("Blackberry", "Cherry", "Raspberry"),
    base_f=45,
    upper_f=86,
    biofix="01-01",
    generations=((1276, 3180, 4000),),
)
