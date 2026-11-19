---
id: western-bean-cutworm
status: draft
updated: 2026-11-19
summary: Rates the risk during the western bean cutworm moth flight from degree days since May 1, from a quarter of the flight at about 1,320 degree days to three quarters at about 1,535, peaking at about 1,420.
sources:
  - VDIFN's western bean cutworm model (the thresholds, the May 1 start and the window)
  - Ahmad 1979, as reported by Hanson et al. 2015 (25, 50 and 75 % of the flight at 1,319, 1,422 and 1,535 degree days; the test of that model on Nebraska trap records)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's western bean cutworm page (scouting and thresholds)
---

## What it predicts

Western bean cutworm has one generation a year. The moths emerge from the soil in summer and lay eggs on corn just before tasseling; the caterpillars feed in corn ears and in dry bean pods. The model rates the risk during the moth flight, when eggs are being laid, from 0 (Very low) to 4 (Very high).

## How it works

Degree days are counted from May 1 by the single-sine method, base 50 °F with no upper cutoff.

- **The flight.** The numbers come from a model T. R. Ahmad built in 1979 from black light trap catches in Nebraska: a quarter of the moths have flown by about 1,320 degree days, half by about 1,420 and three quarters by about 1,535.
- **The levels.** The level rises a level at a time from 0 at 1,320 to 4 near 1,420 and falls back the same way to 0 at 1,535. It is Very high from about 1,387 to 1,458 degree days.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces.

## How to read it

- **Traps first.** Set pheromone traps at field edges by July 1 and check them at least weekly. DATCP's trap network posts counts and maps across Wisconsin.
- **When to scout:** UW–Madison advises starting when degree days point to a quarter of the moths having flown, the model's first rise, or when the first moths are caught nearby, and continuing until 7 to 10 days after the peak.
- **How to scout:** check 20 plants in a row at five places, looking at the top leaves and the leaves around the ear for egg masses and small caterpillars. Scout tasseling fields first.
- **Thresholds:** consider a spray when 5 % of field corn plants, or 4 % of processing sweet corn plants, have egg masses or small caterpillars.
- The level falls to 0 at 1,535 while moths are still flying, so keep scouting through the end of the flight.

The [western bean cutworm topic page](/topics/western-bean-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). Version 0.2 corrected the list of crops to corn, sweet corn and dry beans.
- Given the same degree days, the model's level matches VDIFN's formula at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that the timing is right: it hasn't been compared with Wisconsin trap counts. VDIFN lowered the level for freezes only from November.
- **No risk in the flight's first and last quarters.** Because the window runs from 25 % to 75 % of the flight, the model shows no risk while the first quarter of the moths fly and lay eggs, or after three quarters have flown.
- **The method differs from the source's.** Ahmad's model counted degree days from the daily average temperature. The single-sine method counts more on cool days, so the model's dates likely come somewhat earlier than the source's; by how much on Wisconsin weather hasn't been measured.
- **The upper cutoff is unsettled.** The model has none, as Ahmad's had none; UW Vegetable Entomology's page counts with an 86 °F cutoff.
- Tested on Nebraska trap records from 1981 to 2009, Ahmad's model put a quarter of the flight 3 days late on average, from 7 days early to 12 days late, and a newer model counting from March 1 did better (Hanson et al. 2015).
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
