"""Stalk borer, rebuilt as caterpillars moving into corn, on Lasack and Pedigo 1986 by way of Rice and Davis 2010
and Iowa State, with Levine 1983's degree-day method (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="stalk-borer",
    name="Stalk borer",
    crops=("corn", "sweet-corn"),
    # Levine 1983's method (D37): Allen's (1976) sine-wave degree days from January 1 above 5.1 °C (41.2 °F), the
    # threshold for development from egg to adult, which Lasack and Pedigo 1986 and the extension guides (Iowa State,
    # UW–Madison's A3646) use as 41 °F. None of them uses an upper threshold, so none here (VDIFN's 86 °F changes a
    # Wisconsin total by under 10 degree days by mid-July)
    base_f=41,
    upper_f=None,
    biofix="01-01",
    source="Lasack and Pedigo 1986",
    life_stages=(
        # Caterpillars leaving grasses for corn (pitfall traps in Iowa: Lasack and Pedigo 1986, as Rice and Davis 2010
        # give it): first caught at about 600 °C·d (1,080–1,110 °F·d), half at about 900 (1,620–1,650), little after
        # 1,100 (1,980); Iowa State's table has 10 % at 1,400 and half at 1,700. This curve's 10, 50 and 99 % are
        # 1,390, 1,652 and 2,018. One generation a year (Levine 1983); the moths fly from August to October
        LifeStage(label="Caterpillars moving into corn", start=1100, peak=1670, end=2100),
    ),
    action_windows=(
        # A3646 and Iowa State: scout border rows from 1,300–1,400 and, if needed, spray between 1,400 and 1,700,
        # while caterpillars are moving and before they bore in. This window runs from 3 % moved (about 1,290) to
        # 60 % (about 1,700)
        ActionWindow(
            label="Scout corn borders and treat if needed", stage="Caterpillars moving into corn", between=(0.03, 0.6)
        ),
    ),
    version="0.2",
    status="beta",
    # Lasack and Pedigo's fields were in Iowa; the paper's years aren't in hand (published 1986, "consistent between
    # years"): 1983–1985 is an estimate
    trained=TrainingArea(
        description="pitfall trap catches of caterpillars moving from grassy areas into corn in Iowa",
        years=(1983, 1985),
        states=("IA",),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from VDIFN."),
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt as one stage, caterpillars moving into corn (Lasack and Pedigo 1986; Iowa State: 10 % at 1,400 degree days, half at about 1,650), with a scouting and spray window from about 1,300 to 1,700; single-sine degree days above 41 °F with no upper threshold from January 1 (Levine 1983). Replaces VDIFN's window (1,110, 1,400, 1,700 degree days, 41/86 °F), which was labelled as moth flight and peaked at the start of the spray window.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Caterpillars moving into corn in Iowa (Lasack and Pedigo 1986), and Iowa State's and UW–Madison's scouting guides",
            result="10 % of the caterpillars have moved at 1,390 degree days and half at 1,652, against Iowa State's 1,400 and Lasack and Pedigo's 1,620 (1,650 in UW–Madison's guide). The scouting and spray window runs from 1,292 to 1,704 degree days, as the guides' 1,300 to 1,700. The model hasn't been compared with observations in Wisconsin.",
            report="docs/validation/models/stalk-borer.md#against-its-sources-numbers",
        ),
    ),
    citations=(
        Citation(
            text="Lasack, P. M. and Pedigo, L. P. (1986). Movement of stalk borer larvae (Lepidoptera: Noctuidae) from noncrop areas into corn. Journal of Economic Entomology 79, 1697–1702.",
            doi="10.1093/jee/79.6.1697",
        ),
        Citation(
            text="Rice, M. E. and Davis, P. M. (2010). Stalk borer (Lepidoptera: Noctuidae) ecology and integrated pest management in corn. Journal of Integrated Pest Management 1, C1–C6.",
            doi="10.1603/IPM10006",
        ),
        Citation(
            text="Levine, E. (1983). Temperature requirements for development of the stalk borer, Papaipema nebris (Lepidoptera: Noctuidae). Annals of the Entomological Society of America 76, 892–895.",
            doi="10.1093/aesa/76.5.892",
        ),
        Citation(
            text="Dean, A. and Hodgson, E. Stalk borer. Iowa State University Extension and Outreach.",
            url="https://crops.extension.iastate.edu/encyclopedia/stalk-borer",
        ),
        Citation(
            text="Dewerff, R., Bick, E., Liesch, P. J., et al. (2025). Pest Management in Wisconsin Field Crops (A3646), pp. 53–54. UW–Madison Division of Extension.",
            url="https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf",
        ),
    ),
)
