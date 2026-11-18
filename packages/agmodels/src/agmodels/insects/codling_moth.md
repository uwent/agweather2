---
id: codling-moth
status: draft
summary: Times codling moth flight and egg hatch in apple orchards from degree days, from your first trap catch or one estimated for your latitude, and marks when to protect fruit during each generation's egg hatch.
sources:
  - Jones, Doerr and Brunner 2008 (the model from January 1, Washington)
  - Jones et al. 2013 (first catch by latitude across North America)
  - Wisconsin DATCP apple pest trap network, 2020–2025 (first catch in Wisconsin orchards)
  - Jones and Wiman 2012; WSU's degree-day development table (flight and egg hatch curves)
  - Riedl, Croft and Howitt 1976 (biofix and first egg hatch, Michigan)
  - Riedl and Croft 1978 (diapause and the size of the second generation)
  - Rock et al. 1993 (the time between flights, Pennsylvania)
  - NEWA's and Enviroweather's codling moth models (compared)
---

## What it predicts

Codling moth larvae tunnel into apples soon after they hatch, so sprays and other controls work only if they're in place while eggs are hatching. The model follows the moths through the season from degree days:

- **Adult flight**: how many moths are flying, compared with the first flight's peak.
- **Egg hatch**: how many eggs are hatching, compared with the first generation's peak. This is the risk to fruit.
- **Protect fruit during egg hatch**: the days from first hatch (1 % of the generation's eggs) to 95 % hatch, for each of the two generations.
- **Size of the second generation**: from early August, how much of a second generation to expect this year at this location.

## How it works

Degree days are counted from January 1 by the single-sine method, base 50 °F with a cutoff at 86 °F. The sources use 88 °F; in Wisconsin the difference is less than one summer day's degree days by the end of the season.

- **First catch (the biofix).** The model times everything from the first moth caught in a pheromone trap. If you enter your own first catch date, the model uses it. If not, it estimates first catch from your latitude. The estimate follows how first catch changes with latitude across 29 North American orchards (Jones et al. 2013), set 120 degree days later to match first catches in Wisconsin orchards in the state's trap network from 2020 to 2025: about 350 degree days at 43 °N in southern Wisconsin and 310 at 46 °N in the north. First catch varies a good deal from orchard to orchard and year to year (by about 130 degree days, or a week or more), so your own trap date is better whenever you have one. Enter the date of the first moth, not of the first sustained catch, which comes later.
- **Flight and egg hatch.** Each follows Washington State University's codling moth model, counted from first catch. Eggs begin to hatch about 260 degree days after first catch, half have hatched by about 485 and 95 % by about 810.
- **The second generation.** Moths of the second flight begin about 1,000 degree days after first catch, and their eggs hatch about 1,084 degree days after the first generation's.
- **How big the second generation is.** Many larvae of the first generation stop developing and wait for spring (diapause) once days shorten in early August. The degree days from January 1 on August 4 show how many go on to a second generation that summer (Riedl and Croft 1978). Southwest Wisconsin usually gets most of a second generation; Door County and the far north get a small one.
- **No third generation.** In warm years a few moths of a third flight appear in late August in southern Wisconsin, but their larvae rarely mature, so the model stops at two generations.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

## How to read it

- Use pheromone traps to find first catch in your own orchard, and enter that date. The model's dates then follow your orchard rather than an average.
- Time the first cover spray for the start of the **protect fruit** window, about 250–260 degree days after first catch, and keep fruit protected through the window.
- Where the second generation is small, the second window carries less risk, but trap catches decide whether to treat.

## Validation and caveats

- Draft (model version 0.1, beta). The flight and egg hatch curves were developed and tested in Washington. The default first catch is set from Wisconsin trap records; the timing of egg hatch hasn't been checked against Wisconsin observations.
- NEWA's codling moth model sets its default first catch at 404 degree days from January 1, which in Wisconsin's trap network matches the first week with five or more moths rather than the first moth. Without a trap date, AgWeather's first catch comes a few days before NEWA's. With the same trap date, the two agree on first hatch within a day or two.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your orchard; a block in a frost pocket or on a warm slope may run behind or ahead.
