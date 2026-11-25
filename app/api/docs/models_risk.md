# Risk today

Each model's risk at one location on one day (today unless you choose another), as a list with a row for each model: its name, group and version, the day's `kind`, `risk_level` and `risk_label` (with `risk_value` for an insect's activity, whose risk is a continuous value), whether the day is `in_season`, and with a `planting_date` the crop's `susceptibility`.

Without `models`, the list includes every model that is in season and was developed for the location's region. When you name models, each one is listed, and `reason` explains why a model reports no risk on that day.

`missing_days` counts the days, up to the day asked for, that the model's weather is missing in gaps longer than the seven days we fill with estimates. Its running totals add nothing for those days, so its risk may be late; a warning names the models with any.

## In meta.summary

- `models`: The number of rows, one for each model listed and each of its option sets.
- `option_sets`: When an option is given as `all`, the option values of each `option_set`, by model.
