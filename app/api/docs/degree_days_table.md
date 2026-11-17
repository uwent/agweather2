# Degree-day totals

Degree-day totals for many locations and settings in one request, for reports that list several places, such as weekly pest bulletins. Each row is one location and setting: the total from `biofix` (or `start`) to `end`, with the number of days that were estimated, missing or forecast.

Up to 50 locations (`points`) and any number of settings (`dd`) can be combined.

## In meta.summary

- `days_returned`: The number of days the totals cover, added over every location.
- `days_forecast`: How many of those days are forecast days, including today while it is partly forecast.
- `days_missing`: How many of those days have no data.
- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
