"""Cabbage Looper, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "cabbage-looper",
    "Cabbage Looper",
    ("Celery", "Cole Crops", "Hops", "Leafy Greens", "Melon", "Mint", "Pea", "Potato", "Tomato"),
    base_f=50,
    upper_f=90,
    biofix="05-15",
    criteria=(
        "The first small larvae appear around 325 FDD after the May 15 biofix date. Feeding continues and worsens"
        " as larvae grow, peaking around 520 FDD and ending around 750 FDD. Second generation larvae may begin "
        "appearing around 1115 FDD, peak around 1310 FDD, and end around 1540 FDD."
    ),
    generations=(
        (325, 520, 750),
        (1115, 1310, 1540),
    ),
)
