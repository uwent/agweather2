"""Western Bean Cutworm, from VDIFN."""

from agmodels.phenology import Insect
from agmodels.spec import Change, Check

INSECT = Insect(
    id="western-bean-cutworm",
    name="Western Bean Cutworm",
    crops=("corn", "sweet-corn", "dry-bean"),
    base_f=50,
    upper_f=None,
    biofix="05-01",
    generations=((1320, 1420, 1535),),
    version="0.2",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-18",
            note="Crops corrected to corn, sweet corn and dry beans (the list had been copied from black cutworm's).",
        ),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at all 2,804 totals tested, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/western-bean-cutworm.md#against-vdifn",
        ),
    ),
)
