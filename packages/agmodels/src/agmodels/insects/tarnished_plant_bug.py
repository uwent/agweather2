"""Tarnished Plant Bug (Lygus Bug), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="tarnished-plant-bug",
    name="Tarnished Plant Bug (Lygus Bug)",
    crops=("Celery", "Leafy Greens", "Potato", "Raspberry"),
    base_f=52,
    upper_f=None,
    biofix="01-01",
    criteria="Lygus bugs are active most of the summer after early-season nymph development (starting 275 FDD).",
    generations=((275, 1000, 2000),),
)
