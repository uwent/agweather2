---
id: black-cutworm
status: draft
updated: 2026-11-23
summary: Times black cutworm egg laying, leaf feeding and the cutting stages from degree days after a significant moth capture, your trap date or May 1, so you know when to scout seedlings for cutting.
sources:
  - Kaster and Showers 1984 (caterpillar development outdoors in weather shelters, Iowa)
  - Luckmann, Shaw, Sherrod and Ruesink 1976 (egg development in the laboratory, Illinois)
  - Krupke and Obermeyer, Timing Black Cutworm Scouting, Purdue Pest&Crop, 2023, and Iowa State's Black Cutworm page (the stage table and the biofix)
  - Wisconsin DATCP black cutworm pheromone trap network, 2021–2023 and 2026 (the default capture date)
  - Story, Keaster, Showers and Shaw 1984 (cutworms in Midwest corn fields; compared)
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
- **Development.** Each egg hatches about 94 degree days after it is laid (Luckmann and others, 1976, from laboratory rearing in Illinois). The caterpillar reaches the fourth instar and can cut plants at about 284 degree days after the egg was laid, and pupates at about 613 (Kaster and Showers, 1984, from caterpillars reared outdoors in weather shelters in Iowa in spring).
- **When cutting happens.** The first caterpillars can cut about 290 degree days after the capture, half of them by about 365, and nearly all from about 575. Half have pupated by about 695, 90 % by about 790, and nearly all by 900.
- **One generation.** Black cutworms have more than one generation in Wisconsin, but usually only the first, from the moths arriving in spring, damages corn and vegetable seedlings. The model follows only that one.

In AgWeather's long-term averages (1996–2025), counting from May 1, the first caterpillars can cut around May 31 at Arlington, June 2 at Hancock and June 7 at Rhinelander, and half have pupated around June 24, June 27 and July 4. The window to scout and treat runs from about May 31 to June 29 at Arlington, June 2 to July 2 at Hancock and June 7 to July 9 at Rhinelander.

## How to read it

- **Watch the traps.** DATCP's [trap network](https://datcp.wi.gov/Pages/Programs_Services/TrapNetworks.aspx) posts black cutworm counts each spring. Enter the date of a significant capture near you; the model's dates then follow this year's flight rather than an average.
- **Scout from emergence, and closely once leaf feeding appears.** UW–Madison's field crops guide (A3646) advises checking corn every two to three days for at least two to three weeks after it begins to emerge, for leaf feeding and cut, wilted or missing plants, especially in low, wet areas, late-planted fields and fields with winter annual broadleaf weeds.
- **Treat while caterpillars are cutting.** Iowa State and Minnesota suggest treating corn at 2 to 3 % of plants cut while caterpillars are under ¾ inch long, or 5 % once they are larger; A3646 gives 2 to 5 %. UW Vegetable Entomology gives 2 caterpillars per foot of row for snap beans, 4 per foot for potatoes, and more than 5 % of plants damaged for sweet corn.
- **Once most caterpillars have pupated, sprays won't help.**

The [black cutworm topic page](/topics/black-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.4, beta). The caterpillars' development times come from rearing outdoors in Iowa, the egg's from the laboratory; the default capture date is set from Wisconsin's trap network.
- The first caterpillars hatch where Purdue's and Iowa State's stage table puts them (about 90 degree days after the capture) and reach cutting size a day or so before it (about 290, against the table's 312). Each caterpillar pupates about 613 degree days after its egg is laid, near the table's 641; because the model spreads egg laying over the weeks after the capture, half have pupated by about 695.
- May 1 was the median date of the first week with nine or more moths in 129 trap-years and fell within a week of that week in 60 of them. Because the date was fitted to those same traps, that shows how well it fits them, not a test on new years. The traps are read weekly, so a week with nine moths is an approximation of DATCP's two-night count.
- The spread of egg laying after the capture is our estimate from catches of male moths in pheromone traps, not a measurement of egg laying.
- Until version 0.4 the model followed development times from constant laboratory temperatures (Luckmann and others, 1976). Caterpillars reared outdoors in Iowa grew faster (Kaster and Showers, 1984), and in several fields in Missouri, Illinois and Iowa black cutworm caterpillars were much further along than the laboratory times predict (Story and others, 1984), so the model now follows the outdoor times, and its window to scout and treat ends about a week sooner. The evidence isn't all one way: in one of the two years of Iowa's field plots the caterpillars grew more slowly than the laboratory times. Treat the model's dates as a guide to when to scout, not as a forecast of what you will find.
- The model hasn't been compared with reports of cutting in Wisconsin fields.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
