# Run several models

Several models at one location in one request (`models=tar-spot,white-mold`, or `all`), from January 1 through the forecast. The result holds each model's answer under its identifier, each with its own `meta` and `data`, as `/models/{model_id}/run` gives them.

Options are added as parameters and apply to every model that has them, and `planting_date` applies to every model that involves a crop. The response is JSON only, since it holds one table for each model.

## In meta.summary

- `corrections`: The corrections we applied to the weather we read, each with its version, such as our calibration of the forecast's temperatures.
- Each model's own `meta.summary` holds what `/models/{model_id}/run` gives for one location:
  - `days_returned`, `days_forecast` and `days_missing`: The number of rows returned, how many are forecast days, and how many have no data.
  - `estimated_by_input`: For each input the model needed an estimate for, the number of rows on which it was estimated.
  - `missing_by_input`: For each input with days missing in gaps longer than seven days, the number of those days the results depend on, including any before the first day returned. Only present when there are any.
  - `days_projected`: With `projection`, the number of rows past the forecast.
  - `windows`: For an insect, each action window's periods as pairs of first and last days, by window name. With several locations, option sets or projected years, each entry names its `point`, `option_set` or `year`.
  - `option_sets`: When an option is given as `all`, the option values of each `option_set`.
  - `projection`: With `projection`, how it was made (`mode`), the first projected day (`start`), the earlier years used (`years`), and `milestones`: for each crop stage, risk level and action window (`what` and `name`), in how many of the years it was reached (`reached` of `of`) and the 10th, 50th and 90th percentile dates (`p10`, `p50`, `p90`).
