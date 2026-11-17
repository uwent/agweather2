"""Tarnished Plant Bug (Lygus Bug), from VDIFN."""

from agmodels.phenology import Insect

INSECT = Insect(
    id="tarnished-plant-bug",
    name="Tarnished Plant Bug (Lygus Bug)",
    crops=("celery", "leafy-greens", "potato", "raspberry"),
    base_f=52,
    upper_f=None,
    biofix="01-01",
    generations=((275, 1000, 2000),),
)
