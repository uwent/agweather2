"""Degree-day presets: each crop's usual growing degree-day setting (method, base, upper threshold), when the count
starts, and the temperature that kills the crop in fall, each with its source (PLAN.md Phase 6 step 2).

They serve the degree-day calculator and the crop GDD outlook (`/degree-days/presets`). Where we run a crop's stage
model, its preset is that model's setting, so a calculator total matches the stage page (a test checks they agree);
elsewhere the setting comes from the literature or extension practice, checked against HPRCC's CliGrow list, and
`notes` says where sources differ.
"""

from dataclasses import dataclass
from typing import Literal

from agmodels.ingredients import DegreeDays
from agmodels.spec import Citation

Start = Literal["planting", "january_1"]


@dataclass(frozen=True, kw_only=True)
class Freeze:
    """The air temperature (°F) that kills the crop, as the first fall freeze ends its season."""

    f: float
    note: str  # public: what dies at it
    citations: tuple[Citation, ...]


@dataclass(frozen=True, kw_only=True)
class DegreeDayPreset:
    id: str
    crop: str
    label: str  # public: the crop and what the count is for
    setting: DegreeDays
    starts: Start  # when the count usually starts
    model: str | None = None  # the stage model whose setting this is
    notes: str = ""  # public: where sources differ, what the count is used for
    citations: tuple[Citation, ...]
    freeze: Freeze | None = None


NDSU_FROST = Citation(
    text="NDSU Extension: Fall frost damage to field crops.",
    url="https://www.ndsu.edu/agriculture/ag-hub/fall-frost-damage-field-crops",
)
NDSU_A1995 = Citation(
    text="Kandel, H. et al. (2020). Sunflower production guide. NDSU Extension A1995.",
    url="https://ndsu.edu/agriculture/sites/default/files/2023-12/a1995.pdf",
)

CORN = DegreeDayPreset(
    id="corn",
    crop="Corn",
    label="Corn (field)",
    setting=DegreeDays(method="modified", base_f=50, upper_f=86),
    starts="planting",
    model="corn-stages",
    notes="Hybrids are rated by these degree days from planting to black layer (physiological maturity).",
    citations=(
        Citation(
            text="Gilmore, E. C. and Rogers, J. S. (1958). Heat units as a method of measuring maturity in corn. "
            "Agronomy Journal 50, 611–615.",
            doi="10.2134/agronj1958.00021962005000100014x",
        ),
        Citation(
            text="Neild, R. E. and Newman, J. E. (1987). Growing season characteristics and requirements in the Corn "
            "Belt. National Corn Handbook NCH-40, Purdue University.",
            url="https://www.extension.purdue.edu/extmedia/nch/nch-40.html",
        ),
    ),
    freeze=Freeze(f=28, note="Kills the whole plant; 32 °F kills leaves.", citations=(NDSU_FROST,)),
)
ALFALFA = DegreeDayPreset(
    id="alfalfa",
    crop="Alfalfa",
    label="Alfalfa",
    setting=DegreeDays(method="sine", base_f=41, upper_f=86),
    starts="january_1",
    model="alfalfa-growth",
    notes="Counted from January 1 in spring, or from the last cutting. HPRCC's CliGrow uses an upper threshold of "
    "77 °F; we use 86 °F, as UW–Madison's alfalfa cutting tool does.",
    citations=(
        Citation(
            text="Newell, S. Managing fall alfalfa cutting for persistence. UW–Madison Extension Crops and Soils.",
            url="https://cropsandsoils.extension.wisc.edu/articles/managing-fall-alfalfa-cutting-for-persistence/",
        ),
    ),
    freeze=Freeze(
        f=24,
        note="A killing freeze, which ends the stand's fall growth.",
        citations=(
            Citation(
                text="University of Minnesota Extension: Managing alfalfa winter injury.",
                url="https://extension.umn.edu/growing-forages/managing-alfalfa-winter-injury",
            ),
        ),
    ),
)
POTATO = DegreeDayPreset(
    id="potato",
    crop="Potato",
    label="Potato (to emergence)",
    setting=DegreeDays(method="average", base_f=39.2),
    starts="planting",
    model="potato-stages",
    notes="Degree days above 4 °C (39.2 °F) from planting, fitted to Wisconsin's emergence dates; 50% emergence "
    "comes at about 374 °F·d (208 °C·d). HPRCC's CliGrow uses 45 °F with an upper threshold of 97 °F.",
    citations=(
        Citation(
            text="UW Vegetable Pathology, Vegetable Crop Updates (2020–2026): planting and 50% emergence dates by "
            "location.",
            url="https://vegpath.plantpath.wisc.edu/2026/08/23/vegetable-crop-update-aug-23-2026/",
        ),
    ),
)
SPRING_WHEAT = DegreeDayPreset(
    id="spring-wheat",
    crop="Wheat",
    label="Spring wheat",
    setting=DegreeDays(method="modified", base_f=32, upper_f=95),
    starts="planting",
    model="spring-wheat-stages",
    notes="North Dakota's method also limits the maximum to 70 °F until the second leaf (Haun stage 2.0), which a "
    "single setting can't express; the wheat stage model applies it. HPRCC's CliGrow uses 32/77 °F.",
    citations=(
        Citation(
            text="Bauer, A., Fanning, C., Enz, J. W. and Eberlein, C. V. (1984). Use of growing-degree days to "
            "determine spring wheat growth stages. North Dakota Cooperative Extension Service EB-37.",
        ),
        Citation(
            text="NDAWN (North Dakota Agricultural Weather Network): Wheat growing degree days.",
            url="https://ndawn.ndsu.nodak.edu/help-wheat-growing-degree-days.html",
        ),
    ),
)

BARLEY = DegreeDayPreset(
    id="barley",
    crop="Barley",
    label="Barley",
    setting=DegreeDays(method="modified", base_f=32, upper_f=95),
    starts="planting",
    notes="As for spring wheat, North Dakota's method also limits the maximum to 70 °F until the second leaf "
    "(Haun stage 2.0), which a single setting can't express.",
    citations=(
        Citation(
            text="NDAWN (North Dakota Agricultural Weather Network): Barley growing degree days.",
            url="https://ndawn.ndsu.nodak.edu/help-barley-growing-degree-days.html",
        ),
    ),
)
SOYBEAN = DegreeDayPreset(
    id="soybean",
    crop="Soybean",
    label="Soybean",
    setting=DegreeDays(method="modified", base_f=50, upper_f=86),
    starts="planting",
    notes="The corn setting, as NDAWN and HPRCC's CliGrow use it. Soybean development depends on day length as well "
    "as heat, so degree days predict its stages less well than corn's; our soybean stage model uses both.",
    citations=(
        Citation(
            text="NDAWN (North Dakota Agricultural Weather Network): Soybean growing degree days.",
            url="https://ndawn.ndsu.nodak.edu/help-soybean-growing-degree-days.html",
        ),
    ),
    freeze=Freeze(f=28, note="Kills the plant; 28–32 °F damages leaves and pods.", citations=(NDSU_FROST,)),
)
DRY_BEAN = DegreeDayPreset(
    id="dry-bean",
    crop="Dry bean",
    label="Dry (edible) bean",
    setting=DegreeDays(method="modified", base_f=50, upper_f=86),
    starts="planting",
    notes="HPRCC's CliGrow setting. We found no recent extension publication that sets a base and upper threshold "
    "for dry beans; Nebraska gives 1550–1700 degree days from emergence to maturity.",
    citations=(
        Citation(
            text="HPRCC (High Plains Regional Climate Center): CliGrow.",
            url="https://hprcc.unl.edu/agroclimate/cligrow/",
        ),
        Citation(
            text="University of Nebraska–Lincoln CropWatch: Dry beans (August 21, 2009).",
            url="https://cropwatch.unl.edu/8-21-09-dry-beans",
        ),
    ),
    freeze=Freeze(
        f=32, note="Pinto and navy beans are very sensitive to frost: 30–32 °F kills them.", citations=(NDSU_FROST,)
    ),
)
SORGHUM = DegreeDayPreset(
    id="sorghum",
    crop="Sorghum",
    label="Grain sorghum",
    setting=DegreeDays(method="modified", base_f=50, upper_f=100),
    starts="planting",
    notes="Black layer (physiological maturity) comes at about 2,700 degree days for short-season hybrids and "
    "3,400 for full-season ones. HPRCC's CliGrow uses an upper threshold of 86 °F.",
    citations=(
        Citation(
            text="Kelley, J. (2011). Grain sorghum growth and development. In Grain Sorghum Production Handbook, "
            "University of Arkansas Cooperative Extension Service MP297.",
            url="https://www.uaex.uada.edu/publications/PDF/MP297/1_growth_development.pdf",
        ),
    ),
    freeze=Freeze(
        f=28,
        note="Stops grain fill.",
        citations=(
            Citation(
                text="Kansas State University Research and Extension: Grain sorghum production handbook, MF-2234.",
                url="https://bookstore.ksre.ksu.edu/pubs/MF2234.PDF",
            ),
        ),
    ),
)
SUGARBEET = DegreeDayPreset(
    id="sugarbeet",
    crop="Sugarbeet",
    label="Sugarbeet",
    setting=DegreeDays(method="modified", base_f=34, upper_f=86),
    starts="planting",
    notes="North Dakota's setting, from Holen and Dexter (1997), who found a 34 °F base predicted leaf stages best. "
    "HPRCC's CliGrow uses 50/86 °F.",
    citations=(
        Citation(
            text="Holen, C. D. and Dexter, A. G. (1997). A growing degree day equation for early sugarbeet leaf "
            "stages. Sugarbeet Research and Extension Reports 27, 152–157.",
        ),
        Citation(
            text="NDAWN (North Dakota Agricultural Weather Network): Sugarbeet growing degree days.",
            url="https://ndawn.ndsu.nodak.edu/help-sugarbeet-growing-degree-days.html",
        ),
    ),
)
SUNFLOWER = DegreeDayPreset(
    id="sunflower",
    crop="Sunflower",
    label="Sunflower",
    setting=DegreeDays(method="modified", base_f=44),
    starts="planting",
    notes="North Dakota's setting: temperatures below 44 °F count as 44, with no upper threshold. Physiological "
    "maturity (R9) comes at about 2,310 degree days. HPRCC's CliGrow uses 50/99 °F with the same maturity total.",
    citations=(
        NDSU_A1995,
        Citation(
            text="Schneiter, A. A. and Miller, J. F. (1981). Description of sunflower growth stages. Crop Science 21, "
            "901–903.",
            doi="10.2135/cropsci1981.0011183X002100060024x",
        ),
    ),
    freeze=Freeze(
        f=25,
        note="Causes little damage once seeds have filled; 28–30 °F injures buds and flowers.",
        citations=(NDSU_A1995,),
    ),
)
SWEET_CORN = DegreeDayPreset(
    id="sweet-corn",
    crop="Sweet corn",
    label="Sweet corn (processing)",
    setting=DegreeDays(method="modified", base_f=50, upper_f=86),
    starts="planting",
    notes="The field corn setting, used for processing sweet corn. Oregon State uses 44/86 °F for fresh-market "
    "varieties.",
    citations=(
        Citation(
            text="Andrews, N. et al. Vegetable degree-day models: an introduction for farmers and gardeners. Oregon "
            "State University Extension EM 9305.",
            url="https://extension.oregonstate.edu/catalog/em-9305-vegetable-degree-day-models-introduction-farmers-gardeners",
        ),
    ),
)
PEA = DegreeDayPreset(
    id="pea",
    crop="Pea",
    label="Green pea (processing)",
    setting=DegreeDays(method="average", base_f=40),
    starts="planting",
    notes="The heat units long used to schedule canning peas. Quebec's processors use 41 °F (5 °C).",
    citations=(
        Citation(
            text="Katz, Y. H. (1952). The relationship between heat unit accumulation and the planting and "
            "harvesting of canning peas. Agronomy Journal 44, 74–78.",
            doi="10.2134/agronj1952.00021962004400020004x",
        ),
        Citation(
            text="Bourgeois, G., Jenni, S., Laurence, H. and Tremblay, N. (2000). Improving the prediction of "
            "processing pea maturity based on the growing-degree day approach. HortScience 35, 611–614.",
            doi="10.21273/HORTSCI.35.4.611",
        ),
    ),
)
SNAP_BEAN = DegreeDayPreset(
    id="snap-bean",
    crop="Snap bean",
    label="Snap bean",
    setting=DegreeDays(method="sine", base_f=40, upper_f=90),
    starts="planting",
    notes="Oregon State's Croptime setting, fitted in western Oregon (2013–2015); we found none fitted in the Upper "
    "Midwest. Its authors note that days from planting can predict harvest about as well.",
    citations=(
        Citation(
            text="Oregon State University Croptime: Bean (snap bean) varieties models, version 1.0 (2020).",
            url="https://instar.biossys.oregonstate.edu/CROPTIME/bean_varieties_models.pdf",
        ),
    ),
)

PRESETS: tuple[DegreeDayPreset, ...] = (
    CORN,
    SOYBEAN,
    ALFALFA,
    SPRING_WHEAT,
    BARLEY,
    DRY_BEAN,
    SORGHUM,
    SUGARBEET,
    SUNFLOWER,
    POTATO,
    SWEET_CORN,
    PEA,
    SNAP_BEAN,
)
