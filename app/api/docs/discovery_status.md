# Service status

What the archive and forecast hold right now: the first hour in the archive, the newest hour from each data source, the last day with daily values, the forecast in use, and the days of the last 30 that are missing any hours. Check it to see how current the data are before a scheduled download.

We use our forecast for 12 hours after it's issued. If a newer one hasn't arrived by then, `forecast.in_use` is false, and the forecast for locations inside our area comes from Open-Meteo until ours is current again (`forecast.fallback`). Our maps show no forecast meanwhile.
