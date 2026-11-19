---
id: corn-rootworm
status: draft
updated: 2026-11-19
summary: Rates the risk of corn rootworm larvae feeding on corn roots from air-temperature degree days since January 1, over a window from 329 to 636 degree days peaking at 472; the window closes before the peak of larvae in Wisconsin.
sources:
  - VDIFN's corn rootworm model (the threshold, the January 1 start and the window; species and source not recorded)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's corn rootworm page (the larval peak in early to mid-July; scouting and thresholds)
  - Dean and Hodgson, Corn Rootworm Peak Egg Hatch Is Occurring, Iowa State University Integrated Crop Management News, 2024 (half the eggs hatched at 684–767 soil degree days; compared)
---

## What it predicts

Northern and western corn rootworms spend the winter as eggs in the soil of cornfields. The larvae that hatch in late spring feed on corn roots, which can cause plants to lodge after storms. The model rates the risk of root feeding by the larvae from 0 (Very low) to 4 (Very high). It doesn't follow the beetles that clip silks and lay eggs later in summer.

## How it works

Degree days are counted from January 1 by the single-sine method on air temperature, base 52 °F with no upper cutoff.

- **The window** follows VDIFN's description: the first larvae appear and feed lightly at about 329 degree days, feeding peaks at about 472, and the larval stage ends by about 636.
- **The levels.** The level rises a level at a time from 0 at 329 to 4 near 472 and falls back the same way to 0 at 636. It is Very high from about 424 to 527.

In AgWeather's long-term averages (1996–2025), the window runs from about May 31 to June 21 at Arlington, and from about June 10 to July 3 at Rhinelander.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. One window serves both species, whose larvae can't be told apart in the field.

## How to read it

- **Don't rely on the model for timing.** It runs ahead of UW–Madison's calendar (see below). Larvae are feeding by mid-June and peak in early to mid-July.
- **Roots:** in July or August, dig plants with a 6-inch core of soil, wash the roots and look for brown, tunneled or pruned roots. Iowa State rates injury from 0 to 3 nodes pruned; 0.25 is its economic injury level.
- **Silk clipping:** UW–Madison suggests a spray to protect pollination only when silks are being clipped, pollination is less than half done and there are five or more beetles per plant.
- **Next year's corn:** if counts in August average 0.75 or more beetles per plant, plan a rootworm control if the field goes back to corn.

The [corn rootworm topic page](/topics/corn-rootworm) explains the insects, the variants that defeat rotation, and their management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The model hasn't been compared with field observations.
- **The window closes too early.** On the long-term averages it ends in late June in southern Wisconsin and early July in the north, before the early to mid-July peak of larvae that UW–Madison describes.
- **Air, not soil.** The eggs and larvae live in the soil, and the model counts air temperature. Which species, and whether air or soil temperature, the numbers were made for isn't recorded. Iowa State times egg hatch by soil temperature instead (half the eggs hatched at 684 to 767 degree days, base 52 °F, from January 1), and soil totals can't be set directly against the model's air totals.
- The source of 329, 472 and 636 hasn't been identified; UC IPM's northern corn rootworm model and a lab study of western corn rootworm development (Jackson and Elliott 1988) are the leads to check.
- After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C); in practice the window has closed by then.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
