---
id: common-asparagus-beetle
status: draft
updated: 2026-11-19
summary: Rates the risk from the first generation of common asparagus beetle larvae in one window of degree days from January 1, from egg hatch at 105 through a peak at 250 to the last larvae at 405; the overwintered adults and the later generations on the ferns aren't in the model.
sources:
  - VDIFN's common asparagus beetle model (the thresholds, the January 1 start and the window, unchanged; its source isn't identified)
  - Lowenstein, Groves and Liesch, Asparagus Beetle (XHT1137), UW–Madison Division of Extension, revised 2026 (life cycle, scouting and thresholds)
  - University of Minnesota Extension, Asparagus Beetles (life cycle and scouting)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (adults in April)
---

## What it predicts

Common asparagus beetles spend the winter as adults in plant debris and old fern stems in and near the planting. They become active as the spears come up, feed on the spears and lay rows of dark eggs on them. The larvae feed on spears and ferns for about two weeks, then drop to the soil to pupate, and two to three generations develop in a season. The model rates the risk from the first generation's larvae, from 0 (Very low) to 4 (Very high), in one window.

## How it works

Degree days are counted by the single-sine method, base 50 °F with a cutoff at 86 °F, from January 1.

- **The window:** egg hatch begins at 105 degree days, larvae peak at 250, and the last larvae are gone at 405.
- **The rating** rises a level at a time from Low at 105 through Moderate and High to Very high, and falls the same way to 405. It's Very high from about 200 to 300 degree days, and Very low outside the window.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C). It has no effect on this model, since the window closes in early summer.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. VDIFN's description also put the new adults' peak at about 570 degree days, but the model doesn't rate adults.

## How to read it

- **Scout from spear emergence,** whatever the model shows, and on warm, sunny afternoons, when beetles are most active. In large plantings, check 20 plants at each of five places in spring and 10 plants at each of five places in summer.
- **Use the window to watch for eggs and larvae on the spears.** UW–Madison's thresholds for treatment are adults on 5 to 10 % of plants, eggs on 2 % of spears, larvae on 50 to 75 % of plants, or 10 % of plants defoliated. Spot-treat the areas over threshold rather than the whole planting.
- **Keep scouting the ferns through summer.** Later generations feed on the ferns, and defoliation weakens next year's crop; the model doesn't cover them.

The [common asparagus beetle topic page](/topics/common-asparagus-beetle) explains the insect and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's exactly, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The source of the window isn't identified, and the model hasn't been compared with field counts.
- **Only part of the season.** The overwintered adults that feed and lay eggs on spears during harvest, and the later generations that feed on the ferns, aren't in the model.
- **The window may open early.** On AgWeather's long-term averages (degree days for 1996 to 2025), it opens about April 27 at Arlington and May 9 at Rhinelander, peaks in the second half of May and closes between about May 31 and June 11. That puts the first larvae a week or two earlier than UW–Madison's sequence suggests (adults active in early May, eggs hatching about a week later), though Commercial Vegetable Production in Wisconsin has the adults out in April.
- A laboratory study of how fast the eggs and larvae develop at different temperatures (Taylor and Harcourt 1978) could check the window's length; we haven't yet compared it.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
