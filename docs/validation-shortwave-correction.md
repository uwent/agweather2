# HRRR shortwave correction

Generated 2026-10-31 by `scripts/fit_shortwave_correction.py` (D48). Fitted on 2025, tested on 2026 (to 2026-10-27), at 80 Wisconet stations: hourly HRRR at each station's cell against the station's `60min_solar_radiation_w_avg`. The factor is by the hour's clearness (HRRR over FAO-56 clear-sky Rso), applied as a linear interpolation between bin middles.

| Clearness | 0.05 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.95 | 1.05 | 1.15 |
| --------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| Factor    | 2.02 | 1.22 | 0.98 | 0.89 | 0.86 | 0.82 | 0.80 | 0.78 | 0.79 | 0.83 | 0.88 | 0.93 |

| Year            | correction | hourly bias (W/m²) | hourly MAE | daily MAE (MJ/m²) | ratio | daily r |
| --------------- | ---------- | ------------------ | ---------- | ----------------- | ----- | ------- |
| 2025 (fit)      | none       | +28.3              | 38.2       | 2.64              | 1.193 | 0.952   |
| 2025 (fit)      | applied    | +0.0               | 30.2       | 1.64              | 1.000 | 0.954   |
| 2026 (held out) | none       | +29.8              | 41.1       | 2.80              | 1.175 | 0.956   |
| 2026 (held out) | applied    | -2.2               | 32.9       | 1.66              | 0.987 | 0.957   |

2026 corrected over observed, by month: 1: 0.97, 2: 0.96, 3: 0.98, 4: 0.97, 5: 1.01, 6: 1.00, 7: 0.99, 8: 1.00, 9: 0.99, 10: 0.93

By station: median 0.99, 10–90% 0.96–1.02 (raw HRRR differs by station too: 1.15 at Arlington, 1.26 at Hancock in 2025).
