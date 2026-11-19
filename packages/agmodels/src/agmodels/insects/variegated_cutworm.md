---
id: variegated-cutworm
status: draft
updated: 2026-11-19
summary: Rates the risk from variegated cutworm caterpillars from degree days since May 1, over a window from 900 to 2,100 degree days peaking at 1,450; its temperature thresholds and its events come from different sources, so the timing is unchecked.
sources:
  - VDIFN's variegated cutworm model (the thresholds, the May 1 start and the window)
  - Coop and Berry 1987, via USPest.org's variegated cutworm model (the events, defined at 41 and 88 °F; peppermint, Oregon)
  - Simonet, Clement, Rubink and Rings 1981 (the 45 °F base the model credits; flight peaks at 900 and 2,160 degree days from January 1, Ohio)
  - MSU Enviroweather's variegated cutworm model (compared)
---

## What it predicts

Variegated cutworm caterpillars cut seedlings and transplants, climb larger plants to eat foliage, buds and flowers, and chew holes in tomatoes and other fruit. They feed at night and hide in the soil by day. The model rates the risk from the caterpillars of the season's first generation from 0 (Very low) to 4 (Very high).

## How it works

Degree days are counted from May 1 by the single-sine method, base 45 °F with a cutoff at 80.1 °F.

- **The window** follows VDIFN's description: egg laying peaks at about 900 degree days, caterpillars are active from about 1,150 to 1,900, and the caterpillar stage ends at about 2,100.
- **The levels.** The level rises a level at a time from 0 at 900 to 4 near 1,450 and falls back the same way to 0 at 2,100. It is Very high from about 1,267 to 1,667.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

In AgWeather's long-term averages (1996–2025) at Arlington, the model reaches 900 degree days around June 23 and its peak around July 15.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces.

## How to read it

- Use the model as a reminder to watch DATCP's black light trap counts of variegated cutworm moths, posted weekly through August, and to scout. Until its timing is checked, trap counts and scouting are the better guide.
- The caterpillars feed at night, so check plants in the morning for fresh damage, and the soil around them in the late afternoon or evening for caterpillars.
- **Tomatoes:** check fruit for damage; UMass suggests treating when 1 % of plants are infested.
- **Mint:** from late June, shake the stems and count the caterpillars that drop onto the soil. Treatment levels in the Pacific Northwest run from 1 to 4 caterpillars per square foot, depending on time to harvest, natural enemies and oil price.

The [variegated cutworm topic page](/topics/variegated-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's formula at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that the timing is right: it hasn't been checked against its source or against field counts in Wisconsin. VDIFN lowered the level for freezes only from November.
- **The thresholds and the events come from different sources.** The events (900, 1,450 and 2,100) match those of Coop and Berry's model for peppermint in Oregon, which counts degree days between 41 and 88 °F. The model runs them at 45 and 80.1 °F, credited to an Ohio study by Simonet and colleagues (1981). That study gives a base of 45 °F with no upper cutoff; 80.1 °F appears in it only as one of the temperatures insects were reared at, and has no known source as a cutoff. A higher base and a lower cutoff both count fewer degree days, so the model's events come later than their source would put them.
- **The start may be wrong too.** In 15 years of light trap catches in Ohio, Simonet and colleagues found moth flights peaking at about 900 and 2,160 degree days (45 °F, no cutoff) counted from January 1. These are close to the model's start and end counted from May 1. In AgWeather's long-term averages at Arlington, 900 degree days counted the Ohio way comes around June 14, about nine days before the model's.
- **What 900 means is unclear.** VDIFN's description calls it the peak of egg laying; the Ohio study, the first flight's peak.
- MSU Enviroweather's model counts from March 1 at a base of 45 °F with no cutoff: first flight at 900, egg laying at 1,070, egg hatch at 1,202 and a second flight at 2,160.
- The levels show where the season stands in the window, not how many caterpillars there are. Later generations aren't modeled.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
