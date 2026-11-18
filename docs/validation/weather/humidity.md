# Humidity: the archive against Wisconet

Generated 2026-10-31 by `scripts/compare_humidity.py`, 2025-01-01 to 2026-10-27: 80 Wisconet stations, each against its archive cell (URMA/RTMA RH from temperature and dew point at the top of the hour; the station's are hourly means). 1,162,237 paired hours.

## By month

| Month | RH bias (archive − station) | RH MAE | temperature bias (°C) | RH ≥ 90: station / archive (share of hours) | RH ≥ 80: station / archive | leaf wet (station) |
| ----- | --------------------------- | ------ | --------------------- | ------------------------------------------- | -------------------------- | ------------------ |
| Jan   | +0.9                        | 3.3    | +0.16                 | 0.106 / 0.111                               | 0.297 / 0.326              | 0.140              |
| Feb   | +0.8                        | 3.7    | +0.17                 | 0.114 / 0.118                               | 0.316 / 0.334              | 0.134              |
| Mar   | +0.6                        | 3.9    | +0.12                 | 0.182 / 0.182                               | 0.332 / 0.349              | 0.218              |
| Apr   | +0.2                        | 3.8    | +0.12                 | 0.226 / 0.219                               | 0.382 / 0.393              | 0.258              |
| May   | +0.1                        | 4.3    | +0.15                 | 0.142 / 0.125                               | 0.255 / 0.253              | 0.178              |
| Jun   | -0.4                        | 3.9    | +0.17                 | 0.290 / 0.272                               | 0.462 / 0.461              | 0.281              |
| Jul   | -1.2                        | 4.0    | +0.26                 | 0.327 / 0.292                               | 0.518 / 0.513              | 0.314              |
| Aug   | -1.4                        | 3.9    | +0.25                 | 0.401 / 0.366                               | 0.580 / 0.575              | 0.387              |
| Sep   | -0.9                        | 3.9    | +0.18                 | 0.442 / 0.418                               | 0.612 / 0.617              | 0.426              |
| Oct   | +0.1                        | 4.2    | +0.09                 | 0.258 / 0.234                               | 0.437 / 0.451              | 0.309              |
| Nov   | +0.5                        | 3.6    | +0.06                 | 0.214 / 0.211                               | 0.388 / 0.406              | 0.222              |
| Dec   | +0.6                        | 3.1    | +0.17                 | 0.214 / 0.225                               | 0.499 / 0.521              | 0.241              |

## Hours a day

| Station-days           | RH ≥ 90 station | RH ≥ 90 archive | RH ≥ 80 station | RH ≥ 80 archive | leaf wet (station) |
| ---------------------- | --------------- | --------------- | --------------- | --------------- | ------------------ |
| all (48,134)           | 6.02            | 5.68            | 10.24           | 10.46           | 6.38               |
| May–September (22,680) | 7.79            | 7.16            | 11.77           | 11.73           | 7.69               |

May–September daily counts, correlation with the station's leaf-wet hours: station RH ≥ 90 0.81, archive RH ≥ 90 0.71; archive against station RH ≥ 90 0.90.

## Equivalent archive thresholds

The archive RH at or above which there are as many hours as the stations' RH ≥ 90% and as their leaf-wet hours (a share of the hour wet ≥ 0.5), over the paired hours:

| Hours         | station RH ≥ 90 | leaf wet |
| ------------- | --------------- | -------- |
| all           | 89.0            | 88.0     |
| May–September | 88.0            | 88.0     |

## By local hour (May–September), share of hours

| Hour ending | RH ≥ 90 station | RH ≥ 90 archive | leaf wet | RH bias |
| ----------- | --------------- | --------------- | -------- | ------- |
| 00          | 0.493           | 0.441           | 0.499    | -1.0    |
| 01          | 0.536           | 0.487           | 0.538    | -1.1    |
| 02          | 0.576           | 0.538           | 0.569    | -1.0    |
| 03          | 0.612           | 0.578           | 0.598    | -1.1    |
| 04          | 0.643           | 0.611           | 0.623    | -1.2    |
| 05          | 0.673           | 0.644           | 0.645    | -1.2    |
| 06          | 0.695           | 0.667           | 0.664    | -1.2    |
| 07          | 0.662           | 0.607           | 0.640    | -1.9    |
| 08          | 0.514           | 0.440           | 0.519    | -2.4    |
| 09          | 0.303           | 0.248           | 0.311    | -2.6    |
| 10          | 0.176           | 0.149           | 0.150    | -2.3    |
| 11          | 0.117           | 0.099           | 0.095    | -1.8    |
| 12          | 0.086           | 0.075           | 0.079    | -1.4    |
| 13          | 0.069           | 0.062           | 0.071    | -1.1    |
| 14          | 0.058           | 0.056           | 0.067    | -0.6    |
| 15          | 0.056           | 0.053           | 0.071    | -0.4    |
| 16          | 0.058           | 0.056           | 0.073    | -0.2    |
| 17          | 0.065           | 0.063           | 0.079    | +0.2    |
| 18          | 0.075           | 0.072           | 0.084    | +0.7    |
| 19          | 0.096           | 0.100           | 0.095    | +1.5    |
| 20          | 0.153           | 0.156           | 0.147    | +1.8    |
| 21          | 0.259           | 0.239           | 0.254    | +0.8    |
| 22          | 0.365           | 0.322           | 0.372    | -0.4    |
| 23          | 0.437           | 0.388           | 0.445    | -0.8    |

By station (79 with 90 days or more): archive RH ≥ 90 hours over the station's, median 0.96, 10–90% 0.78–1.15.
