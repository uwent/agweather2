"""European Corn Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="european-corn-borer",
    name="European Corn Borer",
    crops=("Bean", "Corn (Field and Sweet)", "Eggplant", "Pepper", "Potato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "First generation adult flight expected starting 329 FDD, peaking 472 FDD, and ending 636 FDD. Second "
        "generation adult flight expected starting 1660 FDD, peaking 1950 FDD, and ending 2190 FDD."
    ),
    generations=(
        (550, 740, 900),
        (1660, 1950, 2190),
    ),
)
