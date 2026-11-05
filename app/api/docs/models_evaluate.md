# Explore a model

A model's calculation at values you choose, without any weather data: for example, a disease's risk at a range of temperatures and hours of high humidity. This is what the interactive charts on each model's page use.

Send the inputs in a JSON body, as `{"inputs": {"temperature_mean_30day": [18, 22, 26]}}`, using the input names `/models/{model_id}` lists under `explorer`. A list of values gives one row for each; several lists give a row for every combination, up to 10,000 rows. Inputs you leave out take their usual values. Values outside an input's usual range are computed, with a warning.
