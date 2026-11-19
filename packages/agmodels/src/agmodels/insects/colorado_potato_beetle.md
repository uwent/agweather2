---
id: colorado-potato-beetle
status: draft
updated: 2026-11-18
summary: Follows Colorado potato beetle adults, egg masses and larvae through the season from degree days, using curves fitted to a decade of scouting counts in Wisconsin potato fields.
sources:
  - Bradford and Groves, unpublished analysis of Pest Pros' scouting counts, 2014–2025 (UW–Madison Vegetable Entomology)
  - The Crop Risk Tool's Colorado potato beetle model (compared)
---

## What it predicts

The model shows how many Colorado potato beetles a typical field has at each point in the season, by life stage:

- **Adults and larvae** together, per 25 sweeps of a standard sweep net. This is the risk the map shows.
- **Adults** per 25 sweeps.
- **Egg masses** per 10 plants.
- **Larvae** per 25 sweeps.

Each is a typical count for fields in Wisconsin's Central Sands at that point in the season, not a count for your field. Use it to know which stage to scout for and when, and scout to see how many beetles you have.

## How it works

Degree days are counted from January 1 by the single-sine method, base 52 °F with a cutoff at 86 °F. The curves come from scouting counts in commercial potato fields from 2014 to 2025, averaged over several sites in each field on each date. A smooth curve was fitted to the counts of each stage by degree days.

- **Colonization:** overwintered adults begin to appear in fields at about 210 degree days.
- **First eggs** at about 240, with egg masses most numerous around 580.
- **Egg hatch** at about 375; larvae peak around 795.
- **Adults** peak around 590 (the overwintered generation), fall to a low around 960, then peak again around 1,480 as the summer generation emerges. A partial third generation shows around 1,980 in some years.
- **Adults and larvae together** peak around 780 and again around 1,340.

The scouting data end at about 2,310 degree days; after that the counts stay where they were until fall freezes end the season.

## How to read it

- Scout fields from colonization on, and use the stage curves to know whether to look for adults, egg masses or larvae.
- The risk levels compare today's count of adults and larvae with the season's peak: Very high means numbers are near the peak of a typical season.
- The counts are typical values. They run below the average of fields' counts, and individual fields vary widely around them.

## Validation and caveats

- Draft (model version 0.2, beta). The curves describe the scouting data they were fitted to; they haven't yet been tested on years or fields outside it.
- The counts are from the Central Sands' commercial fields. Elsewhere, and in tomato and eggplant, the timing is likely similar, but numbers may differ.
- The Crop Risk Tool used rounded values from the same analysis on degree days from a base of 50 °F, so its events came several days earlier than this model's.
