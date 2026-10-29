"""Mint Root Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "mint-root-borer",
    "Mint Root Borer",
    ("Mint",),
    base_f=50,
    upper_f=None,
    biofix="04-01",
    criteria=(
        "First moth catch expected around 430 FDD, with peak egg hatch occurring around 1280 FDD. End of risk is "
        "approximately 2150 FDD when hibernaculum formation completes."
    ),
    generations=((430, 1280, 2150),),
)
