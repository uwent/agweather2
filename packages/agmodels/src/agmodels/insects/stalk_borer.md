---
id: stalk-borer
status: draft
updated: 2026-11-19
summary: Rates the risk from stalk borer caterpillars moving from grasses and weeds into corn, from degree days since January 1, over a window from 1,110 to 1,700 degree days peaking at 1,400.
sources:
  - VDIFN's stalk borer model (the thresholds and the window)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025 (caterpillars moving into corn from about 1,110 degree days, peaking about 1,650; scouting and thresholds)
  - Iowa State University Extension, Stalk Borer (10 % of caterpillars moving at 1,400 and half at about 1,700)
  - Levine 1983 (development by temperature, base 41 °F; not yet read against the window)
---

## What it predicts

Stalk borer caterpillars hatch in spring from eggs laid on grasses and giant ragweed the fall before. They bore into grass and weed stems, and when they outgrow them, or the weeds are killed, they move into corn, usually in the rows next to a grassy edge. Young corn is most at risk. The model rates the risk from caterpillars moving into corn from 0 (Very low) to 4 (Very high).

## How it works

Degree days are counted from January 1 by the single-sine method, base 41 °F with a cutoff at 86 °F.

- **The window** opens at 1,110 degree days, when UW–Madison expects caterpillars to start moving into corn, and closes at 1,700, the end of the spray window that VDIFN's description gave (1,400 to 1,700).
- **The levels.** The level rises a level at a time from 0 at 1,110 to 4 near 1,400 and falls back the same way to 0 at 1,700. It is Very high from about 1,303 to 1,500.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C); in practice the window has closed by then.

In AgWeather's long-term averages (1996–2025), 1,110 degree days falls around June 12 at Arlington and 1,650 around July 1; at Rhinelander, about two weeks later.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces.

## How to read it

- **Read the window as the season to scout border rows.** UW–Madison and Iowa State advise scouting at about 1,300 to 1,400 degree days, looking for caterpillars in the whorls and frass at entry holes. Start with fields that had stalk borers before and edges next to grassy borders.
- **Time any spray between about 1,400 and 1,700 degree days**, while caterpillars are moving, and before wilting is widespread: by then it's too late.
- **Thresholds:** UW–Madison's guide gives action thresholds by leaf stage, corn price and expected yield. The share of infested plants that justifies a spray is lowest for the youngest corn and rises steeply by the seventh leaf, when plants are unlikely to be killed.
- Map damaged patches at harvest and check them the next year from about 900 to 1,000 degree days.

The [stalk borer topic page](/topics/stalk-borer) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's formula at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that the timing is right: it hasn't been checked against its source or against field counts in Wisconsin.
- **The window mixes two events.** It opens when caterpillars start moving (1,110) and closes at the end of the spray window (1,700), but it peaks at 1,400, the start of that window, rather than at the peak of movement, about 1,650 by UW–Madison's guide. Iowa State puts 10 % of caterpillars moving at 1,400 and half at about 1,700, so the model's peak comes early and its end falls near the middle of the movement.
- **Caterpillars, not moths.** VDIFN's description called 1,110 to 1,650 the moth flight. These numbers mark caterpillars moving into corn; the moths fly from August through October.
- The source of the window hasn't been identified, and Levine's 1983 lab study of the insect's development hasn't yet been read against it.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
