# Freezes

Freeze dates at one or more locations, for one or several temperatures (32, 28 and 24 °F unless you choose others). Each row is one location and temperature: the number of days whose minimum reached it, the last such day before July 1 (`last_spring`), and the first on or after July 1 (`first_fall`), within the period requested.

Freezes are counted from measured daily minimum temperatures only, never from estimates. `missing_days` counts days without a minimum, on which a freeze could have gone unrecorded.

## In meta.summary

- `days_returned`: The number of days searched for freezes, added over every location.
- `days_forecast`: How many of those days are forecast days, including today while it is partly forecast.
- `days_missing`: How many of those days have no data.
- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
