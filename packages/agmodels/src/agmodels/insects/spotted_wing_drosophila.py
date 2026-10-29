"""Spotted Wing Drosophila, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    "spotted-wing-drosophila",
    "Spotted Wing Drosophila",
    ("Blackberry", "Cherry", "Raspberry"),
    base_f=45,
    upper_f=86,
    biofix="01-01",
    criteria=(
        "In Wisconsin, overwintering adult Spotted Wing Drosophila begin egg-laying in mid to late June (around "
        "1276 FDD), and will complete a generation every 8-12 days. Populations peak around 3100 FDD, and will "
        "continue to be a threat to soft-skinned fruit through the end of the season."
    ),
    generations=((1276, 3180, 4000),),
)
