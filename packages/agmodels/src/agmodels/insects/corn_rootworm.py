"""Corn Rootworm, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "corn-rootworm",
    "Corn Rootworm",
    ("Corn (Field and Sweet)",),
    base_f=52,
    upper_f=None,
    biofix="01-01",
    criteria=(
        "First instar larvae appear around 329 FDD with light feeding expected. Larval populations peak around "
        "472 FDD with heavy feeding expected. Larval stage expected to end by 636 FDD."
    ),
    generations=((329, 472, 636),),
)
