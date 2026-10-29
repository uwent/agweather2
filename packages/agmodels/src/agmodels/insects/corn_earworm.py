"""Corn Earworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="corn-earworm",
    name="Corn Earworm",
    crops=("Bean", "Corn (Field and Sweet)"),
    base_f=55,
    upper_f=92,
    biofix="08-01",
    generations=((70, 275, 440),),
)
