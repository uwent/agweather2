"""Corn Earworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="corn-earworm",
    name="Corn Earworm",
    crops=("beans", "corn", "sweet-corn"),
    base_f=55,
    upper_f=92,
    biofix="08-01",
    generations=((70, 275, 440),),
)
