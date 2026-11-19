---
id: pecan-scab
status: draft
updated: 2026-11-19
summary: Counts pecan scab hours, warm and humid hours since March 1 or your last fungicide spray, against the Oklahoma Mesonet's spray thresholds for highly, moderately and less susceptible varieties.
sources:
  - Oklahoma Mesonet, Pecan Scab Advisor (scab hours, the season and the spray thresholds by variety)
  - University of Arkansas System Division of Agriculture, Arkansas Pecan Scab Hours (background)
  - The Crop Protection Network's Crop Risk Tool (compared)
---

## What it predicts

Pecan scab infects young leaves, shoots and nut shucks during long spells of high humidity and warm temperatures. The model counts **scab hours**, hours with relative humidity of 90 % or more and a temperature of 70 °F or more, since March 1 or your last fungicide spray, and rates the total against the spray thresholds for varieties of different susceptibility:

- **Low:** fewer than 10 scab hours.
- **Moderate:** from 10, the threshold for highly susceptible varieties, such as Desirable, Pawnee and Wichita.
- **High:** from 20, the threshold for moderately susceptible varieties, such as Caddo, Kiowa and Stuart.
- **Very high:** from 30, the threshold for varieties of low susceptibility, such as Excel, Kanza and Lakota.

It also shows the scab hours of the last 14 days.

## How it works

The model follows the Oklahoma Mesonet's Pecan Scab Advisor. Scab hours are counted from hourly weather and added up by calendar day, from March 1, or from the date of your last spray, through August 31. A day with a missing hour adds no scab hours.

The model runs at locations in 16 pecan-growing states, from the Carolinas and Florida west to California, on weather from Open-Meteo, because AgWeather's own maps don't yet reach the South.

## How to read it

- Find the level for your variety's susceptibility. The Mesonet recommends a spray once the total reaches your variety's threshold: 10 scab hours for highly susceptible varieties, 20 for moderately susceptible ones and 30 for those of low susceptibility.
- **Check the waiting periods yourself.** The Mesonet also waits until 30 days have passed since March 1, or until the protection period you choose (5 to 14 days) has passed since your last spray. The model doesn't apply these, so a high total soon after a spray doesn't by itself mean another is due.
- After a spray, enter its date so the count starts again.
- Fungicides protect healthy tissue rather than cure infections, so apply them before or soon after wet periods, and rotate FRAC groups from spray to spray.

The [pecan scab topic page](/topics/pecan-scab) explains the disease and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- The Crop Risk Tool, which this model replaces, counted hours at 92 % humidity and above 70 °F in its code, though its text gave the Mesonet's 90 % and 70 °F. We count at the Mesonet's thresholds, so more hours count than in the tool. Counted at the tool's own thresholds, our daily and running scab hours match the tool's on every day of a year's weather.
- Our scab hours haven't been compared with the Mesonet's advisor at its stations, and the thresholds haven't been compared with scab in orchards.
- Scab hours depend on Open-Meteo's humidity, which hasn't been compared with weather stations in the South.
