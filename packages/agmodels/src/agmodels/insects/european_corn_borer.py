"""European corn borer, rebuilt on Wisconsin's own degree-day lineage (Apple 1952 via UW–Madison's table; part H,
D36, D37), checked against DATCP's black light traps."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="european-corn-borer",
    name="European corn borer",
    crops=("beans", "corn", "sweet-corn", "eggplant", "pepper", "potato"),
    # UW–Madison's method (XHT1086/XHT1087, Delahaut 2012): the modified average, the minimum raised to 50 °F and the
    # maximum capped at 86 °F, from January 1; UMN's VegEdge counts the same way, "similar to the original model from
    # Dr. J. W. Apple, UW–Madison". NEWA runs no corn borer model, so D95 doesn't apply. EF-106 (Kentucky; VDIFN's
    # numbers) counts a simple average without an upper, and NCR 327 a simple average from first significant catch
    base_f=50,
    upper_f=86,
    dd_method="modified",
    biofix="01-01",
    source="UW–Madison's degree-day table for European corn borer",
    ported_from="VDIFN",
    life_stages=(
        # UW–Madison's table (Delahaut 2012; also UMass, Hazzard 2017): first spring moths 375 (UMN 374), peak 631;
        # the flight ends near 1,000 (the research's estimate: UMN scouts first-generation larvae to 1,000 and the
        # summer moths begin at 1,400). This curve's 1, 50 and 99 % are 420, 645 and 911. Moths don't feed on the crop
        LifeStage(label="Adult flight", start=374, peak=631, end=1000, weight=0),
        # First eggs 450 (76 after the first moths) and hatch about 100 later (UW: summer eggs 1,450, hatch 1,550;
        # UMass: hatch ~100 after laying). Egg masses are what scouts count; they carry no risk of their own
        DerivedStage(label="Egg masses", follows="Adult flight", lag=76, duration=100, weight=0),
        # Young larvae from hatch until they bore into stalks, shanks or ears, where sprays can't reach them: NCR 327
        # (Showers et al. 1989, Table 2) has peak hatch at 100, the 3rd instar at 350 and the 4th at 400 after first
        # significant catch, and first-generation larvae tunnelling into midribs from the 3rd instar (UW Veg Ento), so
        # about 300 degree days from hatch. The crop's risk
        DerivedStage(label="Young larvae", follows="Adult flight", lag=176, duration=300),
    ),
    # UW–Madison's peaks 631 and 1,733 are 1,102 apart (first moths 374 and 1,400: 1,026). The second flight's spread
    # by D36's default (the first flight's SD, ~117, for the generation time) puts its 1 % at 1,388 and 99 % at 2,144,
    # against UW's first summer moths at 1,400 and its summer treatments ending at 2,100
    generation_dd=1100,
    # Two generations in southern and central Wisconsin, one in the north (A1220; UW Veg Ento); MSU's third flight
    # (2,450–2,950) isn't expected here. Equal weights (D37): DATCP's northern traps show one flight (the report)
    max_generations=2,
    action_windows=(
        # Sprays work only before larvae bore in (A3646): from 10 % to 90 % of each generation's eggs hatched. That's
        # 671–986 and 1,713–2,142 degree days, against UW–Madison's 800–1,000 and 1,550–2,100 (Flandermeyer and Bick)
        ActionWindow(label="Scout and treat young larvae before they bore in", stage="Egg masses", between=(0.1, 0.9)),
    ),
    version="0.2",
    status="beta",
    # Apple's degree-day work was on canning corn in Wisconsin; its field years aren't in hand, so the span runs from
    # his paper (1952) to the table's last revision (2012)
    trained=TrainingArea(
        description="moth flights and egg laying in Wisconsin cornfields, as UW–Madison's degree-day table gives them",
        years=(1952, 2012),
        states=("WI",),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on UW–Madison's degree-day table (the modified average, 50/86 °F, from January 1): the spring flight as a curve from 374 to about 1,000 degree days (peak 631), egg masses and young larvae timed from it, a second flight 1,100 later (peak near 1,733), and a window to scout and treat young larvae before they bore in. Replaces VDIFN's two windows on single sine 50/86 °F (Kentucky's EF-106: 550–900 and 1,660–2,190), which came about 175 degree days late in spring.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="UW–Madison's degree-day table for European corn borer (first and peak moths of both flights, egg laying and hatch) and its spray windows",
            result="The spring flight begins at 374 degree days and peaks at 631, and the summer flight's first moths (1 %) come at 1,388 and its peak at 1,737, against UW–Madison's 375, 631, 1,400 and 1,733. The windows to treat young larvae run from 671 to 986 and from 1,713 to 2,142 degree days, against UW–Madison's 800 to 1,000 and 1,550 to 2,100.",
            report="docs/validation/models/european-corn-borer.md#against-its-sources-numbers",
        ),
        Check(
            kind="observations",
            against="Black light trap catches of corn borer moths in Wisconsin (DATCP), 2020–2026",
            result="At southern and central sites, the model's spring-flight midpoint fell a median 0 days from the week half the spring moths were caught (14 site-years, 11 within a week), and its summer-flight midpoint a median 1 day after (23 site-years, 12 within a week). In the north (Wausau, Marshfield, Antigo) the traps caught 4 moths before midsummer in 12 site-years and one flight from mid-July to mid-August, half caught by 1,402 degree days, which the model's summer flight follows a median 19 days late.",
            report="docs/validation/models/european-corn-borer.md#against-wisconsins-black-light-traps",
        ),
    ),
    citations=(
        Citation(
            text="Delahaut, K. Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087). UW–Madison Division of Extension, revised 2012.",
            url="https://hort.extension.wisc.edu/articles/degree-days-common-fruit-vegetable-insect-pests/",
        ),
        Citation(
            text="Apple, J. W. (1952). Corn borer development and control on canning corn in relation to temperature accumulation. Journal of Economic Entomology 45, 877–879.",
            doi="10.1093/jee/45.5.877",
        ),
        Citation(
            text="Flandermeyer, L. and Bick, E. N. Managing European Corn Borers in Wisconsin Corn Fields. UW–Madison Division of Extension, updated 2025.",
            url="https://cropsandsoils.extension.wisc.edu/articles/managing-european-corn-borers-in-wisconsin-corn-fields",
        ),
        Citation(
            text="Potter, B. European Corn Borer in Minnesota Field Corn. University of Minnesota Extension, reviewed 2020.",
            url="https://extension.umn.edu/corn-pest-management/european-corn-borer-minnesota-field-corn",
        ),
        Citation(
            text="Showers, W. B., et al. (1989). European Corn Borer: Development and Management (NCR 327). North Central Regional Extension Publication, Iowa State University.",
            url="https://publications.iowa.gov/12587/1/European_Corn_Borer.pdf",
        ),
        Citation(
            text="Hoard, M. W. and Weiss, M. J. (1995). Influence of postdiapause development on the voltinism of the European corn borer (Lepidoptera: Pyralidae) in North Dakota. Environmental Entomology 24, 564–570.",
            doi="10.1093/ee/24.3.564",
        ),
        Citation(
            text="Ikten, C., Skoda, S. R., Hunt, T. E., Molina-Ochoa, J. and Foster, J. E. (2011). Genetic variation and inheritance of diapause induction in two distinct voltine ecotypes of Ostrinia nubilalis (Lepidoptera: Crambidae). Annals of the Entomological Society of America 104, 567–575.",
            doi="10.1603/AN09149",
        ),
        Citation(
            text="Wisconsin Department of Agriculture, Trade and Consumer Protection: black light trap counts, 2020–2026.",
            url="https://datcp.wi.gov/Pages/Programs_Services/BlackLightTraps.aspx",
        ),
        Citation(
            text="Bessin, R. European Corn Borer Development Model (ENTFACT-106). University of Kentucky (VDIFN's numbers; compared).",
            url="https://entomology.ca.uky.edu/files/ef106.pdf",
        ),
    ),
)
