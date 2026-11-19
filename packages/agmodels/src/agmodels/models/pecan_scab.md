---
id: pecan-scab
status: draft
updated: 2026-11-19
summary: Counts pecan scab hours, warm and humid hours since March 1 or your last fungicide spray, and says when a spray is advised under the Oklahoma Mesonet's rule, from your variety's susceptibility and the waiting period after March 1 or your last spray.
sources:
  - Oklahoma Mesonet, Pecan Scab Advisor (scab hours, the season and the spray thresholds by variety)
  - University of Arkansas System Division of Agriculture, Arkansas Pecan Scab Hours (background)
  - Payne and Smith 2012 (the one published evaluation of scab hours in Oklahoma orchards)
  - The Crop Protection Network's Crop Risk Tool (compared)
---

## What it predicts

Pecan scab infects young leaves, shoots and nut shucks during long spells of high humidity and warm temperatures. The model counts **scab hours**, hours with relative humidity of 90 % or more and a temperature of 70 °F or more, since March 1 or your last fungicide spray. Our weather data run a little drier than a weather station in humid hours, so we count an hour at 88 % humidity or more, the threshold at which our data matched the Oklahoma Mesonet stations' hours at 90 %. It follows the Oklahoma Mesonet's Pecan Scab Advisor, which advises a spray once the total reaches your variety's threshold and a waiting period has passed:

- **Low:** fewer scab hours than half your variety's threshold.
- **Moderate:** half the threshold or more, or the full threshold while the waiting period lasts.
- **High:** the threshold is reached and the waiting period has passed. A spray is advised.

The thresholds are 10 scab hours for highly susceptible varieties, such as Desirable, Pawnee and Wichita (the default); 20 for moderately susceptible ones, such as Caddo, Kiowa and Stuart; and 30 for those of low susceptibility, such as Excel, Kanza and Lakota. The model also shows the scab hours of the last 14 days, the days since March 1 or your last spray, and the days left in the waiting period.

## How it works

Scab hours are counted from hourly weather and added up by calendar day, from March 1, or from the date of your last spray, through August 31. A day with a missing hour adds no scab hours.

The waiting period depends on where the count starts:

- **From March 1,** it is 30 days, so no spray is advised before March 31. Before then, shoots and nuts aren't yet growing enough to be at risk.
- **From a spray,** it is the number of days you expect a spray to protect: 5, 7, 10 or 14 days (14 by default, as the University of Arkansas and the LSU AgCenter assume).

When the model rates a date High, it advises the spray as soon as both conditions hold. After you spray, enter the date so the count and the waiting period start again.

The model runs at locations in 16 pecan-growing states, from the Carolinas and Florida west to California, on weather from Open-Meteo, because AgWeather's own maps don't yet reach the South.

## How to read it

- Choose your variety's susceptibility and the days your fungicide protects. For an orchard of several varieties, choose the most susceptible one you want to protect.
- **High** means the Mesonet's rule calls for a spray. **Moderate** means scab hours are building: plan a spray, or, if you sprayed recently, expect to spray when the waiting period ends if the hours keep building.
- After a spray, enter its date so the count starts again.
- In long wet spells, the waiting period rather than the scab hours sets how often you spray. In dry spells, the scab hours decide.
- Fungicides protect healthy tissue rather than cure infections, so apply them before or soon after wet periods, and rotate FRAC groups from spray to spray.

The [pecan scab topic page](/topics/pecan-scab) explains the disease and its management in more detail.

## Validation and caveats

- Draft (model version 0.3, beta).
- **What changed in version 0.3:** we compared our weather with five Oklahoma Mesonet stations in pecan-growing areas (Okmulgee, Burneyville, Durant, Eufaula and Shawnee), March to August of 2023, 2024 and 2025. Counted at 90 %, our data gave about two-thirds of the stations' scab hours. Counted at 88 %, they matched the stations' totals and gave the same number of sprays under the advisor's rule (about 10 a season), with the first spray a median 2 days early. We also stopped adjusting the humidity with a correction fitted in Wisconsin, which had made spring in Oklahoma too humid.
- **What changed in version 0.2:** version 0.1 rated the total against all three thresholds at once and left the waiting periods to you. It now applies your variety's threshold and the waiting period, as the Mesonet's advisor does.
- The Crop Risk Tool, which this model replaces, counted hours at 92 % humidity and above 70 °F in its code, though its text gave the Mesonet's 90 % and 70 °F. We count at the Mesonet's thresholds, so more hours count than in the tool. Counted at the tool's own thresholds, our daily and running scab hours match the tool's on every day of a year's weather.
- The only published evaluation of scab hours we know of, by Payne and Smith (2012), rated scab in Oklahoma orchards at five locations over eight site-years. It found the temperature and humidity thresholds workable but suggested the humidity threshold might be changed. We found no published test of the 10, 20 and 30 hour thresholds themselves.
- The thresholds haven't been compared with scab in orchards.
- The 88 % is an average. A single station and season matched anywhere from 84 % to 89 %, and the gap between our data and the stations grows through the season: in April and May our data match the stations at 90 %, by August at about 86 %. So in a given year and place the total can run ahead of or behind a station's.
- The comparison covers Oklahoma only. The Southeast is more humid, and our humidity there hasn't been compared with stations.
