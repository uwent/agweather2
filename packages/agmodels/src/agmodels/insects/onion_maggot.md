---
id: onion-maggot
status: draft
updated: 2026-11-19
summary: Rates onion maggot fly activity in two flights by degree days from January 1, peaking at 680 and 1,950, the first two of UW–Madison's three flight peaks; the late-summer third flight isn't in the model.
sources:
  - VDIFN's onion maggot model (the thresholds, the January 1 start and the two flights, unchanged; its source isn't identified)
  - UW Vegetable Entomology's onion maggot page (three flights in Wisconsin and their degree days; management)
  - Eckenrode, Vea and Stone 1975 (flights against thermal units, New York), and Liu, McEwen and Ritcey 1982 (Ontario)
  - Salgado and Nault, Onion Maggot and Seedcorn Maggot, Cornell University, 2025 (management at planting)
  - Schuh, Hahn and Wold-Burkness, Cabbage and Onion Maggots, University of Minnesota Extension (row covers in gardens)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (management)
---

## What it predicts

Onion maggot flies lay eggs at the base of onion plants, and the maggots crawl down under the leaf sheaths into the bulb. Seedlings wilt and collapse, leaving thin stands, and bulbs damaged later in the season are unmarketable and can rot in storage. There are three flights of flies a year in Wisconsin. The model rates fly activity from 0 (Very low) to 4 (Very high) for the first two.

## How it works

Degree days are counted by the single-sine method, base 39.2 °F (4 °C) with a cutoff at 86 °F, from January 1.

- **The spring flight:** from 510 degree days, peaking at 680 and ending at 850.
- **The summer flight:** from 1,460, peaking at 1,950 and ending at 2,435.
- **The rating** rises a level at a time from Low at a flight's start through Moderate and High to Very high, and falls the same way to its end. It's Very high from about 625 to 735 degree days in the spring flight and from about 1,785 to 2,110 in the summer flight, and Very low before, between and after them.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. Its two peaks are the first two of the three that UW Vegetable Entomology gives, at about 680, 1,950 and 3,230 degree days. UW's figures use a base of 40 °F counted from when the ground thaws; the difference in base is under a degree. The source of the model's start and end points isn't identified.

## How to read it

- **Protection comes at planting.** By the time damage shows, it's too late to control the maggots. Seed treatments, transplant tray drenches and in-furrow treatments at planting protect the crop; sprays against the adult flies are usually not successful, because the flies move between fields and avoid exposure. Use the model to know when flies are active, not to time sprays.
- **Plan around the spring flight.** Plant new onion fields well away from last year's, and remove cull onions and volunteers, which carry maggots into the next season. In gardens, put row covers on by early to mid-May and keep them on until egg laying ends.
- **Keep a record of stand loss.** UW Vegetable Entomology treats damage of more than 5 to 10 % in last year's crop as the signal to use a preventive treatment at planting.
- **Expect a third flight** in late August and September, which the model doesn't show.

The [onion maggot topic page](/topics/onion-maggot) explains the insect and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's exactly, and its degree days match those of the calculator VDIFN used. This shows that the model was carried over faithfully, not that its timing is right.
- The source of the model's numbers isn't identified. Its timing hasn't been checked against published research (Eckenrode and colleagues' New York trapping and Liu and colleagues' Ontario work, which we have but haven't compared), Wisconsin trap catches or NEWA's onion maggot model.
- **There's no third flight.** UW's scouting calendar has flies active from late August through September, and New York trapping found the same three flights.
- **Flights vary from place to place.** In New York the spring flight's midpoint varied from about 500 to 960 degree days (base 40 °F) between sites and years, so flies can be active outside the model's windows.
- **Every flight counts alike.** In New York the most flies were caught in the spring flight; the model rates both flights' peaks the same.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
