# Run a model on your weather

Run a model on weather from your own station or network. The model uses the same code as on our weather, so the two results can be compared directly. The weather you send is used to compute the answer and is not stored.

Send hourly data, daily data, or both, as JSON:

```json
{
  "location": { "lat": 43.07, "lng": -89.4 },
  "units": "metric",
  "hourly": {
    "time": ["2026-06-01T05:00Z", "2026-06-01T06:00Z"],
    "air_temperature": [18.2, 17.9],
    "relative_humidity": [88, 91]
  },
  "start": "2026-07-01",
  "options": { "biofix": "2026-06-15" }
}
```

Columns are named as in `/variables`. Each hourly value is for the hour ending at its `time`, given as an ISO date and time with its time zone (`2026-06-01T05:00Z`) or as Unix time in seconds or milliseconds, as Wisconet sends it. Hourly data are combined into days in the location's time zone, as our own data are. The location is required: it sets the time zone, day length and region. A model's settings, such as `biofix`, `planting_date` or its options, go inside `"options"`, as in the example; a field the request doesn't take is refused with a message saying what to send instead. You can also send a CSV file (`Content-Type: text/csv`) with the other settings as query parameters.

Values outside the range a station could plausibly record are treated as missing, with a warning. With `"fill": "grid"`, gaps in your data are filled from our archive for the location's grid cell. With `"extend": "forecast"`, the model continues past your last day using our forecast. By default, the answer depends only on the data you send.

The result has the same columns as `GET /models/{model_id}/run`, with each day's `kind` saying whether its data were `provided`, `estimated`, filled from the `grid` or `forecast`. As with `GET /models/{model_id}/run`, `"first"`, `"last"` and `"since"` (a string, or a list of them) find days in the results, such as `"first": "high"` or `"first": "dd_total:above_450"`. Days missing in gaps longer than seven days are marked in columns ending `_missing`, as `GET /models/{model_id}/run` describes, with a warning. If your data can't supply what the model needs, the response says which variables are missing. A request can include about two years of hourly data.

## In meta.summary

- `days_returned`, `days_forecast` and `days_missing`: The number of rows returned, how many are forecast days, and how many have no data.
- `days_provided`: How many days use only the weather you sent.
- `days_estimated`: How many of the days you sent needed an estimate for a missing value.
- `days_grid`: How many days were filled from our archive, with `"fill": "grid"`.
- `estimated_by_input`: For each input the model needed an estimate for, the number of rows on which it was estimated.
- `missing_by_input`: For each input with days missing in gaps longer than seven days, the number of those days the results depend on, including any before the first day returned. Only present when there are any.
- `days_projected`: With `projection`, the number of rows past the forecast.
- `windows`: For an insect, each action window's periods as pairs of first and last days, by window name. With several locations, option sets or projected years, each entry names its `point`, `option_set` or `year`.
- `milestones`: Without `projection`, for each crop stage, risk level above the lowest and action window (`what` and `name`), the first day it was reached (`date`; for potato volunteer survival, whose risk only falls through the winter, each level below the highest and the day the risk fell to it) through the forecast, or null if it wasn't, the kind of that day (`day_kind`: `observed`, `forecast` and so on), and `before_start`, true when it was reached on the first day returned and may have been reached earlier. With several option sets, a list for each.
- `events`: For each `first`, `last` and `since` sent, what was found, as `GET /models/{model_id}/run` gives it: the `event`, its `kind`, the result it looks at (`output`), the `date` found (or `days` since it, for `since`), its `day_kind`, `before_start` and `missing_days`. With several option sets, a list for each.
- `option_sets`: When an option is given as `all`, the option values of each `option_set`.
