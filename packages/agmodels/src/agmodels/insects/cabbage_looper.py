"""Cabbage Looper, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="cabbage-looper",
    name="Cabbage Looper",
    crops=("Celery", "Cole Crops", "Hops", "Leafy Greens", "Melon", "Mint", "Pea", "Potato", "Tomato"),
    base_f=50,
    upper_f=90,
    biofix="05-15",
    generations=(
        (325, 520, 750),
        (1115, 1310, 1540),
    ),
)
