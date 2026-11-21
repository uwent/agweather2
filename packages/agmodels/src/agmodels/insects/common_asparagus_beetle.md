---
id: common-asparagus-beetle
status: draft
updated: 2026-11-21
summary: Follows common asparagus beetles from the overwintered adults feeding and laying eggs on spears in spring through up to three generations, from degree days since January 1 by UW–Madison's method, and marks when to scout for beetles and eggs.
sources:
  - Delahaut, Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087), UW–Madison Division of Extension (the method, and egg laying at 150–240 degree days)
  - Lowenstein, Groves and Liesch, Asparagus Beetle (XHT1137), UW–Madison Division of Extension, revised 2026 (development times, generations, scouting and thresholds)
  - Taylor 1979, Carleton University (three generations in eastern Ontario)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (adults in April)
---

## What it predicts

Common asparagus beetles spend the winter as adults in plant debris and old fern stems. They become active as the spears come up, feed on the spears and lay rows of dark eggs on them. Feeding scars the spears, and eggs make them unmarketable. The larvae feed on spears and ferns for about two weeks, drop to the soil to pupate, and new beetles emerge to start the next generation on the ferns. The model gives:

- **Adults feeding and laying eggs**: how active the beetles are, compared with the overwintered beetles' peak.
- **Larvae**: how many larvae are feeding, timed from the beetles that laid the eggs.
- **Scout for beetles and eggs**: the days from 10 % to 90 % of each generation's beetles active.

Risk adds the two stages together. Adults count because their feeding and eggs damage the spears during harvest, and larvae because they feed on spears and ferns. A risk of 1 means as active as the spring beetles at their peak.

## How it works

Degree days are counted from January 1 by UW–Madison's method: the day's average of the high and low, with the low raised to 50 °F and the high capped at 86 °F, minus 50 °F.

- **Spring beetles.** UW–Madison's degree-day table puts asparagus beetle egg laying at 150 to 240 degree days. The model's spring curve has 10 % of the beetles active at about 150 and half at about 240.
- **Larvae.** Eggs hatch in about a week, about 100 degree days in late May, and the larvae feed for about 300 degree days. These are estimates from UW–Madison's development times in days, not from a degree-day study.
- **Generations.** A new generation's beetles follow about 600 degree days after the last, for egg, larva, pupa and a few days of feeding before egg laying. That is also an estimate from UW–Madison's days. The model stops at three generations, as found in eastern Ontario; UW–Madison gives two to three.

In AgWeather's long-term averages (1996–2025), the spring beetles become active around April 28 at Arlington, May 1 at Hancock and May 8 at Rhinelander, and half are out by May 10, May 13 and May 20. The first larvae peak in early June. The second generation's beetles peak in late June (early July at Rhinelander), and the third in late July to early August.

## How to read it

- **Scout spears from emergence**, whatever the model shows, on warm, sunny afternoons when beetles are most active. In large plantings, check 20 plants at each of five places in spring and 10 plants at each of five places in summer.
- **Use the scouting window to watch for beetles and eggs on spears.** UW–Madison's thresholds for treatment are adults on 5 to 10 % of plants, eggs on 2 % of spears, larvae on 50 to 75 % of plants, or 10 % of plants defoliated. Spot-treat the areas over threshold rather than the whole planting, and choose a product with a short preharvest interval during harvest.
- **Keep scouting the ferns through summer.** The later generations feed on the ferns, and defoliation weakens next year's crop.

The [common asparagus beetle topic page](/topics/common-asparagus-beetle) explains the insect and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The spring beetles' 10 % and half match the 150 and 240 degree days in UW–Madison's table. The larvae and the time between generations are estimates from UW–Madison's development times in days; no degree-day study of them was available to us. A laboratory study of the beetle's development by temperature (Taylor and Harcourt 1978) could check them; we haven't yet.
- On the long-term averages the beetles come out in late April in the south and early May in the north, as UW–Madison and Commercial Vegetable Production in Wisconsin describe. The model hasn't been compared with field counts in Wisconsin.
- The spotted asparagus beetle, which appears later, isn't modeled.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
