---
id: corn-earworm
status: draft
updated: 2026-11-23
summary: Times corn earworm caterpillars in sweet corn ears from degree days after egg laying, from the day you first find eggs on silks or catch a significant moth flight, or August 15 without a date.
sources:
  - USPest.org's corn earworm model, Oregon State University, from Hartstack et al. 1976 (the method and the caterpillars' development)
  - UC IPM's corn earworm model (the same development times)
  - Coop, Croft and Drapek 1993 (caterpillars' development in sweet corn ears in Oregon; compared)
  - Wisconsin DATCP corn earworm pheromone trap counts, 2021–2026 (the default start date and how egg laying spreads)
  - UW Vegetable Entomology, Corn Earworm, and UW–Madison Horticulture (the flights and trap thresholds)
---

## What it predicts

Corn earworm moths fly into Wisconsin from the south each summer and lay eggs on fresh corn silks. The caterpillars crawl down the silk channel and feed on the kernels at the ear tip, where sprays can't reach them, so silks have to be protected before the eggs hatch. The model follows the eggs laid by one moth flight:

- **Egg laying**: how many eggs are being laid, starting from the day you give (the biofix).
- **Larvae in ears**: how many caterpillars are feeding in the ears, compared with the most at any time. This is the risk to the crop.

## How it works

Degree days are counted by the single-sine method, base 55 °F with a cutoff at 92 °F, from the biofix: the day you first find eggs on silks, or the first week of a significant moth flight in your area. This is USPest.org's corn earworm model, from a simulation by Hartstack and colleagues (1976).

- **Eggs hatch** about 73 degree days after they are laid, and the caterpillars go straight into the ears.
- **Caterpillars leave the ears** to pupate in the soil about 437 degree days after the egg was laid.
- **Eggs are laid over several weeks**, as moths keep arriving. The model spreads them as DATCP's pheromone traps show a flight continuing after its first big week: half the moths in about 141 degree days, roughly 10 days in late August.
- **Without a date, the model starts on August 15,** a date we chose to fit DATCP's pheromone traps, 2021–2026. In those traps the main flight's first week of 35 or more moths (an average of 5 a night) came within a week of August 15 in two thirds of the site-years (a site in one year). Moths arrive with weather from the south, so in some years the main flight comes weeks earlier or later than that.
- **One generation.** The caterpillars' own moths would need about 873 degree days to lay eggs, more than Wisconsin's fall provides.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In a typical year (AgWeather's 1996–2025 averages), eggs laid on August 15 hatch around August 20 in southern and central Wisconsin, and their caterpillars begin leaving the ears around September 19 at Arlington and September 27 at Hancock.

## How to read it

- **Traps decide when to spray.** UW–Madison suggests treating sweet corn from first silk until the silks turn brown when pheromone traps catch 5 to 10 moths a night, or black light traps 3 to 5, for three nights in a row. Check silks for eggs to confirm. DATCP posts weekly corn earworm trap counts from July through September.
- Once you find eggs on silks or see a significant flight, enter that date as the biofix at your location. The model then shows when those caterpillars are in the ears and when they leave. Silks need protection before the eggs hatch.
- Early plantings that silk in late June or July can be hit by a small June flight, which the August 15 start doesn't follow. Watch traps from the time early corn silks, and enter your own date if moths arrive early.

The [corn earworm topic page](/topics/corn-earworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The caterpillars' development times come from work in Texas; USPest.org rates the model partly validated in the Pacific Northwest. Caterpillars reared in sweet corn ears in western Oregon took about as long to grow (Coop and others, 1993), though single caterpillars took up to about a week less or more. They haven't been checked against caterpillars in Wisconsin fields.
- The August 15 default and the spread of egg laying were set from DATCP's pheromone traps, 2021–2026; across those years the main flight's first big week came from late July to early September. Checking against the same traps shows the fit, not a test on new years. The old default, August 1, came a median 15 days before that week.
- DATCP's traps go up around July 1, so the default says nothing about the June flight.
- The model follows one flight's eggs. Moths can arrive in more than one wave; a later wave needs a later date.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
