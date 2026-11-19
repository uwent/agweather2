---
id: imported-cabbageworm
status: draft
updated: 2026-11-19
summary: Rates the risk from imported cabbageworm butterflies and caterpillars in two windows of degree days from January 1, the spring flight and one long window for the summer; the later generations that Wisconsin sources describe aren't modeled separately.
sources:
  - VDIFN's imported cabbageworm model (the threshold, the January 1 start and the two windows, unchanged; its source isn't identified)
  - Liesch and Groves, Imported Cabbageworm, UW–Madison Division of Extension, revised 2026, and UW Vegetable Entomology's imported cabbageworm page (flights and generations in Wisconsin)
  - University of Minnesota VegEdge, Imported Cabbageworm (number of generations)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (scouting and thresholds)
---

## What it predicts

The imported cabbageworm is the caterpillar of the cabbage white butterfly, and the most important caterpillar pest of cole crops in Wisconsin. The butterflies come out of overwintering chrysalises in spring and lay eggs on cruciferous weeds and early cole crops; later generations feed on planted crops through the summer. The model rates the risk from 0 (Very low) to 4 (Very high) in two windows: the spring flight and its caterpillars, and a long window for the summer generations. The rating says where the season is in the model's timing, not how many caterpillars there are.

## How it works

Degree days are counted by the single-sine method, base 50 °F with no cutoff, from January 1.

- **The spring flight:** butterflies from 150 degree days, their flight peaking at 240, and caterpillars feeding through 630.
- **The summer window:** the second flight from 830, peaking at 1,030, with caterpillars feeding through about 2,000. This one long window stands in for all the later generations.
- **The rating** rises a level at a time from Low at a window's start through Moderate and High to Very high, and falls the same way to its end. It's Very high from about 210 to 370 degree days in the first window and from about 965 to 1,355 in the second, and Very low between and after them.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. VDIFN's notes cite a source for its numbers that we haven't been able to identify.

## How to read it

- **Use the windows as a reminder to scout, not as spray dates.** Scout cole crops weekly through the season whatever the model shows. Walk a W-shaped path, examine 25 to 50 plants, and count a plant as infested if it has eggs or caterpillars of the imported cabbageworm, the cabbage looper or the diamondback moth.
- **Treat by the share of infested plants.** For cabbage, Commercial Vegetable Production in Wisconsin gives 10 % in the seedbed, 30 % from transplanting to cupping, 20 % from cupping to early head and 10 % at mature head; for broccoli and cauliflower, 10 % in the seedbed, 50 % from transplanting to the first flower bud or curd, and 10 % after.
- **The rating peaks with the butterflies' flight.** By VDIFN's description, each window peaks with a flight (at 240 and 1,030 degree days) and runs on while the caterpillars feed. Eggs hatch within about a week and caterpillars feed for about 11 to 20 days, so a flight's caterpillars are largest after the rating has passed its peak. Look for eggs and small caterpillars around the peak: insecticides work best on small caterpillars.
- UW–Madison says the second generation, from mid-July, does the most damage; nearly all of its caterpillars grow up on planted cole crops.

The [imported cabbageworm topic page](/topics/imported-cabbageworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's exactly, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The source of the windows isn't identified, and the model hasn't been compared with field counts.
- **The spring flight agrees with UW–Madison.** On AgWeather's long-term averages (degree days for 1996 to 2025), the first flight begins around the start of May in southern Wisconsin, at Arlington and Lancaster, as UW–Madison describes.
- **The summer window comes early and ends early.** In an average year it peaks from late June to early July at Arlington and Lancaster, a week or two before the mid-July flight UW–Madison describes, and it ends in mid to late August.
- **Two windows for several generations.** UW–Madison's fact sheet says there are usually three generations a season, UW Vegetable Entomology three to six and the University of Minnesota three to five, overlapping. The model has two windows, so caterpillars of the late-summer generations aren't covered.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
