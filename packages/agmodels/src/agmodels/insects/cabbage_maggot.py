"""Cabbage Maggot, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "cabbage-maggot",
    "Cabbage Maggot",
    ("Cole Crops",),
    base_f=42.8,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "Adult emergence occurs around 360 FDD, with peak emergence occurring around 600 FDD. Egg laying occurs "
        "from around 750 FDD to 1500 FDD with a peak around 1050 FDD. Second generation adult emergence begins "
        "around 1880 FDD and peaks around 2120 FDD, with egg-laying occurring from 2270 FDD through 3040 FDD."
    ),
    generations=(
        (360, 600, 1521),
        (1881, 2121, 3042),
    ),
)
