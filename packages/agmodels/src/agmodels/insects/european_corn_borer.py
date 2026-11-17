"""European Corn Borer, from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="european-corn-borer",
    name="European Corn Borer",
    crops=("beans", "corn", "sweet-corn", "eggplant", "pepper", "potato"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    generations=(
        (550, 740, 900),
        (1660, 1950, 2190),
    ),
)
