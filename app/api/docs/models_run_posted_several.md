# Run several models on your weather

Several models (`"models": ["tar-spot", "white-mold"]`, or `"all"`) on weather you send, in one request. The body is the same as for `POST /models/{model_id}/run`, and the result is shaped like `GET /models/run`. Models that can't run on the variables you sent are listed in `meta.summary.skipped`, with what each one needs. The weather you send is not stored.

## In meta.summary

- `days_provided`, `days_estimated`, `days_grid`, `days_forecast` and `days_missing`: How many days use only the weather you sent, needed an estimate for a missing value, were filled from our archive, came from our forecast, or have no data.
- `skipped`: The models that couldn't run on the weather you sent, by model, each with what it needs.
- Each model's own `meta.summary` holds what `POST /models/{model_id}/run` gives:
  - `days_returned`, `days_forecast` and `days_missing`: The number of rows returned, how many are forecast days, and how many have no data.
  - `estimated_by_input`: For each input the model needed an estimate for, the number of rows on which it was estimated.
  - `missing_by_input`: For each input with days missing in gaps longer than seven days, the number of those days the results depend on, including any before the first day returned. Only present when there are any.
  - `days_projected`: With `projection`, the number of rows past the forecast.
  - `windows`: For an insect, each action window's periods as pairs of first and last days, by window name. With several locations, option sets or projected years, each entry names its `point`, `option_set` or `year`.
  - `option_sets`: When an option is given as `all`, the option values of each `option_set`.
  - `stages`: For a crop model, each growth stage's `code` and `name`, whether it is `estimated` (placed between stages the method predicts), and its `threshold`: the running total, in the column named by `progress` (such as `gdd_total`) and in that column's units, at which the stage begins for the options given. A chart can mark a stage, such as silking, where the running total reaches it. The threshold is null for a stage the options skip, such as leaves a corn hybrid doesn't reach, and for soybeans, whose stages depend on day length as well as temperature. With several option sets, each stage is listed for each, with its `option_set`.
