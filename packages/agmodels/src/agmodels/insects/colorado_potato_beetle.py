"""Colorado potato beetle, from the Crop Risk Tool."""

from agmodels.insects import CRT
from agmodels.phenology import Insect, Stage
from agmodels.spec import Citation

INSECT = Insect(
    id="colorado-potato-beetle",
    name="Colorado potato beetle",
    crops=("Potato", "Tomato", "Eggplant"),
    base_f=50,
    upper_f=86,
    biofix="01-01",
    stages=(
        Stage(start=200, severity=1, label="1st gen adult colonization"),
        Stage(start=350, severity=2, label="1st gen egg hatch"),
        Stage(start=600, severity=3, label="1st gen peak adults"),
        Stage(start=800, severity=4, label="1st gen peak larvae"),
        Stage(start=935, severity=2, label="1st gen pupation"),
        Stage(start=1100, severity=3, label="2nd gen adult emergence"),
        Stage(start=1470, severity=4, label="2nd gen peak adults"),
        Stage(start=1800, severity=3, label="2nd gen adult feeding continues"),
        Stage(start=1970, severity=2, label="2nd gen adults begin dispersing"),
        Stage(start=2265, severity=1, label="2nd gen adults mostly dispersed"),
    ),
    source=CRT,
    citations=(
        Citation(text="The Crop Risk Tool (UW–Madison Vegetable Entomology)."),
        Citation(text="Bradford, B. Z. and Groves, R. L. Vegetable Entomology Lab, UW–Madison, unpublished analysis."),
    ),
)
