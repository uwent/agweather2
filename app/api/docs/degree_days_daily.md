# Growing degree days

Daily and running growing degree days at one or more locations, by any method and thresholds, for one or several settings at once (`dd=modified_50_86,sine_48_86`).

Each row is one location and day: `date`, `kind`, the day's minimum and maximum temperature, and for each setting the day's degree days (`dd_<setting>`) and the running total from `biofix` (`dd_<setting>_cum`). Thresholds and results are in °F unless you choose `units=metric`.

When a day's minimum or maximum temperature is missing, it is estimated from the days around it, for gaps of up to seven days, and the day is marked in `temperature_estimated`. A longer gap adds nothing to the running total and is counted as missing.

`targets` reports the day a running total reaches a given value. `projection` continues the series to the end of the year using the weather of each earlier year in the archive, which shows the likely range of dates for a target still ahead.

`roll=7` adds each setting's degree days over the past 7 days (`dd_sine_50_86_7d`), and `roll_stat=mean` gives their daily average instead, a smoothed rate of accumulation.

## In meta.summary

- `days_returned`: The number of rows returned, over every location.
- `days_forecast`: How many of those rows are forecast days, including today while it is partly forecast.
- `days_missing`: How many of those rows have no data (a `kind` of `null`).
- `days_estimated`: How many rows have degree days worked out from estimated temperatures, where a short gap was bridged.
- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
- `roll`: With `roll`, each window column's source column, statistic and length in days (`columns`), the alignment (`align`), and for each window the first day that includes forecast days (`forecast_from`) and the days whose windows were shortened at the ends of the data (`clipped`).
- `targets`: With `targets`, one entry for each location (`point`), setting (`setting`) and target (`target`, in the request's units): in how many of the series the running total reached it (`reached` of `of`; 1 of 1 without a projection) and the 10th, 50th and 90th percentile dates it was reached (`p10`, `p50`, `p90`; the same date without a projection).
- `projection`: With `projection`, the first projected day (`start`) and the earlier years used (`years`). With several locations, a list with an entry for each location (`point`).
