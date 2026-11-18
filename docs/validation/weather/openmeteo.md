# Open-Meteo against Wisconet

Generated 2026-10-31 by `scripts/compare_openmeteo_wisconet.py`, 2025-01-01 to 2026-10-30, at 80 Wisconet stations. Open-Meteo from its historical-forecast API at each station's location: `ncep_nbm_conus`, `best_match`, and the two merged hour by hour (ncep_nbm_conus first, as v2's points and WISP use them). The archive is v2's grid at the station's cell. Ratios are totals over the days both have.

## Coverage

| Source       | hours with temperature | with shortwave | with RH |
| ------------ | ---------------------- | -------------- | ------- |
| NBM          | 0.991                  | 0.991          | 0.991   |
| best_match   | 1.000                  | 1.000          | 1.000   |
| merged       | 1.000                  | 1.000          | 1.000   |
| archive (v2) | 1.000                  | 1.000          | 1.000   |

## Daily shortwave (MJ/m²)

| Source            | ratio, all | ratio, Apr–Oct | MAE  | by month (ratio)                                                                                            |
| ----------------- | ---------- | -------------- | ---- | ----------------------------------------------------------------------------------------------------------- |
| NBM               | 1.146      | 1.145          | 2.29 | Jan 1.14 Feb 1.13 Mar 1.13 Apr 1.11 May 1.12 Jun 1.17 Jul 1.17 Aug 1.17 Sep 1.16 Oct 1.10 Nov 1.21 Dec 1.26 |
| best_match        | 1.205      | 1.200          | 2.97 | Jan 1.24 Feb 1.20 Mar 1.18 Apr 1.20 May 1.20 Jun 1.24 Jul 1.20 Aug 1.22 Sep 1.19 Oct 1.13 Nov 1.31 Dec 1.37 |
| merged            | 1.146      | 1.145          | 2.30 | Jan 1.14 Feb 1.13 Mar 1.13 Apr 1.11 May 1.12 Jun 1.17 Jul 1.17 Aug 1.17 Sep 1.16 Oct 1.10 Nov 1.21 Dec 1.26 |
| archive (v2)      | 0.993      | 0.993          | 1.65 | Jan 1.00 Feb 0.96 Mar 0.98 Apr 0.99 May 1.01 Jun 1.02 Jul 0.99 Aug 1.00 Sep 0.98 Oct 0.95 Nov 1.07 Dec 1.07 |
| merged, corrected | 0.996      | 0.999          | 1.55 | Jan 0.98 Feb 0.97 Mar 0.97 Apr 0.96 May 0.97 Jun 1.02 Jul 1.02 Aug 1.02 Sep 1.00 Oct 0.95 Nov 1.04 Dec 1.06 |

The merged series' correction fitted on 2025, for the held-out check (`--fit` writes `agdata/data/openmeteo_shortwave_correction.json` refitted on every year):

| Clearness | 0.05 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.95 | 1.05 | 1.15 |
| --------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| Factor    | 0.57 | 1.07 | 0.91 | 0.85 | 0.82 | 0.83 | 0.84 | 0.86 | 0.89 | 0.90 | 0.87 | 0.64 |

Held out (2026): ratio 1.136 → 0.987, daily MAE 2.33 → 1.58 MJ/m².

## Hourly temperature and humidity

RH is Open-Meteo's `relative_humidity_2m`, and RH from its temperature and dew point as v2 derives it. Humid hours per day are over complete local days, May–September; the threshold is the RH at or above which the source counts as many hours as the stations' RH ≥ 90% (the archive's: 88%, D50).

| Source              | temperature bias (°C) | RH bias | RH MAE | RH ≥ 90 h/day (station) | threshold |
| ------------------- | --------------------- | ------- | ------ | ----------------------- | --------- |
| NBM                 | +0.16                 | -0.5    | 6.0    | 5.57 (7.80)             | 85.0      |
| NBM, derived        | +0.16                 | -0.5    | 6.0    | 5.30 (7.80)             | 84.9      |
| best_match          | +0.19                 | -2.9    | 6.0    | 4.85 (7.80)             | 84.0      |
| best_match, derived | +0.19                 | -2.9    | 6.0    | 4.52 (7.80)             | 84.2      |
| merged              | +0.16                 | -0.5    | 6.0    | 5.53 (7.80)             | 85.0      |
| merged, derived     | +0.16                 | -0.6    | 6.0    | 5.27 (7.80)             | 84.9      |
| archive (v2)        | +0.16                 | -0.1    | 3.8    | 7.17 (7.80)             | 88.0      |

The merged series' RH mapped onto the archive's, fitted on 2025 and held out, May–September (`--fit` writes `agdata/data/openmeteo_rh_map.json` refitted on every year; fitted on 2026 and tested on 2025 instead, the map lands 0.2 h a day over the archive at RH ≥ 88%, where this way it's 1.2 under: Open-Meteo's humidity changes from year to year):

| RH                  | RH ≥ 90 h/day | RH ≥ 88 h/day | bias against the archive | MAE against the stations |
| ------------------- | ------------- | ------------- | ------------------------ | ------------------------ |
| stations            | 7.54          | 8.35          | +0.9                     | 0.0                      |
| archive             | 6.75          | 7.74          | +0.0                     | 4.1                      |
| Open-Meteo, derived | 4.73          | 5.62          | -2.0                     | 6.9                      |
| Open-Meteo, mapped  | 5.71          | 6.57          | -1.7                     | 6.7                      |

## Daily ET0 (mm), against FAO-56 from the stations' measurements

| Source                                     | ratio, Apr–Oct | MAE, Apr–Oct | ratio, all | by month, Apr–Oct (ratio)                                      |
| ------------------------------------------ | -------------- | ------------ | ---------- | -------------------------------------------------------------- |
| Open-Meteo's own (merged; WISP's)          | 1.156          | 0.52         | 1.148      | Apr 1.10 May 1.10 Jun 1.18 Jul 1.19 Aug 1.18 Sep 1.17 Oct 1.12 |
| Open-Meteo's own, NBM                      | 1.155          | 0.52         | 1.148      | Apr 1.10 May 1.10 Jun 1.18 Jul 1.19 Aug 1.18 Sep 1.16 Oct 1.12 |
| Open-Meteo's own, best_match               | 1.220          | 0.68         | 1.224      | Apr 1.20 May 1.19 Jun 1.22 Jul 1.21 Aug 1.24 Sep 1.24 Oct 1.23 |
| ours from Open-Meteo (merged; v2's points) | 1.126          | 0.46         | 1.116      | Apr 1.07 May 1.08 Jun 1.15 Jul 1.16 Aug 1.16 Sep 1.14 Oct 1.08 |
| ours from Open-Meteo, shortwave corrected  | 1.032          | 0.34         | 1.027      | Apr 0.99 May 0.99 Jun 1.06 Jul 1.06 Aug 1.05 Sep 1.03 Oct 1.01 |
| archive (v2, corrected shortwave)          | 1.025          | 0.26         | 1.023      | Apr 1.01 May 1.03 Jun 1.04 Jul 1.03 Aug 1.03 Sep 1.01 Oct 1.01 |
| old API                                    | 1.113          | 0.61         | 1.036      | Apr 0.97 May 0.98 Jun 1.14 Jul 1.26 Aug 1.23 Sep 1.17 Oct 0.84 |

The stations' FAO-56 ET0 averages 3.01 mm a day over Apr–Oct (30,503 station-days).
