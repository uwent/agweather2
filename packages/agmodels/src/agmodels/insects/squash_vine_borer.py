"""Squash Vine Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "squash-vine-borer",
    "Squash Vine Borer",
    ("Cucumber", "Melon", "Pumpkin and Squash"),
    base_f=50,
    upper_f=None,
    biofix="01-01",
    criteria="Adult emergence begins around 750 FDD, peaking around 900 FDD, and ending around 1000 FDD.",
    generations=((750, 900, 1000),),
)
