# NBM shortwave correction

Generated 2026-11-02 by `scripts/backtest_forecast.py --fit-shortwave` (D48). The raw forecast's daily shortwave (NBM's DSWRF by solar-day clearness) at 2695 cells in 73 runs, against the archive (HRRR corrected against Wisconet). Factors by lead group and the forecast day's clearness (its total over the FAO-56 clear-sky total); bins with fewer than 2000 cell-days take their neighbours'. Most of it is calibration: as skill falls with lead, a forecast very dark or very clear day turns out less so.

| Lead days | 0.05 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.95 | 1.05 | 1.15 |
| --------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 1–1       | 2.21 | 1.58 | 1.30 | 1.18 | 1.08 | 1.00 | 0.93 | 0.90 | 0.88 | 0.87 | 0.87 | 0.87 |
| 2–3       | 4.81 | 2.54 | 1.63 | 1.33 | 1.14 | 1.01 | 0.93 | 0.87 | 0.82 | 0.79 | 0.73 | 0.73 |
| 4–6       | 6.76 | 3.08 | 2.06 | 1.61 | 1.28 | 1.10 | 0.98 | 0.87 | 0.79 | 0.76 | 0.78 | 0.78 |
| 7–10      | 9.83 | 4.11 | 2.44 | 1.71 | 1.34 | 1.11 | 0.97 | 0.84 | 0.75 | 0.69 | 0.66 | 0.68 |

Fitted on alternate runs, tested on the others (bias / MAE, MJ/m² a day, by lead day):

|           | day 1        | day 2        | day 3        | day 4        | day 5        | day 6        | day 7        | day 8        | day 9        | day 10       | ratio |
| --------- | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ----- |
| raw       | +0.61 / 2.17 | +2.33 / 3.60 | +0.37 / 2.94 | +0.87 / 3.56 | +2.27 / 4.60 | +1.62 / 4.44 | +0.75 / 4.69 | +2.49 / 5.38 | +1.36 / 5.35 | +1.31 / 5.41 | 1.109 |
| corrected | -0.32 / 1.62 | +0.41 / 2.15 | -0.69 / 2.39 | +0.24 / 2.56 | +0.72 / 3.06 | +0.82 / 3.16 | -0.07 / 2.65 | +0.52 / 3.23 | -0.30 / 3.08 | -0.50 / 3.17 | 1.007 |
