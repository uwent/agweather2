"""Corn Earworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "corn-earworm",
    "Corn Earworm",
    ("Bean", "Corn (Field and Sweet)"),
    base_f=55,
    upper_f=92,
    biofix="08-01",
    criteria=(
        "Adjust biofix to match date when first eggs or adults are observed. Corn earworm eggs typically hatch "
        "around 70 FDD after the biofix date. Peak larval populations and damage occur around 275 FDD, with "
        "larvae leaving corn ears and pupating around 440 FDD."
    ),
    generations=((70, 275, 440),),
)
