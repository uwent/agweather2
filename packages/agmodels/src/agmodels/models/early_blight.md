---
id: early-blight-pdays
status: draft
updated: 2026-11-19
summary: Adds up potato physiological days (P-days) from daily high and low temperatures, starting at crop emergence, to show when temperatures have favored early blight of potato and the first fungicide spray is due (about 300 P-days).
sources:
  - Sands, Hackett and Nix 1979 (potato physiological days)
  - Pscheidt and Stevenson 1986 (first sprays at 300 P-days controlled early blight on cultivars of different maturity, Wisconsin)
  - Pscheidt and Stevenson 1988 (the critical period for early blight control on Russet Burbank, after about 400 P-days)
  - UW Vegetable Pathology's potato early blight page (300 P-days from emergence; the weekly average after)
  - The Crop Risk Tool's early blight model (the risk levels; compared)
  - The old AgWeather service at UW Vegetable Pathology's forecast locations (compared)
---

## What it predicts

Early blight of potato builds through midsummer, first on the older leaves. Its first infections set how much disease follows, so protecting the crop at the right time matters most. The model adds up potato physiological days (P-days), a measure of heat for potato like degree days, from crop emergence:

- **P-days**: each day's value, from 0 to 10.
- **P-days since emergence**: the season's total, which sets the risk until it reaches 400.
- **The last 7 days' average**: P-days a day over the past week, which sets the risk after 400.

## How it works

- **P-days.** Sands, Hackett and Nix (1979) built P-days to follow how fast potato plants develop. Development is fastest at 70 °F (21 °C) and stops below 45 °F (7 °C) and above 86 °F (30 °C). Each day's P-days weigh that rate at four temperatures between the day's low and high, so a day held at 70 °F earns the full 10, and a hot or a cold day earns little.
- **The start.** The count starts at crop emergence, when about half the plants are up. If you give a planting date, emergence comes from the [potato emergence model](/models/potato-stages); you can also enter your own emergence date at a location. Otherwise the count starts on May 15. The model runs from May 1 to September 30.
- **The threshold.** UW Vegetable Pathology times the first spray at about 300 P-days from emergence. The threshold comes from Pscheidt and Stevenson's research in Wisconsin: in their 1986 comparison, starting sprays at 300 P-days controlled early blight on cultivars of different maturity. Their 1988 study found that for Russet Burbank, a late-maturing variety, the critical period for control came after about 400 P-days, so first sprays on that variety could wait until then; they said earlier varieties such as Superior would need their own study first. The model keeps 300, the threshold UW uses for all varieties.
- **Risk levels** follow the Crop Risk Tool. Until the total reaches 400 P-days, the total sets the level: **Low** from 200, **Moderate** from 250, **High** from 300 and **Very high** from 350. From 400, the last 7 days' average does: **Very low** below 1 P-day a day, **Low** from 1, **Moderate** from 3, **High** from 5 and **Very high** from 9.

## How to read it

- Once 300 P-days have accumulated since emergence, temperatures have favored early blight infection. UW Vegetable Pathology advises scouting closely and starting protective fungicide sprays then, since first infections build the spores for the rest of the season.
- After that, the week's average shows how strongly temperatures are favoring the disease. Several applications are usually needed through the season. Keep scouting, especially the lower leaves, and follow the [early blight topic page](/topics/early-blight) for fungicide choices and resistance management.
- Over a Wisconsin season from May through September, P-days average about 7 to 8 a day, so after 400 the level most often reads High: Very high in the mildest, most even weeks, and lower in cool or very hot ones. In 2025 near Eau Claire, the level after 400 read High on about 6 days in 10 and Very high on most of the rest.

## Validation and caveats

- Draft (model version 0.2, beta). From the Crop Risk Tool's own inputs for 2025 at a location near Eau Claire, the model's daily P-days and risk levels match the tool's on every day when it weighs the day's temperatures as the tool does. We weigh the day's high in the last of the four terms, as Sands and colleagues wrote it, where the tool weighs the low. On that season this lowered the total from May 15 to September 30 by under 1 % (1,098 P-days against 1,107), and both reached 300 P-days on June 27.
- Against the old AgWeather service at UW Vegetable Pathology's seven forecast locations in Wisconsin, from May 1 to September 30, 2026, our season totals were within 4 % of the old service's at every location.
- The 300 P-day threshold and the levels around it haven't been compared with when early blight appears in Wisconsin fields. The P-day curve was developed for potatoes in Australia and isn't adjusted for Wisconsin varieties.
- The risk switches from the total to the weekly average at 400 P-days, as the Crop Risk Tool and VDIFN did. UW Vegetable Pathology's page describes the weekly average taking over at 300. Between 300 and 400 the model shows High and then Very high by the total, and at 400 the level can drop, from Very high to High in a typical week or lower in a cool one. Treat 300 as the point at which protection should start, whatever the level after it.
- The model is for potato. UW–Madison also times early blight on tomato, pepper and eggplant by P-days, counted from transplanting, but this model lists potato only and hasn't been set up or checked for those crops.
- An estimated emergence date can be off by several days; your own emergence date is better.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
