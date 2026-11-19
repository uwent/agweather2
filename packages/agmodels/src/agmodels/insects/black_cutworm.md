---
id: black-cutworm
status: draft
updated: 2026-11-19
summary: Rates the risk of black cutworm cutting from degree days after May 15, or after a moth flight you enter, over a window from 300 to 1,000 degree days peaking at 700; by Purdue's and Iowa State's stage tables, cutting usually ends by about 640.
sources:
  - VDIFN's black cutworm model (the thresholds, the May 15 start and the window; its source isn't identified with certainty)
  - Krupke and Obermeyer, Timing Black Cutworm Scouting, Purdue Pest&Crop, 2023, and Iowa State's Black Cutworm page (stage table by degree days after a moth flight)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's cutworms page (scouting and thresholds)
---

## What it predicts

Black cutworm moths fly into Wisconsin from the south in spring and lay eggs on low weeds and crop residue. The older caterpillars cut seedlings of corn and many vegetables at or below the soil line. The model rates the risk of cutting from 0 (Very low) to 4 (Very high), counted from the moths' arrival.

## How it works

Degree days are counted by the single-sine method, base 50 °F with a cutoff at 86 °F, from May 15, which stands in for a large moth flight.

- **The window** runs from 300 to 1,000 degree days and peaks at 700. The level rises a level at a time from 0 at 300 to 4 near 700 and falls back the same way to 0 at 1,000; it is Very high from about 567 to 800.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

When you look up a single location, you can change the start date (the biofix) to the day of a large moth flight in your area. Maps count from May 15.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces.

**Stages after a moth flight** (Purdue's and Iowa State's table, base 50 °F):

- Eggs hatch at about 90 degree days, and young caterpillars feed on leaves until about 311.
- Cutting begins with the fourth stage, at about 312, and runs through the sixth, to about 640.
- From about 641 to 989 the insects are pupae in the soil and don't feed.

In AgWeather's long-term averages (1996–2025) at Arlington, counting from May 15, 300 degree days falls around June 8, 640 around June 26 and 700 around June 29.

## How to read it

- **Read the start of the window as the time to scout.** Iowa State and Minnesota define a significant flight as eight or more moths in a pheromone trap over two nights; start scouting before about 300 degree days after it. DATCP's black cutworm trap network posts counts each spring.
- **Corn:** from emergence, check marked areas every two to three days for two to three weeks for leaf feeding and cut, wilted or missing plants, especially in low, wet, weedy spots and late-planted fields. Iowa State and Minnesota suggest treating at 2 to 3 % of plants cut while caterpillars are under ¾ inch long, or 5 % once they are larger; UW–Madison's field crops guide gives 2 to 5 %.
- **Vegetables:** UW Vegetable Entomology gives 2 caterpillars per foot of row for snap beans, 4 per foot for potatoes, and more than 5 % of plants damaged for sweet corn.
- **Use the stage table for when cutting ends.** Once the total passes about 640 degree days after the flight, the caterpillars are pupating and sprays won't help, even though the model's level is still high.

The [black cutworm topic page](/topics/black-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The model hasn't been compared with trap counts or reports of cutting. VDIFN lowered the level for freezes only from November.
- **The peak comes after cutting ends.** The window's start, 300, agrees with the start of cutting, but its peak at 700 and its end at 1,000 fall after the caterpillars have pupated, by the stage table above.
- **May 15 is a stand-in.** The guides count from a significant moth flight, which comes on a different date each year, and moths can arrive well before May 15. Your own date at a location follows it; the maps can't.
- **Egg hatch isn't modeled.** VDIFN's description put egg hatch at about 180 degree days; the stage table puts it at about 90.
- The study behind the window isn't identified with certainty, and the window hasn't been read against the lab studies of the insect's development.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
