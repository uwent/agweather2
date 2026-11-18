# NBM forecast calibration

Generated 2026-11-02 by `scripts/backtest_forecast.py --fit-calibration` (D39, D49), from the forecast's hours at 2695 cells in 73 runs against the archive, after the max is reshaped to NBM's TMAX. In order, each on the forecast with the ones before it applied:

1. **Max offset** by season: NBM's TMAX less the archive's daily max (the warmest top-of-hour value) on lead days 1–3, applied at every lead (later leads' errors are mostly weather) and interpolated through the year between mid-season days.
2. **Night min**: the hours' warm bias at each night's min by lead (interpolation between NBM's steps rounds off the coldest hours), each night's coldest hours (00–12Z) lowered by it.
3. **RH maps**: quantile maps from the forecast's hourly RH to the archive's, by season, lead group (hours 72, 144 and on) and solar hour, on every 2nd cell; the dew point is recomputed with the temperature kept. NBM's blended humidity rarely saturates, so the forecast counts too few humid hours (most in daytime rain and overcast).

| Season          | DJF   | MAM   | JJA   | SON   |
| --------------- | ----- | ----- | ----- | ----- |
| max offset (°C) | -0.41 | +0.26 | +0.60 | +0.43 |

| Lead day             | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10   |
| -------------------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| night warm bias (°C) | 0.45 | 0.66 | 0.71 | 0.96 | 0.91 | 0.77 | 0.87 | 1.59 | 1.94 | 1.79 |

Held out (2-fold: each run with its step's table fitted on the other half; the steps before it use the tables fitted on every run), bias / MAE by lead day (°C, hours a day):

|                          |              | day 1        | day 2        | day 3        | day 4        | day 5        | day 6        | day 7        | day 8        | day 9        | day 10       |
| ------------------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
| `air_temperature_max`    | none         | +0.15 / 1.26 | +0.23 / 1.45 | +0.28 / 1.52 | +0.10 / 1.72 | -0.14 / 1.92 | -0.32 / 2.47 | +0.19 / 2.90 | +0.57 / 3.02 | +0.55 / 3.43 | -0.08 / 3.47 |
| `air_temperature_max`    | + max offset | -0.05 / 1.27 | +0.03 / 1.46 | +0.08 / 1.51 | -0.11 / 1.69 | -0.34 / 1.89 | -0.51 / 2.42 | -0.01 / 2.89 | +0.38 / 3.00 | +0.35 / 3.41 | -0.28 / 3.44 |
| `air_temperature_max`    | + night min  | -0.06 / 1.23 | +0.01 / 1.43 | +0.07 / 1.48 | -0.12 / 1.68 | -0.35 / 1.91 | -0.53 / 2.45 | -0.02 / 2.90 | +0.37 / 3.02 | +0.34 / 3.43 | -0.29 / 3.43 |
| `air_temperature_max`    | + RH map     | -0.06 / 1.23 | +0.01 / 1.43 | +0.07 / 1.48 | -0.12 / 1.68 | -0.35 / 1.91 | -0.53 / 2.45 | -0.02 / 2.90 | +0.37 / 3.02 | +0.34 / 3.42 | -0.29 / 3.43 |
| `air_temperature_min`    | none         | +0.45 / 1.18 | +0.66 / 1.35 | +0.71 / 1.55 | +0.96 / 1.71 | +0.91 / 2.11 | +0.77 / 2.18 | +0.87 / 2.50 | +1.59 / 2.80 | +1.94 / 3.62 | +1.79 / 4.01 |
| `air_temperature_min`    | + max offset | +0.45 / 1.18 | +0.66 / 1.35 | +0.71 / 1.55 | +0.96 / 1.71 | +0.91 / 2.11 | +0.77 / 2.18 | +0.87 / 2.50 | +1.59 / 2.80 | +1.94 / 3.62 | +1.79 / 4.01 |
| `air_temperature_min`    | + night min  | +0.09 / 1.22 | +0.25 / 1.31 | +0.17 / 1.49 | +0.33 / 1.53 | +0.36 / 2.01 | +0.25 / 2.17 | +0.18 / 2.45 | +0.35 / 2.61 | +0.70 / 3.24 | +0.72 / 3.79 |
| `air_temperature_min`    | + RH map     | +0.09 / 1.16 | +0.25 / 1.28 | +0.17 / 1.47 | +0.32 / 1.52 | +0.37 / 2.01 | +0.25 / 2.15 | +0.20 / 2.44 | +0.37 / 2.56 | +0.74 / 3.21 | +0.72 / 3.79 |
| `hours_rh_over_80`       | none         | -1.26 / 3.27 | -1.57 / 3.80 | -1.41 / 4.39 | -1.35 / 4.12 | -1.21 / 4.33 | -1.84 / 5.10 | -1.91 / 5.66 | -3.16 / 6.17 | -2.87 / 5.57 | -2.88 / 5.47 |
| `hours_rh_over_80`       | + max offset | -1.19 / 3.22 | -1.50 / 3.79 | -1.32 / 4.37 | -1.27 / 4.09 | -1.15 / 4.30 | -1.78 / 5.05 | -1.84 / 5.62 | -3.13 / 6.15 | -2.85 / 5.56 | -2.85 / 5.45 |
| `hours_rh_over_80`       | + night min  | -0.67 / 3.17 | -0.79 / 3.72 | -0.49 / 4.29 | -0.25 / 4.02 | -0.20 / 4.24 | -0.78 / 4.98 | -0.38 / 5.52 | -1.39 / 5.73 | -0.80 / 5.24 | -0.74 / 5.11 |
| `hours_rh_over_80`       | + RH map     | -0.24 / 3.11 | -0.24 / 3.76 | +0.13 / 4.31 | +0.09 / 4.22 | +0.24 / 4.46 | -0.24 / 4.98 | +0.35 / 5.66 | -0.52 / 6.26 | -0.04 / 5.67 | -0.17 / 5.49 |
| `hours_rh_over_90`       | none         | -1.59 / 2.80 | -1.94 / 3.12 | -1.89 / 3.83 | -1.81 / 3.55 | -1.91 / 3.71 | -2.65 / 4.23 | -2.89 / 4.30 | -3.64 / 4.85 | -3.64 / 4.71 | -3.68 / 4.80 |
| `hours_rh_over_90`       | + max offset | -1.58 / 2.82 | -1.92 / 3.12 | -1.86 / 3.82 | -1.78 / 3.53 | -1.89 / 3.70 | -2.64 / 4.21 | -2.88 / 4.29 | -3.63 / 4.85 | -3.64 / 4.70 | -3.67 / 4.80 |
| `hours_rh_over_90`       | + night min  | -1.01 / 2.76 | -1.10 / 2.97 | -0.82 / 3.70 | -0.58 / 3.40 | -0.71 / 3.56 | -1.52 / 4.13 | -1.21 / 4.25 | -1.36 / 4.75 | -1.05 / 4.50 | -1.14 / 4.47 |
| `hours_rh_over_90`       | + RH map     | -0.16 / 2.63 | -0.25 / 2.97 | +0.23 / 3.80 | +0.21 / 3.56 | +0.06 / 3.66 | -0.65 / 4.12 | +0.01 / 4.58 | -0.31 / 5.22 | -0.04 / 4.90 | -0.42 / 4.79 |
| `hours_rh_over_90_night` | none         | -0.45 / 1.73 | -0.77 / 1.72 | -0.84 / 2.22 | -0.85 / 2.53 | -0.83 / 2.26 | -0.93 / 2.67 | -1.18 / 2.53 | -1.62 / 2.93 | -2.01 / 3.16 | -1.98 / 3.14 |
| `hours_rh_over_90_night` | + max offset | -0.45 / 1.73 | -0.77 / 1.72 | -0.84 / 2.22 | -0.85 / 2.53 | -0.83 / 2.26 | -0.93 / 2.67 | -1.18 / 2.53 | -1.62 / 2.93 | -2.01 / 3.16 | -1.98 / 3.14 |
| `hours_rh_over_90_night` | + night min  | +0.05 / 1.75 | -0.05 / 1.77 | +0.01 / 2.14 | +0.44 / 2.62 | +0.37 / 2.30 | +0.12 / 2.82 | +0.04 / 2.65 | +0.69 / 3.22 | +0.64 / 3.47 | +0.50 / 3.26 |
| `hours_rh_over_90_night` | + RH map     | +0.08 / 1.64 | -0.02 / 1.70 | +0.05 / 2.15 | +0.33 / 2.55 | +0.09 / 2.20 | -0.30 / 2.67 | -0.33 / 2.47 | +0.42 / 3.22 | +0.25 / 3.35 | -0.05 / 3.11 |
