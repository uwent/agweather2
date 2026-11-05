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

Columns are named as in `/variables`. Each hourly value is for the hour ending at its `time`. Hourly data are combined into days in the location's time zone, as our own data are. The location is required: it sets the time zone, day length and region. You can also send a CSV file (`Content-Type: text/csv`) with the other settings as query parameters.

Values outside the range a station could plausibly record are treated as missing, with a warning. With `"fill": "grid"`, gaps in your data are filled from our archive for the location's grid cell. With `"extend": "forecast"`, the model continues past your last day using our forecast. By default, the answer depends only on the data you send.

The result has the same columns as `GET /models/{model_id}/run`, with each day's `kind` saying whether its data were `provided`, `estimated`, filled from the `grid` or `forecast`. If your data can't supply what the model needs, the response says which variables are missing. A request can include about two years of hourly data.
