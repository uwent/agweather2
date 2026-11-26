# Risk today

Each model's risk at one location on one day (today unless you choose another), as a list with a row for each model: its name, group and version, the day's `kind`, `risk_level` and `risk_label` (with `risk_value` for an insect's activity, whose risk is a continuous value), whether the day is `in_season`, and with a `planting_date` the crop's `susceptibility`.

Without `models`, the list includes every model that is in season and was developed for the location's region, and no retired model. A model is in season between the first and last days of its `season` (`GET /api/v2/models/{id}`). Most insects' seasons open at each location on a day of their own: about a week before the 30-year normal temperatures bring the insect's first activity there, or, for an insect tied to a crop, on the day the crop typically reaches its stage (potatoes emerging, apples blooming). Insects that arrive on the wind from the south open on the first day of their `season` everywhere, as do the others where we don't have the normal temperatures (a warning then says so). An insect's season also ends early at a location where fall freezes have ended it. When you name models, each one is listed, and `reason` explains why a model reports no risk on that day. `models=all` lists every model but the retired ones, which are listed only when you name them.

`missing_days` counts the days, up to the day asked for, that the model's weather is missing in gaps longer than the seven days we fill with estimates. Its running totals add nothing for those days, so its risk may be late; a warning names the models with any.

## Several days

Give `start` or `end` in place of `date` for each model's risk on every day of a period, such as the past week and the forecast for a chart of risk over time. The table then has a row for each model and day, beginning with a `date` column, with each model's days together in order. The period runs from `start` (today if you leave it out) through `end` (the forecast's last day if you leave it out), within one calendar year.

Without `projection=true`, the results end with the forecast's last day, and `meta.request` gives the last day included. With `projection=true`, days past the forecast take each model's median risk across the earlier years in the archive, with `projection_years` saying how many years each day has.

Without `models`, the list includes every model that is in season on any day of the period and was developed for the location's region.

## In meta.summary

- `models`: The number of models listed, counting each option set of a model separately. With one day, this is the number of rows.
- `days`: With `start` or `end`, the number of days for each model.
- `option_sets`: When an option is given as `all`, the option values of each `option_set`, by model.
