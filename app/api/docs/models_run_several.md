# Run several models

Several models at one location in one request (`models=tar-spot,white-mold`, or `all`), from January 1 through the forecast. The result holds each model's answer under its identifier, each with its own `meta` and `data`, as `/models/{model_id}/run` gives them.

Options are added as parameters and apply to every model that has them, and `planting_date` applies to every model that involves a crop. The response is JSON only, since it holds one table for each model.
