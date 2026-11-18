# Validation reports

Technical reports on how AgWeather's data and models compare with measurements, published sources and other systems. Each says what was compared, the numbers, and the command that reproduces it. The methods page links the weather reports behind each correction (D92); each model page links its model's report (D98).

- `weather/`: the archive, the forecast, the normals and Open-Meteo against stations (Wisconet, ACIS) and gridMET, and the corrections fitted to them.
- `legacy/`: v2 against the old AgWeather API and its callers (D54: the old API is a reference, not the truth).
- `models/`: one report per model, `<model id>.md`, with its sources and what we took from each, the choices and differences from other systems, its checks (against its sources' numbers, other systems on the same weather, and observations) and its limits. Tables a script writes in full go in `models/<model id>/`. A model's spec summarizes each check for the public (`agmodels.spec.Check`), and a test fails if a number there isn't in the report section it links to.
- `data/`: the observations and reference tables the checks read, one folder per dataset with a README giving its source, date and caveats. Only small, public datasets are kept here; large downloads are fetched by the scripts that use them.
