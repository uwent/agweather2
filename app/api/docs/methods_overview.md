# Sources, corrections and normals

Where our weather data come from and how we adjust them, generated from the code that does it, so it always matches what the service does.

`sources` lists each source and what we use it for: our archive of past weather, the newest hours before the archive's source publishes them, the forecast, locations outside the area our maps cover, and the earlier years of the 30-year normal. Each entry gives the variables it supplies and the dates it supplies them, where those are limited.

`corrections` lists each correction we apply to a source's data: what it corrects and how, the variables it changes, when it was last fitted, and how much it improved the data on a test it was not fitted to. Each links to our technical reports, which give fuller results. `/variables` and each model's inputs name the corrections that change them, and `meta.summary.corrections` lists those applied to the weather in an answer.

`normals` describes how we make the normals that maps and the climate endpoints compare with: each period and the years it takes from our archive and from gridMET, how daily values are pooled across nearby days, how running totals, percentiles, counts of days and freeze dates are computed, how gridMET's earlier years are adjusted to our archive, and when each insect's season opens. Its periods' years follow today's date and the years we hold, so they change at the start of each year.
