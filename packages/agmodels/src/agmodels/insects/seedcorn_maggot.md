---
id: seedcorn-maggot
status: draft
summary: Times each generation's adult flight and the larval feeding that follows from degree days since January 1, and marks the windows when planting a susceptible crop is most likely to be hit.
sources:
  - Sanborn, Wyman and Chapman 1982 (development times by stage)
  - Funderburk, Higley and Pedigo 1984 (field flight peaks, Iowa and Wisconsin)
  - Throne and Eckenrode 1985 (emergence patterns, New York)
  - Olaya-Arenas et al. 2024 (first emergence, New York)
  - UW Vegetable Entomology, seedcorn maggot (vegento.russell.wisc.edu, 2026)
  - University of Minnesota Extension, seedcorn maggot (Potter, reviewed 2018)
  - Crop Risk Tool docs/insects/scm.md; VDIFN db/seeds.rb (seedcorn-maggot)
---

## What it predicts

Seedcorn maggot flies lay eggs in moist, freshly worked soil, especially where seeds are germinating or organic matter is breaking down. The maggots that hatch feed on germinating seed and young seedlings. Damage can only be prevented, not rescued, so the useful question is _when_ a planting is exposed. The model answers it in three ways:

- **Adult flight**: how active the flies are relative to the first generation's peak, for each generation through the season.
- **Larval feeding**: how many maggots are feeding in the soil, timed from the flies that laid them.
- **Avoid planting during adult flight**: the days from 10% to 90% of each generation's flight, when a susceptible crop planted into the field is most likely to attract egg-laying.

Risk adds the two stages together. Flight counts because egg-laying leads to the feeding; feeding counts because it's the damage. Risk of 1 means as active as the first generation's flight at its peak.

## How it works

The model counts degree days from January 1 by the method its sources use: the day's average temperature above 39 °F (3.9 °C), with both the high and the low capped at 84 °F (29 °C) first. This matters. Single-sine degree days, which AgWeather used for this model before, run 70–100 degree days ahead in spring, and would put each event about a week early.

- **First flight.** The over-wintered flies start emerging around 70 degree days (54–94 in New York; Olaya-Arenas et al. 2024). Half have emerged by about 345 (347 in Wisconsin, Sanborn 1981 in Funderburk et al. 1984) and 90% by 495. The curve ends at 650.
- **Larvae.** Females lay eggs a few days after emerging, and eggs hatch about 54 degree days later; together about 82. Larvae then feed for about 367 degree days before pupating (Sanborn et al. 1982). So larvae from the first flight are feeding from about 150 to 1,100 degree days, most of them around 650.
- **Later generations.** Each generation takes about 720 degree days from adult to adult (706 in the lab; Funderburk et al. 1984). The model repeats the first generation every 720 degree days until fall freezes end the season, letting each generation spread a little more than the one before, because individuals develop at slightly different rates (Sanborn et al. 1982). Every generation is assumed to be as large as the first.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season for good.

## How to read it

- Plan plantings of susceptible crops (beans, peas, sweet corn, cucurbits, onions and others) outside the **avoid planting** windows where you can, especially in fields with fresh manure, an incorporated cover crop or green manure, or heavy weeds.
- If planting during a window can't be avoided, that's when an insecticide seed treatment earns its keep, and when shallow planting into warm soil (faster emergence) helps most.
- Risk stays fairly high through summer because the generations overlap. The windows are sharper than the risk curve, so use them for timing.

## Validation and caveats

- Draft (model version 2.0, beta). The degree-day numbers come from laboratory development times and field flight peaks in Wisconsin, Iowa and New York, not from a fit to Wisconsin trap data. Wisconsin DATCP trap captures could check it (PLAN.md, model review).
- Air temperature runs ahead of the soil where the insects develop: Iowa's field generations took about 490 °C·d against the lab's 392 (Funderburk et al. 1984). Later generations may come later than shown.
- Later generations are often smaller than the first, and some flies enter a summer or winter dormancy instead of emerging; the model doesn't predict population size.
- Flies emerge from over-wintered pupae over a long period (Throne and Eckenrode 1985), so a few can be active outside the windows.
