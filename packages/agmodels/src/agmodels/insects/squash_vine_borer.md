---
id: squash-vine-borer
status: draft
updated: 2026-11-23
summary: Follows squash vine borer moth flight and egg laying, and the larvae boring in the vines, from degree days since January 1 (modified average, 50/86 °F), and marks when to protect stems during egg laying, from about 825 to 1,240 degree days.
sources:
  - Liesch and Groves, Squash Vine Borer (XHT1136), UW–Madison Division of Extension, 2026 (first moths at 900 degree days, three weeks of egg laying around 1,000)
  - Delahaut, Degree Days for Common Fruit and Vegetable Insect Pests (XHT1087), UW–Madison Division of Extension, 2012 (the degree-day method; egg laying 900–1,000)
  - SDSU Extension, squash vine borer activity estimates (Varenhorst and others, 2023) (egg hatch and larval feeding in degree days)
  - Ruger and Leach, Squash Vine Borer (ENT-0106), Ohio State University Extension, 2026 (emergence at 1,000 degree days; compared)
  - MSU Enviroweather's squash vine borer model (the end of the flight)
  - UW–Madison Vegetable Entomology, squash vine borer (2026) (one generation; emergence after about 1,000 degree days)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (spray timing)
  - Schuh, Hahn and Burkness, Squash Vine Borers, University of Minnesota Extension, reviewed 2026 (traps; start watching the last week of June)
---

## What it predicts

Squash vine borer moths lay their eggs at the base of squash and pumpkin vines in early summer. The larvae that hatch bore into the stems, where sprays can't reach them, and feed there until the vine wilts and dies. Insecticides work only if they're on the stems while eggs are hatching, so the timing of the moths matters. There is one generation a year in Wisconsin. The model follows:

- **Moth flight and egg laying**: how many moths are flying and laying eggs, compared with the flight's peak.
- **Larvae in vines**: how many larvae are boring in the stems.
- **Protect stems during egg laying**: the days from the first moths until three quarters of the season's moths have flown.

Risk is the larvae's, since they do the damage; the moths don't feed. A risk of 1 means as many larvae in the vines as at the season's peak. Act during the window, before the risk rises: once larvae are inside the vines, sprays do little.

## How it works

No research study of squash vine borer timing is known to us, so the model combines the extension guides. Degree days are counted from January 1 by the modified average (UW–Madison's method): the day's high, capped at 86 °F, and low, raised to 50 °F, are averaged, less 50 °F.

- **Moth flight and egg laying.** UW–Madison's fact sheet expects the first moths at about 900 degree days and three weeks of egg laying around 1,000. South Dakota State and Ohio State put emergence at about 1,000, and Michigan State's model has the flight declining from 1,800 and over by 2,000. The model's first moths come at about 825 degree days, half have flown by about 1,085, three quarters by about 1,240, and the last by 1,900. Females lay eggs as they fly, so the one curve stands for both.
- **Larvae.** Eggs hatch about 270 degree days after they're laid, and the larvae feed inside the vines for about 660 degree days, South Dakota State's numbers.
- **The window** runs from the first moths to three quarters of the flight, about 825 to 1,240 degree days: UW–Madison's three weeks of egg laying.

South Dakota State and Ohio State count degree days by the plain daily average, which runs about a week behind UW–Madison's method in a Wisconsin spring, so their 1,000 degree days comes later on the calendar than UW–Madison's 1,000.

In an average year (AgWeather's degree days for 1996 to 2025), the window runs from about June 21 to July 12 at Arlington, June 24 to July 16 at Hancock and July 2 to July 26 at Rhinelander. The most larvae are in the vines in early August in the south and late August in the north.

## How to read it

- Start watching for moths as the window opens, and by the last week of June at the latest. Yellow pans of water with a drop of dish soap catch the moths; pheromone traps show when males are flying but also catch related clearwing moths. Neither kind of trap has a treatment threshold.
- UW–Madison recommends two to three sprays 5 to 7 days apart during the three weeks of egg laying, aimed at newly hatched larvae before they bore into the vines. Protecting plants with runners shorter than 2 feet is particularly important.
- **The window may close too early.** It follows UW–Madison's three weeks of egg laying, but Michigan State's model has moths flying for weeks longer, and photographs of the moths in the upper Midwest put half the sightings about 8 days after the model's half flight, with many after the window. Keep stems protected while moths are still being seen, even after the window closes.
- Check the bases of stems for entry holes and sawdust-like droppings (frass), which show where larvae have bored in before plants wilt.

## Validation and caveats

- Draft (model version 0.2, beta). Built from the timing in extension guides from Wisconsin, South Dakota, Ohio and Michigan, which don't cite the data behind their numbers; the shape of the flight is our judgment across them.
- The model's first moths, half flight and window match the guides' numbers, since it was drawn to them.
- **Moths are seen later than the guides suggest.** Against 235 iNaturalist photographs of moths in the upper Midwest from 2016 to 2026, the first 5 and 10 % of the records came within about 25 degree days of the model's, but half came about 8 days after the model's half, and the last tenth well after the window. A photograph isn't a moth laying eggs, and records follow how common moths are, but the records agree better with Michigan State's long flight than with three weeks of egg laying. The model wasn't fitted to these records, and no trap counts in Wisconsin are known to us.
- The model shows where the season stands, not how many moths or borers there are.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
