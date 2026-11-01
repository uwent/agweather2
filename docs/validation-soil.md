# Soil temperature against Wisconet

Generated 2026-11-01 by `scripts/compare_soil_wisconet.py`, 2025-01-01 to 2026-10-26, at 80 Wisconet stations (with a sensor at 5 cm: 79, 10: 78, 20: 77, 50: 77, 100: 71). The archive is v2's grid at the station's cell (ERA5-Land's soil, D52, where the archive has it); IFS is Open-Meteo's `ecmwf_ifs` from its historical-forecast API (short leads) and ERA5-Land from its archive API (`era5_land`), both at the station's location and taken to the depths the same way. Each depth the potato model reads (2, 4 and 8 in) is set against the station's sensor at 5, 10 and 20 cm. Bias is the source minus the station, in °C; snow-covered hours are those with IFS's snow depth ≥ 2 cm.

## By depth and season (bias / MAE, °C)

| Depth        | Source    | all          | Dec–Feb      | Mar–May      | Jun–Aug      | Sep–Nov      | Nov–Mar, snow | Nov–Mar, bare |
| ------------ | --------- | ------------ | ------------ | ------------ | ------------ | ------------ | ------------- | ------------- |
| 2 in (5 cm)  | archive   | -0.10 / 1.78 | -0.86 / 1.60 | -0.20 / 1.82 | +0.05 / 1.97 | +0.53 / 1.68 | -0.76 / 1.56  | -0.34 / 1.52  |
| 2 in (5 cm)  | IFS       | -1.12 / 2.27 | -3.04 / 3.41 | -0.58 / 1.94 | -0.56 / 2.06 | -0.62 / 1.86 | -3.01 / 3.26  | -1.33 / 2.33  |
| 2 in (5 cm)  | ERA5-Land | -0.11 / 1.81 | -0.84 / 1.63 | -0.25 / 1.87 | +0.04 / 1.99 | +0.52 / 1.71 | -0.74 / 1.60  | -0.35 / 1.55  |
| 4 in (10 cm) | archive   | -0.09 / 1.59 | -0.89 / 1.51 | -0.25 / 1.62 | +0.12 / 1.71 | +0.57 / 1.47 | -0.76 / 1.47  | -0.43 / 1.38  |
| 4 in (10 cm) | IFS       | -1.17 / 2.05 | -3.04 / 3.30 | -0.81 / 1.75 | -0.56 / 1.77 | -0.62 / 1.59 | -3.02 / 3.20  | -1.43 / 2.10  |
| 4 in (10 cm) | ERA5-Land | -0.10 / 1.61 | -0.88 / 1.54 | -0.30 / 1.66 | +0.12 / 1.72 | +0.55 / 1.49 | -0.74 / 1.51  | -0.44 / 1.41  |
| 8 in (20 cm) | archive   | -0.13 / 1.48 | -0.94 / 1.42 | -0.36 / 1.54 | +0.12 / 1.59 | +0.57 / 1.33 | -0.76 / 1.36  | -0.54 / 1.31  |
| 8 in (20 cm) | IFS       | -1.31 / 1.99 | -2.98 / 3.15 | -1.14 / 1.82 | -0.72 / 1.70 | -0.69 / 1.46 | -2.93 / 3.06  | -1.54 / 2.00  |
| 8 in (20 cm) | ERA5-Land | -0.14 / 1.50 | -0.93 / 1.44 | -0.40 / 1.57 | +0.12 / 1.60 | +0.56 / 1.35 | -0.75 / 1.39  | -0.55 / 1.32  |

## Archive minus IFS, by month (°C, mean over the hours both have)

What a forecast steps by at the handover, on average, if neither drifts with lead. Beside it, each source's bias against the stations at 4 in.

| Month | 2 in  | 4 in  | 8 in  | archive − station, 4 in | IFS − station, 4 in |
| ----- | ----- | ----- | ----- | ----------------------- | ------------------- |
| Jan   | +2.36 | +2.36 | +2.20 | -1.29                   | -3.71               |
| Feb   | +1.66 | +1.63 | +1.59 | -0.54                   | -2.04               |
| Mar   | +0.15 | +0.25 | +0.34 | +0.07                   | -0.24               |
| Apr   | +0.73 | +0.92 | +1.22 | -0.27                   | -1.26               |
| May   | +0.21 | +0.42 | +0.69 | -0.54                   | -0.93               |
| Jun   | +0.18 | +0.27 | +0.45 | -0.20                   | -0.43               |
| Jul   | +0.67 | +0.75 | +0.92 | +0.11                   | -0.62               |
| Aug   | +0.99 | +1.05 | +1.17 | +0.43                   | -0.61               |
| Sep   | +1.04 | +1.11 | +1.23 | +0.66                   | -0.45               |
| Oct   | +1.26 | +1.28 | +1.33 | +0.96                   | -0.31               |
| Nov   | +1.25 | +1.25 | +1.25 | -0.35                   | -1.57               |
| Dec   | +2.72 | +2.64 | +2.51 | -0.75                   | -3.44               |

5th to 95th percentile of the hourly difference: 2 in -1.5 to +4.3; 4 in -1.1 to +4.0; 8 in -0.8 to +3.8 °C.

## Shifting IFS by the difference at the seam

If the archive hands over to IFS at hour t (ERA5-Land's last hour), how far is IFS from the archive d days later: unshifted, shifted by the difference in hour t, or by the mean difference over the 24 hours to t? RMSE (°C) of archive − IFS d days on, over every station-hour of the period (IFS's short leads stand in for its longer ones). r is the correlation of the difference with itself d days later (each station's mean removed).

| Depth | shift     | 1 d  | 2 d  | 3 d  | 5 d  | 7 d  | 9 d  |
| ----- | --------- | ---- | ---- | ---- | ---- | ---- | ---- |
| 2 in  | none      | 2.34 | 2.34 | 2.34 | 2.34 | 2.34 | 2.34 |
| 2 in  | hour t    | 1.53 | 1.85 | 2.00 | 2.16 | 2.31 | 2.43 |
| 2 in  | 24 h to t | 1.64 | 1.86 | 1.96 | 2.11 | 2.26 | 2.36 |
| 2 in  | r         | 0.72 | 0.59 | 0.53 | 0.45 | 0.37 | 0.30 |
| 4 in  | none      | 2.16 | 2.16 | 2.15 | 2.15 | 2.15 | 2.15 |
| 4 in  | hour t    | 1.17 | 1.51 | 1.66 | 1.82 | 1.98 | 2.10 |
| 4 in  | 24 h to t | 1.30 | 1.54 | 1.65 | 1.80 | 1.96 | 2.06 |
| 4 in  | r         | 0.79 | 0.65 | 0.57 | 0.49 | 0.40 | 0.32 |
| 8 in  | none      | 2.02 | 2.02 | 2.01 | 2.01 | 2.01 | 2.01 |
| 8 in  | hour t    | 0.89 | 1.20 | 1.34 | 1.50 | 1.65 | 1.76 |
| 8 in  | 24 h to t | 1.02 | 1.24 | 1.35 | 1.50 | 1.65 | 1.75 |
| 8 in  | r         | 0.84 | 0.70 | 0.63 | 0.54 | 0.44 | 0.36 |

## IFS's layers against the stations at their middles (bias / MAE, °C)

The stations' value at a layer's middle is linear between their sensors around it (64 cm between 50 and 100). If a layer agrees here but its interpolated depths don't, the interpolation is at fault.

| Layer                               | middle (cm) | all          | Dec–Feb      | Mar–May      | Jun–Aug      | Sep–Nov      |
| ----------------------------------- | ----------- | ------------ | ------------ | ------------ | ------------ | ------------ |
| 0_to_7cm                            | 3.5         | -1.11 / 2.25 | -2.96 / 3.37 | -0.63 / 1.95 | -0.60 / 2.05 | -0.57 / 1.82 |
| 7_to_28cm                           | 17.5        | -1.31 / 1.90 | -3.07 / 3.22 | -1.17 / 1.69 | -0.67 / 1.54 | -0.65 / 1.33 |
| 28_to_100cm                         | 64          | -1.88 / 2.13 | -1.98 / 2.08 | -3.10 / 3.14 | -1.90 / 2.18 | -0.45 / 1.01 |
| The archive's 30 cm, for comparison | 30          | -0.17 / 1.33 | -0.92 / 1.33 | -0.58 / 1.40 | +0.07 / 1.40 | +0.68 / 1.18 |

## Hours below 27 °F, November–March

Hours per station-winter-day, over the station-days on which the station and every source have every hour, and in brackets the share of those days with any. Station soil under snow is insulated; a field the wind has scoured is colder, so a source below the stations isn't necessarily wrong here.

| Depth | station    | archive    | IFS        | ERA5-Land  | station-days |
| ----- | ---------- | ---------- | ---------- | ---------- | ------------ |
| 2 in  | 2.27 (14%) | 3.15 (18%) | 7.12 (41%) | 3.14 (18%) | 16,438       |
| 4 in  | 1.75 (10%) | 2.81 (15%) | 6.47 (35%) | 2.76 (15%) | 16,121       |
| 8 in  | 1.02 (6%)  | 2.18 (11%) | 5.86 (30%) | 2.12 (11%) | 16,056       |

## Daily range at 2 in (°C, max − min of the local day)

| Source         | Dec–Feb | Mar–May | Jun–Aug | Sep–Nov |
| -------------- | ------- | ------- | ------- | ------- |
| station (5 cm) | 0.91    | 4.86    | 5.66    | 3.66    |
| archive        | 1.30    | 6.25    | 6.97    | 5.79    |
| IFS            | 3.36    | 6.50    | 7.64    | 6.39    |
| ERA5-Land      | 1.30    | 6.21    | 6.96    | 5.77    |

## IFS shifted at the seam (Q23)

The weight on the difference in ERA5-Land's last hour, fitted on 2025's hours and tested on the later ones: RMSE (°C) of the archive − IFS at each lead, unshifted, shifted by the whole difference, and by the fitted weight. The table written (`ifs_soil_seam.json`) is fitted on every year.

| Depth | lead (d) | weight | none | whole | weighted |
| ----- | -------- | ------ | ---- | ----- | -------- |
| 4cm   | 3        | 0.53   | 2.34 | 1.79  | 1.69     |
| 4cm   | 6        | 0.43   | 2.33 | 2.07  | 1.88     |
| 4cm   | 9        | 0.35   | 2.34 | 2.30  | 2.02     |
| 4cm   | 12       | 0.33   | 2.35 | 2.46  | 2.10     |
| 4cm   | 15       | 0.31   | 2.34 | 2.53  | 2.13     |
| 4cm   | 18       | 0.29   | 2.32 | 2.62  | 2.14     |
| 4cm   | 21       | 0.27   | 2.23 | 2.61  | 2.07     |
| 4cm   | 24       | 0.27   | 2.08 | 2.56  | 1.93     |
| 10cm  | 3        | 0.64   | 2.18 | 1.47  | 1.39     |
| 10cm  | 6        | 0.55   | 2.17 | 1.76  | 1.61     |
| 10cm  | 9        | 0.46   | 2.18 | 1.99  | 1.77     |
| 10cm  | 12       | 0.43   | 2.18 | 2.15  | 1.86     |
| 10cm  | 15       | 0.40   | 2.18 | 2.23  | 1.90     |
| 10cm  | 18       | 0.38   | 2.16 | 2.33  | 1.93     |
| 10cm  | 21       | 0.37   | 2.06 | 2.33  | 1.86     |
| 10cm  | 24       | 0.37   | 1.92 | 2.28  | 1.74     |
| 30cm  | 3        | 0.81   | 2.04 | 1.02  | 0.98     |
| 30cm  | 6        | 0.74   | 2.03 | 1.28  | 1.20     |
| 30cm  | 9        | 0.66   | 2.04 | 1.49  | 1.38     |
| 30cm  | 12       | 0.62   | 2.04 | 1.64  | 1.49     |
| 30cm  | 15       | 0.58   | 2.04 | 1.73  | 1.56     |
| 30cm  | 18       | 0.55   | 2.03 | 1.84  | 1.62     |
| 30cm  | 21       | 0.54   | 1.97 | 1.89  | 1.61     |
| 30cm  | 24       | 0.54   | 1.90 | 1.89  | 1.58     |
