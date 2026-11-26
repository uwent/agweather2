"""Mint root borer, rebuilt on Oregon State's USPest model (`mrb`, Berry, Takeyasu and Morris 1997) as D36 curves
(part H)."""

from agmodels.phenology import ActionWindow, DerivedStage, Insect, LifeStage
from agmodels.spec import Change, Check, Citation, TrainingArea

INSECT = Insect(
    id="mint-root-borer",
    name="Mint root borer",
    season=("06-01", "10-31"),
    opens="degree_days",
    crops=("mint",),
    # USPest's method: single sine above 50 °F from April 1; its upper threshold, 129–130 °F, is never reached, so
    # none here (the stored total)
    base_f=50,
    upper_f=None,
    biofix="04-01",
    source="Oregon State University's mint root borer model (USPest.org)",
    ported_from="VDIFN",
    life_stages=(
        # Moth flight (USPest `mrb`): first moth caught at 430, peak catch at 910, 90 % caught at 1,350. A PERT with its
        # mode at the peak, through 2 % at 430 (a first catch) and 90 % at 1,350; half the moths at 945 and 99 % at
        # 1,598, about 60 days of flight in a Wisconsin July, as Tollerup et al. 2013 saw in California. Moths don't
        # feed: the larvae carry the risk
        LifeStage(label="Moth flight", start=279, peak=910, end=1817, weight=0),
        # Larvae in roots and rhizomes: USPest's peak egg hatch (1,280) comes 370 after its peak moth catch (910, the
        # peak egg laying at 1,130 between), and half the larvae have formed their winter chambers (hibernacula) at
        # 2,150, 835 after half have hatched (945 + 370 = 1,315). Each larva feeds until it has made its chamber, so
        # the stage ends when the last larvae have, not at half; 5 % have at 1,705 (USPest 1,850)
        DerivedStage(label="Larvae in roots", follows="Moth flight", lag=370, duration=835),
    ),
    # Pheromone traps and sweep nets show when moths fly (Pacific Northwest handbook): from the first catch (2 %) to
    # 90 % caught, USPest's two flight events
    action_windows=(ActionWindow(label="Trap or sweep for moths", stage="Moth flight", between=(0.02, 0.9)),),
    version="0.4",
    status="beta",
    # Berry, Takeyasu and Morris's peppermint fields were in the Pacific Northwest; the years aren't in hand (the model
    # is dated 1997): 1990–1997 is an estimate
    trained=TrainingArea(
        description="moth and larval observations in Pacific Northwest peppermint",
        years=(1990, 1997),
        states=("OR", "WA", "ID"),
    ),
    changelog=(
        Change(
            version="0.2",
            date="2026-11-21",
            note="Rebuilt on Oregon State's mint root borer model (USPest.org; Berry, Takeyasu and Morris 1997): single-sine degree days above 50 °F from April 1, the moth flight as a curve through its first catch (430), peak (910) and 90 % catch (1,350), and the larvae in roots timed from it, from the peak egg hatch (1,280) until each has formed its winter chamber (half by 2,150). Moths carry no risk; the larvae do. Replaces VDIFN's window (430, 1,280, 2,150), which ended when half the larvae had formed their chambers.",
        ),
        Change(
            version="0.3",
            date="2026-11-26",
            note="In season from June 1 to October 31: from a week before its earliest activity on 2016–2025's weather at six Wisconsin places to October 31, the end of Wisconsin's growing season. Activity ends after October 31 whatever the weather, as fall freezes end it, so a mild fall no longer holds a stalled curve's activity into winter.",
        ),
        Change(
            version="0.4",
            date="2026-11-26",
            note="The season opens at each place about a week before the first moth flight in a typical year (the day the 30-year normal degree days, averaged over about 50 km, reach it), rather than on June 1 everywhere; where we don't have the normals, it still opens on June 1.",
        ),
    ),
    checks=(
        Check(
            kind="published",
            against="Oregon State's mint root borer model (USPest.org; Berry, Takeyasu and Morris 1997)",
            result="The moth flight passes 2 % at 430 degree days, peaks at 910 and reaches 90 % at 1,350, as the model's first catch, peak catch and 90 % catch. Half the larvae have hatched at 1,315 (the model's peak hatch 1,280) and half have formed their winter chambers at 2,150, as in the model; the first 5 % have at 1,705, earlier than its 1,850.",
            report="docs/validation/models/mint-root-borer.md#against-its-sources-numbers",
        ),
        Check(
            kind="published",
            against="Pheromone trap catches in peppermint in Shasta and Siskiyou counties, California, 2010–2011 (Tollerup et al. 2013)",
            result="The same model, run on California weather, was late: moths were caught 4 to 11 days before or after its first catch, its peak flight came 10 to 25 days late in three of four county-years, and its 90 % catch 15 to 17 days late in Shasta and about a month late in Siskiyou. The authors found it a poor predictor there. It hasn't been compared with catches in Wisconsin.",
            report="docs/validation/models/mint-root-borer.md#against-trap-catches-in-california",
        ),
    ),
    citations=(
        Citation(
            text="Berry, R. E., Takeyasu, J. and Morris, M. (1997). Mint root borer degree-day model. Oregon State University, Integrated Plant Protection Center, on USPest.org.",
            url="https://uspest.org/cgi-bin/ddmodel2.pl?spp=mrb",
        ),
        Citation(
            text="Tollerup, K. E., Marcum, D., Wilson, R. and Godfrey, L. (2013). Biology of mint root borer (Lepidoptera: Crambidae) and control options on California peppermint. Journal of Integrated Pest Management 4(3), A1–A4.",
            doi="10.1603/IPM13004",
        ),
        Citation(
            text="Mint-Mint root borer. In Pacific Northwest Pest Management Handbooks: Insect Management Handbook. Oregon State University, Washington State University and University of Idaho, 2026.",
            url="https://pnwhandbooks.org/insect/agronomic/mint/mint-mint-root-borer",
        ),
    ),
)
