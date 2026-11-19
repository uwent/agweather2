---
id: custom-degree-days
status: draft
updated: 2026-11-19
summary: Counts degree days from any start date with the base, upper threshold, method and unit you choose.
sources:
  - Baskerville and Emin 1969 (the single-sine method)
  - The old AgWeather service's degree-day calculator (compared)
---

## What it predicts

Degree days measure the warmth available for an insect or crop to develop. This model counts them for any setting you choose, so you can follow a published model that AgWeather doesn't offer, or compare settings. It gives each day's degree days and their running total since your start date (the biofix).

## How it works

You choose:

- **The method:**
  - **Single sine** (the default): the day's temperature is drawn as a smooth curve through the minimum and maximum, and the degree days are the area of the curve above the base (Baskerville and Emin 1969). With an upper threshold, the part of the curve above it counts as if it were at the threshold (a horizontal cutoff).
  - **Simple average:** the average of the minimum and maximum, less the base, and zero if that's negative. With an upper threshold, both temperatures are first lowered to it if they're above it.
  - **Modified average,** the method used for corn: as the simple average, but a minimum below the base is first raised to the base.
- **The base and upper threshold:** any values, or no upper threshold. The default is a base of 50 °F with an upper threshold of 86 °F.
- **The unit:** thresholds in °F or °C. A Celsius degree day is 9/5 of a Fahrenheit one, so 900 degree days (°F) are 500 (°C).
- **The start date:** January 1 by default, or any date, such as planting or an insect's first trap catch.

A day with missing temperatures adds nothing to this model's total. The [degree-day calculator](/tools/degree-days) fills short gaps with estimated temperatures and flags them.

## How to read it

- A degree-day total only means something with the base, upper threshold, method and start date the research behind it used. Use the same settings as the model or publication you're following: on a day of 45 and 65 °F with a base of 50 °F, the simple average gives 5 degree days, the single sine about 6.1 and the modified average 7.5.
- Degree days tell you when to look, not what you'll find. Use them with traps and scouting to time field visits and controls.

The [degree days topic page](/topics/degree-days) explains each method and how to choose settings.

## Validation and caveats

- Draft (model version 0.2, beta). Version 0.2 lets the simple average take an upper threshold, as the degree-day calculator does; before, the simple average with the default upper threshold failed.
- The single-sine degree days agree with a numerical integration of Baskerville and Emin's temperature curve within 0.0002 degree days in 8 test cases.
- All three methods match the old AgWeather service's calculator within 0.000001 degree days in 11,781 combinations of thresholds and temperatures. The old calculator's simple average had no upper threshold, so that comparison covers the simple average without one.
- At Waunakee, Wisconsin, from January 1 to October 31, 2026, our single-sine total (base 50 °F, upper 86 °F) was 3,184 degree days, 0.6 % below the old service's 3,203 on its own weather data. The methods are the same; the difference is in the weather data, mostly because the old service's days followed daylight saving time.
- The model offers no double sine, triangle methods or vertical cutoff. Methods based on the daily minimum and maximum can't follow a day whose temperature doesn't rise and fall smoothly, as when a front passes.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
