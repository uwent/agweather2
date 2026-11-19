---
id: oak-wilt-vectors
status: draft
updated: 2026-11-19
summary: Estimates the risk of oak wilt spreading to fresh wounds on oaks by its sap beetle vector, from the beetle's flight timed by degree days (base 41 °F) and lowered after mid-July.
sources:
  - Jagemann, Juzwik, Tobin and Raffa 2018 (sap beetle flight in Wisconsin by degree days; the flight percentiles behind the levels)
  - Wisconsin DNR and Wisconsin Council on Forestry, Oak Harvesting Guidelines (the July 15 end of the restricted period)
  - University of Minnesota Extension, Oak wilt in Minnesota (pruning season and wound care)
  - VDIFN's oak wilt model (compared)
---

## What it predicts

Oak wilt spreads to healthy oaks when sap beetles carry spores of the fungus from infected trees to fresh wounds or freshly cut stumps. The model estimates the risk that a wound made on a given day is found by these beetles, from Very low to Very high, by following the flight of the beetle _Colopterus truncatus_ through the season. It applies only where oak wilt and its beetle vectors occur.

## How it works

Degree days are counted from January 1 by the single-sine method, base 41 °F (5 °C), with no upper threshold. The levels follow the flight of _C. truncatus_ in a two-year trapping study in Wisconsin oak stands by Jagemann and colleagues (2018). Its bounds are the study's flight percentiles for this beetle, converted to °F:

- **Very low** before 180 degree days, and **Low** from 180, when the first beetles fly.
- **Moderate** from 231 (5 % of the season's beetles have flown) and **High** from 283 (10 %).
- **Very high** from 388 (25 %) to 913 (75 %), the peak of the flight.
- Then **High** until 1,792 (90 %), **Moderate** until 2,172 (95 %) and **Low** after that.

From July 15 the level drops two steps, to Low at most, and from July 22 one step more. These steps follow the end of Wisconsin's restricted period for oak harvesting on July 15, not the beetles' flight. The model runs from March through July.

## How to read it

- **Don't wound oaks while the beetles fly.** Any level above Very low means some beetles are flying. Prune only in the dormant season, from November through March, and not from April through July.
- If you must prune, or an oak is damaged, while beetles are flying, paint the wound right away with latex paint or shellac. Beetles can reach a wound within minutes, and wounds and stumps can be infected for up to 72 hours.
- **Follow Wisconsin's guidelines for harvesting.** In counties with oak wilt, or within six miles of one, the guidelines restrict harvesting from April 15 to July 15 in the north zone and from April 1 to July 15 in the south zone. Use the model alongside these guidelines, not instead of them.
- A warm March can bring the beetles out early; the model's degree days show when that happens.

The [oak wilt topic page](/topics/oak-wilt) explains the disease, its beetle vectors and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta).
- Given the same degree days and date, the model's level matches VDIFN's, the Wisconsin tool it replaces, in all 1,757 cases tested. In leap years its July steps fall on July 15 and 22, where VDIFN's came a day early.
- The levels haven't been compared with the study's trap catches or other observations of beetle flight.
- The study counted degree days by a modified sine method (Allen 1976); the model uses the single sine with no upper threshold, which may give somewhat different totals.
- The model follows _C. truncatus_ only. The second main vector, _Carpophilus sayi_, flies later: the study caught about two-thirds of them in the north and a quarter in the south after July 15, though few late beetles carried the fungus. The July steps follow the state's calendar rather than these late flights.
- The model was developed in Wisconsin and may not apply elsewhere.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your woodlot.
