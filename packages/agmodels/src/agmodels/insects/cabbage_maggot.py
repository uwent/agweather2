"""Cabbage Maggot, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Check

INSECT = Insect(
    id="cabbage-maggot",
    name="Cabbage Maggot",
    crops=("cole-crops",),
    base_f=42.8,
    upper_f=86,
    biofix="01-01",
    generations=(
        (360, 600, 1521),
        (1881, 2121, 3042),
    ),
    checks=(
        Check(
            kind="published",
            against="Trap catches of cabbage maggot flies in Wisconsin (Eckenrode and Chapman 1972)",
            result="The first flight starts at 360 degree days, within the 290 to 365 at which spring flies emerged over five years in the study. The second generation starts 1,521 degree days after the first, against the 1,176 the study found between generations, so it comes later than the study puts it.",
            report="docs/validation/models/cabbage-maggot.md#against-eckenrode-and-chapman-1972",
        ),
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, on the same degree-day totals",
            result="Our severity ratings, from 0 to 4, match VDIFN's own formula exactly at every 0.01 degree day across this insect's two risk windows, and our degree days match the calculator VDIFN used to within 0.000001 degree days. This shows that we reproduce VDIFN, not that its timing is right for Wisconsin.",
            report="docs/validation/models/cabbage-maggot.md#against-vdifn",
        ),
    ),
)
