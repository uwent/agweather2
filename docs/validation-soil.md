# Soil temperature against Wisconet

Generated 2026-10-31 by `scripts/compare_soil_wisconet.py`, 2025-01-01 to 2026-10-29, at 80 Wisconet stations (with a sensor at 5 cm: 79, 10: 78, 20: 77, 50: 77, 100: 71). The archive is HRRR's land-surface model at the station's cell; IFS is Open-Meteo's `ecmwf_ifs` from its historical-forecast API (short leads) and ERA5-Land from its archive API (`era5_land`), both at the station's location and taken to the depths the same way. Each depth the potato model reads (2, 4 and 8 in) is set against the station's sensor at 5, 10 and 20 cm. Bias is the source minus the station, in °C; snow-covered hours are those with IFS's snow depth ≥ 2 cm.

## By depth and season (bias / MAE, °C)

| Depth        | Source         | all          | Dec–Feb      | Mar–May      | Jun–Aug      | Sep–Nov      | Nov–Mar, snow | Nov–Mar, bare |
| ------------ | -------------- | ------------ | ------------ | ------------ | ------------ | ------------ | ------------- | ------------- |
| 2 in (5 cm)  | archive (HRRR) | -0.93 / 3.49 | -4.82 / 5.95 | +1.00 / 3.04 | -0.21 / 2.72 | -0.37 / 2.69 | -5.06 / 5.86  | -0.81 / 4.03  |
| 2 in (5 cm)  | IFS            | -1.11 / 2.27 | -3.04 / 3.41 | -0.58 / 1.94 | -0.56 / 2.06 | -0.61 / 1.85 | -3.01 / 3.26  | -1.33 / 2.33  |
| 2 in (5 cm)  | ERA5-Land      | -0.11 / 1.81 | -0.84 / 1.63 | -0.25 / 1.87 | +0.04 / 1.99 | +0.52 / 1.72 | -0.74 / 1.60  | -0.35 / 1.55  |
| 4 in (10 cm) | archive (HRRR) | -0.72 / 3.02 | -4.36 / 5.46 | +1.44 / 2.70 | -0.32 / 2.20 | -0.25 / 2.15 | -4.62 / 5.36  | -0.34 / 3.63  |
| 4 in (10 cm) | IFS            | -1.17 / 2.05 | -3.04 / 3.30 | -0.81 / 1.75 | -0.56 / 1.77 | -0.62 / 1.58 | -3.02 / 3.20  | -1.43 / 2.10  |
| 4 in (10 cm) | ERA5-Land      | -0.10 / 1.61 | -0.88 / 1.54 | -0.30 / 1.66 | +0.12 / 1.72 | +0.55 / 1.49 | -0.74 / 1.51  | -0.44 / 1.41  |
| 8 in (20 cm) | archive (HRRR) | -0.61 / 2.76 | -3.93 / 4.86 | +1.81 / 2.61 | -0.52 / 2.08 | -0.36 / 1.87 | -4.10 / 4.74  | -0.13 / 3.35  |
| 8 in (20 cm) | IFS            | -1.31 / 1.98 | -2.98 / 3.15 | -1.14 / 1.82 | -0.72 / 1.70 | -0.68 / 1.45 | -2.93 / 3.06  | -1.54 / 2.00  |
| 8 in (20 cm) | ERA5-Land      | -0.14 / 1.50 | -0.93 / 1.44 | -0.40 / 1.57 | +0.12 / 1.60 | +0.56 / 1.35 | -0.75 / 1.39  | -0.55 / 1.32  |

## HRRR minus IFS, by month (°C, mean over the hours both have)

What a forecast steps by at the handover, on average, if neither drifts with lead. Beside it, each source's bias against the stations at 4 in.

| Month | 2 in  | 4 in  | 8 in  | archive − station, 4 in | IFS − station, 4 in |
| ----- | ----- | ----- | ----- | ----------------------- | ------------------- |
| Jan   | -2.45 | -1.99 | -1.58 | -5.86                   | -3.71               |
| Feb   | -0.85 | -0.51 | -0.32 | -2.42                   | -2.04               |
| Mar   | +1.59 | +2.28 | +2.86 | +2.06                   | -0.24               |
| Apr   | +1.90 | +2.65 | +3.56 | +1.33                   | -1.26               |
| May   | +1.46 | +1.98 | +2.61 | +0.93                   | -0.93               |
| Jun   | +0.67 | +0.79 | +1.04 | +0.28                   | -0.43               |
| Jul   | +0.38 | +0.22 | +0.17 | -0.42                   | -0.62               |
| Aug   | +0.11 | -0.18 | -0.46 | -0.79                   | -0.61               |
| Sep   | +0.18 | +0.12 | -0.01 | -0.32                   | -0.45               |
| Oct   | +0.16 | +0.35 | +0.41 | +0.03                   | -0.30               |
| Nov   | +0.53 | +0.89 | +0.87 | -0.67                   | -1.57               |
| Dec   | -1.94 | -1.35 | -0.72 | -4.81                   | -3.44               |

5th to 95th percentile of the hourly difference: 2 in -4.5 to +5.0; 4 in -3.9 to +5.1; 8 in -3.3 to +5.2 °C.

## Shifting IFS by the difference at the seam

If HRRR hands over to IFS at hour t, how far is IFS from HRRR d days later: unshifted, shifted by the difference in hour t, or by the mean difference over the 24 hours to t? RMSE (°C) of HRRR − IFS d days on, over every station-hour of the period (HRRR's archive and IFS's short leads stand in for HRRR's f48 and IFS's longer leads). r is the correlation of the difference with itself d days later (each station's mean removed).

| Depth | shift     | 1 d  | 2 d  | 3 d  | 5 d  | 7 d  | 9 d  |
| ----- | --------- | ---- | ---- | ---- | ---- | ---- | ---- |
| 2 in  | none      | 3.29 | 3.29 | 3.29 | 3.29 | 3.29 | 3.30 |
| 2 in  | hour t    | 2.56 | 3.08 | 3.18 | 3.39 | 3.62 | 3.70 |
| 2 in  | 24 h to t | 2.80 | 3.06 | 3.14 | 3.34 | 3.54 | 3.61 |
| 2 in  | r         | 0.69 | 0.55 | 0.52 | 0.45 | 0.37 | 0.35 |
| 4 in  | none      | 3.15 | 3.15 | 3.15 | 3.15 | 3.15 | 3.15 |
| 4 in  | hour t    | 2.21 | 2.71 | 2.84 | 3.07 | 3.29 | 3.40 |
| 4 in  | 24 h to t | 2.45 | 2.73 | 2.83 | 3.05 | 3.25 | 3.35 |
| 4 in  | r         | 0.74 | 0.60 | 0.56 | 0.49 | 0.41 | 0.37 |
| 8 in  | none      | 2.99 | 2.99 | 2.99 | 2.99 | 3.00 | 3.00 |
| 8 in  | hour t    | 1.63 | 2.09 | 2.26 | 2.52 | 2.74 | 2.89 |
| 8 in  | 24 h to t | 1.80 | 2.10 | 2.23 | 2.49 | 2.71 | 2.84 |
| 8 in  | r         | 0.83 | 0.72 | 0.67 | 0.59 | 0.52 | 0.47 |

## IFS's layers against the stations at their middles (bias / MAE, °C)

The stations' value at a layer's middle is linear between their sensors around it (64 cm between 50 and 100). If a layer agrees here but its interpolated depths don't, the interpolation is at fault.

| Layer                        | middle (cm) | all          | Dec–Feb      | Mar–May      | Jun–Aug      | Sep–Nov      |
| ---------------------------- | ----------- | ------------ | ------------ | ------------ | ------------ | ------------ |
| 0_to_7cm                     | 3.5         | -1.10 / 2.25 | -2.96 / 3.37 | -0.63 / 1.95 | -0.60 / 2.05 | -0.56 / 1.81 |
| 7_to_28cm                    | 17.5        | -1.31 / 1.89 | -3.07 / 3.22 | -1.17 / 1.69 | -0.67 / 1.54 | -0.65 / 1.33 |
| 28_to_100cm                  | 64          | -1.87 / 2.12 | -1.98 / 2.08 | -3.10 / 3.14 | -1.90 / 2.18 | -0.44 / 1.01 |
| HRRR's 30 cm, for comparison | 30          | -0.49 / 2.56 | -3.43 / 4.35 | +2.07 / 2.56 | -0.74 / 2.03 | -0.33 / 1.59 |

## Hours below 27 °F, November–March

Hours per station-winter-day, over the station-days on which the station and every source have every hour, and in brackets the share of those days with any. Station soil under snow is insulated; a field the wind has scoured is colder, so a source below the stations isn't necessarily wrong here.

| Depth | station    | archive (HRRR) | IFS        | ERA5-Land  | station-days |
| ----- | ---------- | -------------- | ---------- | ---------- | ------------ |
| 2 in  | 2.27 (14%) | 10.36 (59%)    | 7.09 (41%) | 3.12 (18%) | 16,675       |
| 4 in  | 1.75 (10%) | 9.15 (47%)     | 6.44 (35%) | 2.74 (15%) | 16,358       |
| 8 in  | 1.02 (6%)  | 7.91 (40%)     | 5.83 (30%) | 2.10 (11%) | 16,293       |

## Daily range at 2 in (°C, max − min of the local day)

| Source         | Dec–Feb | Mar–May | Jun–Aug | Sep–Nov |
| -------------- | ------- | ------- | ------- | ------- |
| station (5 cm) | 0.91    | 4.85    | 5.69    | 3.70    |
| archive (HRRR) | 6.95    | 10.22   | 10.15   | 9.35    |
| IFS            | 3.35    | 6.50    | 7.65    | 6.39    |
| ERA5-Land      | 1.28    | 6.17    | 6.94    | 5.75    |
