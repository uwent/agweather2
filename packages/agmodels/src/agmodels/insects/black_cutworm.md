---
id: black-cutworm
status: draft
updated: 2026-11-23
summary: Times black cutworm egg laying, leaf feeding and the cutting stages from degree days after a significant moth capture, your trap date or May 1, so you know when to scout seedlings for cutting.
sources:
  - Luckmann, Shaw, Sherrod and Ruesink 1976 (development times from egg to pupa, Illinois)
  - Krupke and Obermeyer, Timing Black Cutworm Scouting, Purdue Pest&Crop, 2023, and Iowa State's Black Cutworm page (the stage table and the biofix)
  - Wisconsin DATCP black cutworm pheromone trap network, 2021–2023 and 2026 (the default capture date)
  - Story, Keaster, Showers and Shaw 1984 (cutworms in Midwest corn fields), and Kaster and Showers 1984 (black cutworm development outdoors in Iowa; compared)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's cutworms page (scouting and thresholds)
---

## What it predicts

Black cutworm moths fly into Wisconsin from the south in spring and lay eggs on low weeds and crop residue. The young caterpillars feed on leaves; from the fourth of their six stages (instars), they cut seedlings of corn and many vegetables at or below the soil line. The model follows one generation from the moths' arrival:

- **Egg laying**: how many eggs are being laid, compared with its peak.
- **Leaf-feeding caterpillars**: the first three instars, which chew small holes in leaves. Leaf feeding is a sign that cutting may follow.
- **Cutting caterpillars**: the fourth to sixth instars, which cut plants until they pupate in the soil. This is the risk, from 0 to 1, where 1 means every caterpillar of the generation is in the cutting stages.
- **Scout and treat while caterpillars can cut plants**: from the first caterpillars big enough to cut until 90 % have pupated in the soil.

## How it works

Degree days are counted by the single-sine method, base 50 °F with a cutoff at 86 °F, from the biofix: a significant moth capture.

- **The biofix.** Iowa State and Minnesota call a capture significant at eight or more moths in a pheromone trap over two nights; Wisconsin's Department of Agriculture, Trade and Consumer Protection (DATCP) uses nine. If you enter the date of a significant capture near you, the model counts from it. If not, it counts from May 1, a date we fitted to DATCP's black cutworm traps: the median date of the first week with nine or more moths at each trap in 2021–2023 and 2026. The moths ride storm fronts north, so their arrival varies by two weeks or more either way from year to year and place to place, and a date from a nearby trap is much better than the default.
- **Egg laying.** Moths keep arriving and laying eggs for a few weeks after a significant capture. The model spreads egg laying over about 350 degree days after the capture, half of it within about 80. This spread is our estimate, from how long DATCP's pheromone traps kept catching moths after a significant capture.
- **Development.** Each egg hatches about 94 degree days after it is laid, the caterpillar reaches the fourth instar and can cut plants at about 306, and it pupates at about 729 (Luckmann and others, 1976, from laboratory rearing in Illinois).
- **When cutting happens.** The first caterpillars can cut about 310 degree days after the capture, half of them by about 390, and nearly all from about 600. Half have pupated by about 810, and nearly all by 1,000.
- **One generation.** Black cutworms have more than one generation in Wisconsin, but usually only the first, from the moths arriving in spring, damages corn and vegetable seedlings. The model follows only that one.

In AgWeather's long-term averages (1996–2025), counting from May 1, the first caterpillars can cut around June 2 at Arlington, June 4 at Hancock and June 8 at Rhinelander, and half have pupated around June 30, July 3 and July 11. The window to scout and treat runs from about June 2 to July 5 at Arlington, June 4 to July 8 at Hancock and June 8 to July 16 at Rhinelander.

## How to read it

- **Watch the traps.** DATCP's [trap network](https://datcp.wi.gov/Pages/Programs_Services/TrapNetworks.aspx) posts black cutworm counts each spring. Enter the date of a significant capture near you; the model's dates then follow this year's flight rather than an average.
- **Scout from emergence, and closely once leaf feeding appears.** UW–Madison's field crops guide (A3646) advises checking corn every two to three days for at least two to three weeks after it begins to emerge, for leaf feeding and cut, wilted or missing plants, especially in low, wet areas, late-planted fields and fields with winter annual broadleaf weeds.
- **Treat while caterpillars are cutting.** Iowa State and Minnesota suggest treating corn at 2 to 3 % of plants cut while caterpillars are under ¾ inch long, or 5 % once they are larger; A3646 gives 2 to 5 %. UW Vegetable Entomology gives 2 caterpillars per foot of row for snap beans, 4 per foot for potatoes, and more than 5 % of plants damaged for sweet corn.
- **Once most caterpillars have pupated, sprays won't help.**

The [black cutworm topic page](/topics/black-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.3, beta). The development times come from laboratory rearing; the default capture date is set from Wisconsin's trap network.
- The first caterpillars hatch and reach cutting size where Purdue's and Iowa State's stage table puts them (about 90 and 312 degree days after the capture). Cutting lasts longer in the model than in that table, which has the caterpillars pupating from about 641. The model follows the laboratory study's time to pupation, about 90 degree days later, and spreads egg laying over the weeks after the capture rather than starting every egg on the capture day.
- May 1 was the median date of the first week with nine or more moths in 129 trap-years and fell within a week of that week in 60 of them. Because the date was fitted to those same traps, that shows how well it fits them, not a test on new years. The traps are read weekly, so a week with nine moths is an approximation of DATCP's two-night count.
- The spread of egg laying after the capture is our estimate from catches of male moths in pheromone traps, not a measurement of egg laying.
- In several fields in Missouri, Illinois and Iowa, black cutworm caterpillars were much further along than laboratory development times predict (Story and others, 1984). Caterpillars reared outdoors in Iowa grew faster than in the laboratory's constant temperatures: they reached the fourth instar about a day sooner and pupated about 115 degree days sooner (Kaster and Showers, 1984). On those times, cutting would end about five or six days earlier in June than the model shows. Treat the model's dates as a guide to when to scout, not as a forecast of what you will find.
- The model hasn't been compared with reports of cutting in Wisconsin fields.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
