---
id: alfalfa-weevil
status: draft
updated: 2026-11-19
summary: Marks the alfalfa weevil's life stages from degree days since January 1 (base 48.2 °F), from egg hatch at 300 degree days through the larval stages to pupation at 595 and new adults at 815; the risk is High from 440 and Very high from 505 to 595.
sources:
  - The Crop Risk Tool's alfalfa weevil model (the stage table, its thresholds and risk levels)
  - Litsinger and Apple 1973 (larval development times measured in Wisconsin; the table's larval stages match them; compared)
  - Harcourt 1981 (a degree-day model of the weevil's stages in southern Ontario; the table's adult emergence matches it; compared)
  - Bick, Managing Alfalfa Weevil in Wisconsin Alfalfa Fields, UW–Madison Extension, 2025; Jensen, Alfalfa Weevil, Wisconsin Crop Manager, 2018; and Pest Management in Wisconsin Field Crops (A3646), 2025 (scouting, thresholds and the period of heaviest feeding)
  - Hanson and Potter, University of Minnesota Extension, 2023 (the later-developing western strain)
  - MSU Enviroweather's alfalfa weevil model (compared)
---

## What it predicts

Alfalfa weevil larvae feed on the stem tips and leaves of the first alfalfa crop, cutting yield and forage quality. The model marks the weevil's stages through the season from degree days and rates the risk to the crop from 0 (Very low) to 4 (Very high) by the stage the larvae have reached.

## How it works

Degree days are counted from January 1 by the single-sine method, base 48.2 °F (9 °C) with a cutoff at 86 °F (30 °C). Each stage begins at a fixed total and sets the level until the next:

- **300 degree days: egg hatch, begin scouting.** Low.
- **370: second-stage larvae.** Moderate.
- **440: third-stage larvae.** High.
- **505: fourth-stage larvae**, the largest, which do most of the feeding. Very high.
- **595: pupae, end of scouting.** Moderate.
- **815: new adults emerge.** Low.
- **1,000: adults leave the field and rest for the summer.** Very low.

The table comes from the Crop Risk Tool, which cites no study for it. Its larval stages match development times measured in Wisconsin by Litsinger and Apple (1973), and its adult emergence matches Harcourt's 1981 model from southern Ontario.

## How to read it

- **Start checking fields at about 300 degree days**, first on warm, south-facing slopes and sandy knolls, where feeding usually shows first.
- **How to scout:** pick 50 stems at random across the field and count those with tip feeding. A sweep net shows whether larvae are present, but don't base a decision on sweep counts.
- **First crop:** treat when 40 % of stems show feeding and the field is more than a week from harvest. If it is within 7 to 10 days of harvest, cut it early instead.
- **Keep checking after 595** while larvae are still feeding. UW–Madison puts the heaviest feeding at about 600 to 800 degree days, later than the model's peak (see below).
- **After cutting:** check the stubble 4 to 5 days after harvest. Treat if larvae are still active and 50 % of stems show feeding, or if larvae or adults are present and there is no regrowth 3 to 4 days after harvest.

The [alfalfa weevil topic page](/topics/alfalfa-weevil) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- On the weather of Eau Claire, Wisconsin, in 2025, the model's level matched the Crop Risk Tool's on all 365 days. The tool's degree days ran up to 7.7 higher by late summer, because it skips the 86 °F cutoff on some hot days, but no stage began on a different day.
- After egg hatch, each larval stage begins within 3 degree days of Litsinger and Apple's development times, and adult emergence at 815 is within 2 of Harcourt's 817. The two highest levels, from 440 to 595, lie close to the period when Harcourt found most feeding damage. We found no published source for egg hatch at 300 degree days from January 1.
- **The peak may come early.** UW–Madison puts the heaviest feeding at about 600 to 800 degree days (base 48 °F), when the model has already marked the end of scouting.
- **Mixed sources.** The table combines Litsinger and Apple's development times, counted by a different method from each larva's own hatch, with Harcourt's degree days counted from April 1, on one total from January 1. It treats all eggs as hatching at 300.
- **One base for every stage.** Litsinger and Apple found that eggs develop above 50 °F, not 48.2 °F. Some eggs are laid the autumn before, so first hatch also depends on when eggs were laid.
- Minnesota reports a western strain of the weevil that develops 1 to 2 weeks later than the eastern strain on which degree-day models are based.
- Each stage starts on one day for the whole population; in the field, stages overlap. You can't enter an observed stage to reset the later ones, as MSU Enviroweather's model allows.
- The model hasn't been compared with weevil counts or tip feeding in Wisconsin fields.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
