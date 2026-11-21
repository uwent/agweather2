---
id: corn-rootworm
status: draft
updated: 2026-11-21
summary: Times corn rootworm egg hatch, larvae feeding on corn roots and the beetles that follow from air-temperature degree days since January 1 (base 52 °F), on Wisconsin's northern corn rootworm study, and marks when to dig and rate roots.
sources:
  - Apple, Walgenbach and Knee 1971 (northern corn rootworm egg hatch, Madison, Wisconsin; the base and the hatch)
  - UC IPM, northern corn rootworm degree-day models (Apple et al.'s numbers; the single-sine method)
  - Delahaut, Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087), UW–Madison Division of Extension (beetles at 1,300 degree days above 50 °F)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's corn rootworm page (larvae feeding about three weeks; the season; scouting and thresholds)
  - Dean and Hodgson, Iowa State University, 2024, and Iowa State's Biology and Ecology of Corn Rootworm (half the eggs hatched at 684–767 soil degree days; peak hatch in central Iowa; compared)
---

## What it predicts

Northern and western corn rootworms spend the winter as eggs in the soil of cornfields. The larvae that hatch in late spring feed on corn roots, which can cause plants to lodge after storms. The beetles that follow in midsummer feed on silks and pollen and lay next year's eggs. The model gives:

- **Egg hatch**: how fast eggs are hatching.
- **Larvae feeding on roots**: how many larvae are feeding, compared with their peak. This is the risk, from 0 to 1.
- **Beetles**: how many beetles are out, compared with their peak.
- **Dig and rate roots for larval injury**: the days from when half the larvae have finished feeding until 95 % have, when root injury is easiest to see.

## How it works

Degree days are counted from January 1 in air temperature by the single-sine method, base 52 °F with no upper limit. The base comes from a study of northern corn rootworm eggs from Wisconsin fields (Apple, Walgenbach and Knee 1971). The study didn't say how it counted degree days or from what date; the single sine from January 1 is our choice, and little warmth above 52 °F builds up before April.

- **Egg hatch.** In the laboratory, the first eggs hatched at about 300 degree days. Eggs buried in a Madison field reached half hatched on June 13, 1970, when air temperatures had given 533 degree days. The model's hatch begins at 300, is half done at 533 and runs over about four weeks.
- **Larvae.** Each larva feeds for about three weeks (UW–Madison), about 350 degree days in late June and early July.
- **Beetles.** UW–Madison's degree-day table puts the beetles at 1,300 degree days above 50 °F, which in an average year is about 1,075 above 52 °F. The model has half the beetles out then.
- **One generation a year.** Eggs laid in August hatch the next spring.

In AgWeather's long-term averages (1996–2025), half the eggs hatch around June 14 at Arlington, June 18 at Hancock and June 26 at Rhinelander. Larvae peak around June 24, June 28 and July 7. The window to dig roots runs from about July 4 to 17 at Arlington and July 19 to August 3 at Rhinelander, and half the beetles are out around July 15 at Arlington and July 31 at Rhinelander.

## How to read it

- **Larvae are feeding on roots by mid-June** in southern Wisconsin (UW–Madison). Control of the larvae (rotation, Bt hybrids, soil insecticides or seed treatments) is chosen before or at planting, from the beetle counts the summer before.
- **Dig roots in the window:** dig plants with a 6-inch core of soil, wash the roots and look for brown, tunneled or pruned roots. Iowa State rates injury from 0 to 3 nodes pruned; 0.25 is its economic injury level. By fall, root decay hides the damage.
- **Silk clipping:** UW–Madison suggests a spray to protect pollination only when silks are being clipped, pollination is less than half done and there are five or more beetles per plant.
- **Next year's corn:** count beetles from late July through late August. If counts average 0.75 or more beetles per plant in August, plan a rootworm control if the field goes back to corn.

The [corn rootworm topic page](/topics/corn-rootworm) explains the insects, the variants that defeat rotation, and their management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). Egg hatch follows the Wisconsin study's numbers: hatch begins at 300 degree days, against 304 in the laboratory, and is half done at 533. The larvae's three weeks and the beetles' timing come from UW–Madison's descriptions and degree-day table; the model hasn't been compared with field observations in Wisconsin.
- **Northern corn rootworm.** The hatch timing is the northern species'. We found no degree-day timing for western corn rootworm hatch to compare; Iowa State notes that northern corn rootworm males begin emerging 5 to 7 days after western corn rootworms. The larvae can't be told apart in the field, and one model serves both.
- **Air, not soil.** Eggs and larvae live in the soil, and the model counts air temperature. Iowa State and the University of Minnesota time hatch by soil temperature (half hatched at 684 to 767 degree days, base 52 °F, from January 1); those numbers can't be set directly against the model's air totals. On the calendar, the model's half hatched at Arlington comes about a week after Iowa State's average peak hatch in central Iowa (June 6).
- **Larvae and beetles may come early.** On the long-term averages, larvae peak in late June in the south and early July in the north, a week or two before UW–Madison's early to mid-July. The model's first beetles come in early July at Arlington, as UW–Madison's field crops guide says, but an older three-year study at Arlington found the first beetles between July 16 and 24, after the model has half of them out (about July 15).
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
