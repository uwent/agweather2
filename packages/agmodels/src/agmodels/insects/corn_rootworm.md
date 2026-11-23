---
id: corn-rootworm
status: draft
updated: 2026-11-23
summary: Times corn rootworm egg hatch, larvae feeding on corn roots and the beetles that follow from air-temperature degree days since January 1 (base 52 °F), on Wisconsin's northern corn rootworm study, and marks when to dig and rate roots.
sources:
  - Apple, Walgenbach and Knee 1971 (northern corn rootworm egg hatch, Madison, Wisconsin; the base and the hatch)
  - Chiang and Sisson 1968 (northern corn rootworm egg hatch in Minnesota; the base, and hatch in soil and air temperatures compared)
  - UC IPM, northern corn rootworm degree-day models (the single-sine method)
  - Davis, Brenes and Allee 1996 (larvae, pupae and beetles in New York cornfields; the larvae's time, and compared)
  - Jackson and Elliott 1988 (western corn rootworm larvae and pupae at constant temperatures; the pupa's time)
  - Wilde 1971 and Levine, Oloumi-Sadeghi and Ellis 1992 (western corn rootworm egg hatch in the laboratory; compared)
  - Delahaut, Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087), University of Wisconsin–Extension, 2005, revised 2012 (adult beetles present at 1,300 degree days above 50 °F; compared)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's corn rootworm page (the season, the first beetles at Arlington, scouting and thresholds)
  - Dean and Hodgson, Iowa State University, 2024, and Iowa State's Biology and Ecology of Corn Rootworm (peak hatch in central Iowa; compared)
---

## What it predicts

Northern and western corn rootworms spend the winter as eggs in the soil of cornfields. The larvae that hatch in late spring feed on corn roots, which can cause plants to lodge after storms. The beetles that follow in midsummer feed on silks and pollen and lay next year's eggs. The model gives:

- **Egg hatch**: how fast eggs are hatching.
- **Larvae feeding on roots**: how many larvae are feeding, compared with their peak. This is the risk, from 0 to 1.
- **Beetles**: how many beetles are out, compared with their peak.
- **Dig and rate roots for larval injury**: the days from when half the larvae have finished feeding until 95 % have, when root injury is easiest to see.

## How it works

Degree days are counted from January 1 in air temperature by the single-sine method, base 52 °F with no upper limit. The base comes from a study of northern corn rootworm eggs from Wisconsin fields (Apple, Walgenbach and Knee 1971) and agrees with a Minnesota study (Chiang and Sisson 1968). The Wisconsin study used air temperatures from a weather station a mile from its plot and didn't say how it counted degree days; the single sine from January 1 is our choice, and little warmth above 52 °F builds up before mid-April.

- **Egg hatch.** In the laboratory, the first eggs hatched at about 300 degree days. Eggs buried 2 inches deep in a bare Madison plot reached half hatched on June 13, 1970, when air temperatures had given 533 degree days, and had all hatched by July 10, at about 1,000. The model's hatch begins at 300, is half done at 533 and is complete at 1,000, within 3 percentage points of those buried eggs throughout.
- **Larvae.** Larvae feed for about 550 degree days from hatch until they pupate, as they did in New York cornfields (Davis, Brenes and Allee 1996), about a month in July.
- **Pupae and beetles.** The pupa in the soil takes about 200 degree days more, as in a laboratory study (Jackson and Elliott 1988), so the beetles come about 750 degree days after the eggs hatch: half are out at about 1,283. The first beetles come at about the 1,300 degree days above 50 °F at which UW–Madison's degree-day table has adult beetles present.
- **One generation a year.** Eggs laid in August hatch the next spring.

In AgWeather's long-term averages (1996–2025), half the eggs hatch around June 14 at Arlington, June 18 at Hancock and June 26 at Rhinelander. Larvae peak around July 3, July 7 and July 17. The window to dig roots runs from about July 15 to 27 at Arlington and July 31 to August 17 at Rhinelander. The first beetles come around July 15 at Arlington and July 31 at Rhinelander, and half are out around July 25 and August 14.

## How to read it

- **Larvae are feeding on roots by mid-June** in southern Wisconsin (UW–Madison). Control of the larvae (rotation, Bt hybrids, soil insecticides or seed treatments) is chosen before or at planting, from the beetle counts the summer before.
- **Dig roots in the window:** dig plants with a 6-inch core of soil, wash the roots and look for brown, tunneled or pruned roots. Iowa State rates injury from 0 to 3 nodes pruned; 0.25 is its economic injury level. By fall, root decay hides the damage.
- **Fields differ.** Eggs deeper in the soil or under crop residue hatch later than the model's, and the larvae's and beetles' timing comes from New York fields. Dig roots and count beetles by what you find in your fields, and keep looking after the model's dates have passed.
- **Silk clipping:** UW–Madison suggests a spray to protect pollination only when silks are being clipped, pollination is less than half done and there are five or more beetles per plant.
- **Next year's corn:** count beetles from late July through late August. If counts average 0.75 or more beetles per plant in August, plan a rootworm control if the field goes back to corn.

The [corn rootworm topic page](/topics/corn-rootworm) explains the insects, the variants that defeat rotation, and their management in more detail.

## Validation and caveats

- Draft (model version 0.3, beta). Egg hatch follows the Wisconsin study's numbers: hatch begins at 300 degree days, against 304 in the laboratory, and is half done at 533. The larvae and pupae follow New York cornfields and a laboratory study; on the long-term averages the larvae peak in UW–Madison's early to mid-July, and the first beetles come when the long-term averages reach the degree days at which UW–Madison's degree-day table has adult beetles present and, at Arlington, within the July 16 to 24 when an older three-year study there found them. UW–Madison's field crops guide says the first beetles normally appear at Arlington in early July, a week or two before the model's. The model hasn't been compared with field counts of larvae or beetles in Wisconsin. Version 0.2 had the larvae feeding for about 350 degree days and half the beetles out at about 1,075, which ran a week or two early.
- **Northern and western corn rootworm.** The hatch timing is the northern species'. In laboratory studies with temperatures that change as they do in soil, half of western corn rootworm eggs hatched at 509 to 650 degree days (South Dakota and Illinois eggs), within the model's hatch (43 to 78 % hatched); at constant temperatures they took more (Wilde 1971; Levine, Oloumi-Sadeghi and Ellis 1992). Iowa State notes that northern corn rootworm males begin emerging 5 to 7 days after western corn rootworms. The larvae can't be told apart in the field, and one model serves both.
- **Air, not soil.** Eggs and larvae live in the soil, and the model counts air temperature. The Wisconsin study's eggs were 2 inches deep in soil kept bare; in Minnesota, eggs hatched later under crop residue or weeds than in bare soil at the same air temperatures (Chiang and Sisson 1968), so in most fields hatch may come later than the model's. Iowa State and the University of Minnesota give half hatched at 684 to 767 degree days (base 52 °F) in soil temperature; those numbers trace to laboratory studies of western corn rootworm eggs at constant temperatures, not to soil temperatures measured in the field. On the calendar, the model's half hatched at Arlington comes about a week after Iowa State's average peak hatch in central Iowa (June 6).
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
