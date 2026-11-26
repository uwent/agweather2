"""Stalk borer, rebuilt as caterpillars moving into corn, on Lasack and Pedigo 1986 and Iowa State, with Levine 1983's
degree-day method (part H, D36, D37)."""

from agmodels.phenology import ActionWindow, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="stalk-borer",
    name="Stalk borer",
    season=("05-15", "08-31"),
    opens="degree_days",
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
        # Caterpillars leaving grasses for corn (Lasack and Pedigo 1986, p. 1702: linear pitfall traps in front of corn
        # rows beside grassy terraces and a waterway near Baxter, Iowa, 1984 and 1985; Allen's sine above 5.1 °C from
        # January 1 at Newton): first caught after 600 °C·d (1,080 °F·d), half after 904 in 1984 and 881 in 1985 (1,627
        # and 1,586 °F·d), little after 1,100 (1,980); Iowa State's table has 10 % at 1,400 and half at 1,700. This
        # curve's 10, 50 and 99 % are 1,390, 1,652 and 2,018. One generation a year (Levine 1983); the moths fly from
        # August to October
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
    version="0.4",
    status="beta",
    # Lasack and Pedigo's two fields near Baxter, Jasper County, Iowa, sampled in 1984 and 1985 (p. 1697)
    trained=TrainingArea(
        description="pitfall trap catches of caterpillars moving from grassy areas into corn in Iowa",
        years=(1984, 1985),
        states=("IA",),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from VDIFN."),
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt as one stage, caterpillars moving into corn (Lasack and Pedigo 1986; Iowa State: 10 % at 1,400 degree days, half at about 1,650), with a scouting and spray window from about 1,300 to 1,700; single-sine degree days above 41 °F with no upper threshold from January 1 (Levine 1983). Replaces VDIFN's window (1,110, 1,400, 1,700 degree days, 41/86 °F), which was labelled as moth flight and peaked at the start of the spray window.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from May 15 to August 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to the end of the month its latest activity ended in (August 5). Activity ends after August 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="The season opens at each place about a week before the first caterpillars moving into corn in a typical year (the day the 30-year normal degree days, averaged over about 50 km, reach it), rather than on May 15 everywhere; where we don't have the normals, it still opens on May 15.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Caterpillars moving into corn in Iowa (Lasack and Pedigo 1986), and Iowa State's and UW–Madison's scouting guides",
            result="10 % of the caterpillars have moved at 1,390 degree days and half at 1,652, against Iowa State's 1,400 and Lasack and Pedigo's 1,627 and 1,586 in their two years (1,650 in UW–Madison's guide). The scouting and spray window runs from 1,292 to 1,704 degree days, as the guides' 1,300 to 1,700. The model hasn't been compared with observations in Wisconsin.",
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
            text="Allen, J. C. (1976). A modified sine wave method for calculating degree days. Environmental Entomology 5, 388–396.",
            doi="10.1093/ee/5.3.388",
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
