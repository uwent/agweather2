---
id: colorado-potato-beetle
status: draft
updated: 2026-11-21
summary: Follows Colorado potato beetle adults, egg masses and larvae through the season, by degree days or calendar date, using curves fitted to a decade of scouting counts in central Wisconsin's potato fields.
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

Each is a typical count for commercial potato fields in central Wisconsin at that point in the season, not a count for your field. Use it to know which stage to scout for and when, and scout to see how many beetles you have.

## How it works

The curves come from scouting counts in commercial potato fields in central Wisconsin, mostly the Central Sands, from 2014 to 2025. Each visit's count is the average of the scout's count across the field and the counts at its edges and in hot spots, where the scout recorded them. A smooth curve was fitted to the counts of each stage by degree days, counted from January 1 by the single-sine method, base 52 °F with a cutoff at 86 °F.

- **Colonization:** overwintered adults begin to appear in fields at about 205 degree days (about May 22 in a typical year in central Wisconsin).
- **First eggs** at about 215, with egg masses most numerous around 530 (mid-June).
- **Larvae** begin to show at about 400 degree days and peak around 735 (early July).
- **Adults** peak around 560 (the overwintered adults, mid-June), fall to a low around 905, then peak again around 1,450 (early August) as first-generation adults emerge. Some of them lay eggs before leaving for their winter sites, and egg masses rise again from about 1,860.
- **Adults and larvae together** peak around 735, dip slightly around 975 and peak again around 1,325. Between the peaks they stay near their highest, so risk stays high through midsummer.

You can also read the same curves by **calendar date**, which gives the typical central Wisconsin season: colonization about May 22, the overwintered adults' peak about June 18, the larval peak about July 2 and the first-generation adults' peak about August 5. Degree days move these dates with each year's weather; the calendar doesn't.

The numbers vary from year to year more than the timing does: fits by year show some years' counts well below others' at the same degree days. The curves end where the scouting data become sparse, at about 2,180 degree days or early September; after that the counts stay where they were until fall freezes end the season.

## How to read it

- Scout fields from colonization on, and use the stage curves to know whether to look for adults, egg masses or larvae.
- The risk levels compare today's count of adults and larvae with the season's peak: Very high means numbers are near the peak of a typical season.
- The counts are typical values for fields that were treated at planting and sprayed for the beetle. They run below the average of fields' counts, and individual fields vary widely around them.

## Validation and caveats

- Draft (model version 0.3, beta). Refitted with each year left out, the curves described a held-out season's counts better than no curve, and their events moved little (within about 20 degree days or 2 days).
- In these fields the calendar timed a held-out year's events as well as degree days did: colonization and the season's peaks varied little from year to year. The fields lie close together, so the data can't show how the timing shifts farther north or south, which is where degree days should do better.
- The counts are from central Wisconsin's commercial fields. Elsewhere, and in tomato and eggplant, the model runs with a warning: the timing is likely similar by degree days, but the numbers may differ, and the calendar dates are central Wisconsin's.
- The Crop Risk Tool used rounded values from an earlier version of the same analysis on degree days from a base of 50 °F, so its events came several days earlier than this model's.
