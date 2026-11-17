# Hourly weather

Hourly weather at one or more locations, for the past seven days through the forecast unless you choose other times.

Each row is one location and hour: `time` (the end of the hour, in UTC), `kind` (`observed` or `forecast`), a column for each variable in `vars`, and with `tz=local` the time in the location's own time zone. An hour without data has a `kind` of `null`, and its values are missing. A request can cover up to two years.

## In meta.summary

- `hours_requested`: The number of hours from the start time through the end time.
- `hours_returned`: The number of rows returned, over every location.
- `hours_forecast`: How many of those rows are forecast hours.
- `hours_missing`: How many of those rows have no data (a `kind` of `null`).
