# Growing degree days

Daily and running growing degree days at one or more locations, by any method and thresholds, for one or several settings at once (`dd=modified_50_86,sine_48_86`).

Each row is one location and day: `date`, `kind`, the day's minimum and maximum temperature, and for each setting the day's degree days (`dd_<setting>`) and the running total from `biofix` (`dd_<setting>_cum`). Thresholds and results are in °F unless you choose `units=metric`.

When a day's minimum or maximum temperature is missing, it is estimated from the days around it, for gaps of up to seven days, and the day is marked in `temperature_estimated`. A longer gap adds nothing to the running total and is counted as missing.

`targets` reports the day a running total reaches a given value. `projection` continues the series to the end of the year using the weather of each earlier year in the archive, which shows the likely range of dates for a target still ahead.
