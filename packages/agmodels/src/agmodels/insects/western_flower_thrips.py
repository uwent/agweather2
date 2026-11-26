"""Western flower thrips, from VDIFN. Retired 2026-11-21 (Ben, part H): the thrips doesn't overwinter outdoors in
Wisconsin, so counting from January 1 has no meaning here, and its source (USPest's model) is under development."""

from agmodels.phenology import Insect
from agmodels.spec import Change, Check

INSECT = Insect(
    id="western-flower-thrips",
    name="Western flower thrips",
    season=("04-15", "10-31"),
    opens="calendar",
    crops=("cucumber", "eggplant", "pepper", "tomato"),
    base_f=45,
    upper_f=None,
    biofix="01-01",
    generations=(
        (340, 675, 1010),
        (1010, 1350, 1685),
        (1685, 2025, 2360),
        (2360, 2700, 3375),
    ),
    status="retired",
    version="0.2",
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Retired: western flower thrips don't survive the winter outdoors in Wisconsin, so a count of degree days from January 1 doesn't time them here, and the model's source, Oregon State's model, is still under development. Scout transplants and field edges instead.",
        ),
    ),
    checks=(
        Check(
            kind="system",
            against="VDIFN, the vegetable disease and insect forecasting tool this model replaces",
            result="Given the same degree days, our risk level matches VDIFN's exactly at every total tested, including across this insect's own four generations, and our degree days match the AgWeather calculator VDIFN used. This shows the model was carried over faithfully, not that its timing is right: it hasn't yet been checked against its source or against field counts in Wisconsin.",
            report="docs/validation/models/western-flower-thrips.md#against-vdifn",
        ),
    ),
)
