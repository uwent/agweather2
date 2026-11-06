# Service status

What the archive and forecast hold right now: the first hour in the archive, the newest hour from each data source, the last day with daily values, and the forecast in use. Check it to see how current the data are before a scheduled download.

| Field                         | Meaning                                                                             |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| `version`                     | The version of the service's software                                               |
| `service_box`                 | The name of the area the archive covers                                             |
| `archive.first_hour`          | The first hour in the archive (UTC)                                                 |
| `archive.last_hour_by_source` | The newest hour received from each data source                                      |
| `archive.daily_through`       | The last day with daily values                                                      |
| `archive.stale`               | Daily values waiting to be recomputed after an update to the service; usually empty |
| `archive.refreshed_at`        | When these facts were last read from the archive                                    |
| `forecast.cycle`              | The forecast in use, by the time it was issued                                      |
| `forecast.last_hour`          | The forecast's last hour                                                            |
| `forecast.in_use`             | Whether results run through the forecast; `reason` says why not                     |
| `models`                      | The number of models available                                                      |
| `downloads.files`             | The number of yearly data files available from `/downloads`                         |
| `downloads.built_at`          | When the newest of those files was built                                            |
