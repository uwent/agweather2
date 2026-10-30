# NBM shortwave correction

Generated 2026-10-30 by `scripts/backtest_forecast.py --fit-shortwave` (D48). The raw forecast's daily shortwave (NBM's DSWRF by solar-day clearness) at 2695 cells in 73 runs, against the archive (HRRR corrected against Wisconet). Factors by lead group and the forecast day's clearness (its total over the FAO-56 clear-sky total); bins with fewer than 2000 cell-days take their neighbours'. Most of it is calibration: as skill falls with lead, a forecast very dark or very clear day turns out less so.

| Lead days | 0.05 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.95 | 1.05 | 1.15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1–1 | 2.21 | 1.60 | 1.30 | 1.20 | 1.10 | 1.02 | 0.94 | 0.91 | 0.89 | 0.88 | 0.88 | 0.88 |
| 2–3 | 4.90 | 2.57 | 1.66 | 1.36 | 1.17 | 1.04 | 0.95 | 0.89 | 0.84 | 0.81 | 0.75 | 0.74 |
| 4–6 | 6.86 | 3.14 | 2.11 | 1.64 | 1.31 | 1.12 | 1.00 | 0.89 | 0.81 | 0.78 | 0.78 | 0.78 |
| 7–10 | 9.95 | 4.17 | 2.48 | 1.75 | 1.38 | 1.13 | 0.99 | 0.86 | 0.77 | 0.71 | 0.66 | 0.68 |

Fitted on alternate runs, tested on the others (bias / MAE, MJ/m² a day, by lead day):

| | day 1 | day 2 | day 3 | day 4 | day 5 | day 6 | day 7 | day 8 | day 9 | day 10 | ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| raw | +0.48 / 2.12 | +2.02 / 3.43 | +0.07 / 2.89 | +0.60 / 3.51 | +1.94 / 4.39 | +1.31 / 4.21 | +0.43 / 4.53 | +2.20 / 5.26 | +1.05 / 5.30 | +1.02 / 5.31 | 1.086 |
| corrected | -0.31 / 1.63 | +0.40 / 2.20 | -0.72 / 2.43 | +0.24 / 2.57 | +0.70 / 3.03 | +0.79 / 3.24 | -0.06 / 2.72 | +0.52 / 3.29 | -0.33 / 3.16 | -0.49 / 3.19 | 1.006 |
