"""Cabbage Looper, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="cabbage-looper",
    name="Cabbage Looper",
    crops=("celery", "cole-crops", "hops", "leafy-greens", "melon", "mint", "pea", "potato", "tomato"),
    base_f=50,
    upper_f=90,
    biofix="05-15",
    generations=(
        (325, 520, 750),
        (1115, 1310, 1540),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own program exactly at 701 degree-day totals from 0 to 3,500 on this insect's two generations, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/cabbage-looper.md#against-vdifn",
        ),
    ),
)
