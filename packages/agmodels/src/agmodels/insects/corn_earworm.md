---
id: corn-earworm
status: draft
updated: 2026-11-19
summary: Rates the risk from corn earworm caterpillars in sweet corn ears from degree days after August 1, or after the day you first find eggs or moths, from egg hatch at about 70 degree days to the caterpillars leaving the ears at about 440.
sources:
  - VDIFN's corn earworm model (the thresholds, the August 1 start and the larval window)
  - USPest.org's corn earworm model, from Hartstack et al. 1976 (the likely source; counts from first silk; not yet read)
  - UW Vegetable Entomology, Corn Earworm (egg finds on silks around August 1; trap thresholds)
  - UW–Madison Horticulture and University of Minnesota Extension (the June and late-summer flights)
---

## What it predicts

Corn earworm moths fly into Wisconsin from the south each summer and lay eggs on fresh corn silks. The caterpillars crawl down the silk channel and feed on the kernels at the ear tip, so sprays have to be on the silks before the eggs hatch. The model rates the risk from the caterpillars of one egg-laying event from 0 (Very low) to 4 (Very high), from the time the eggs hatch until the caterpillars leave the ears.

## How it works

Degree days are counted by the single-sine method, base 55 °F with a cutoff at 92 °F, from August 1, which stands in for the day eggs are first found on silks.

- **Egg hatch** at about 70 degree days after the start: the level begins to rise.
- **The peak of caterpillar feeding and damage** at about 275: the level is Very high from about 207 to 330.
- **Caterpillars leave the ears** to pupate in the soil at about 440: the level falls back to 0.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

When you look up a single location, you can change the start date (the biofix) to the day you first find eggs on silks or first catch moths in your traps. Maps count from August 1.

The numbers come from VDIFN, the vegetable forecasting tool AgWeather replaces.

## How to read it

- **Traps decide when to spray.** UW–Madison suggests treating sweet corn from first silk until the silks turn brown when pheromone traps catch 5 to 10 moths a night, or black light traps 3 to 5, for three nights in a row. Check silks for eggs to confirm. DATCP posts weekly corn earworm trap counts from July through September.
- Once you have a date for eggs or moths, set it as the biofix at your location. The model then shows when those eggs hatch and when feeding from them peaks. Silks need protection before the eggs hatch, since caterpillars inside the ear are out of reach.
- Early plantings that silk in late June or July can be hit by the small June flight, which the August 1 start doesn't follow. Watch traps from the time early corn silks.

The [corn earworm topic page](/topics/corn-earworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The model hasn't been compared with Wisconsin's trap counts. VDIFN lowered the level for freezes only from November.
- **The August 1 start is a stand-in.** The moths' arrival changes from year to year with winds from the south, so a fixed date can be weeks off. UW Vegetable Entomology says eggs are typically first found on silks around August 1, and USPest.org's model counts from first silk. The maps can't follow either; your own date at a location can.
- **The June flight is missed.** A small flight usually arrives in June and threatens very early sweet corn; counting from August 1, the model shows no risk then.
- The numbers likely come from USPest.org's model, based on a USDA simulation by Hartstack and colleagues (1976), which hasn't yet been read to confirm them.
- The model follows one egg-laying event. Moths keep arriving through August and early September, so new eggs can be laid after the level has fallen.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
