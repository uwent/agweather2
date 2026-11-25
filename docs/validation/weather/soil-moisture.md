# Soil moisture against Wisconet

Generated 2026-11-25 by `scripts/compare_soil_moisture_wisconet.py`, 2025-01-01 to 2026-11-17, at 80 Wisconet stations (with a moisture sensor at 5 cm: 79, 10: 78, 20: 77, 50: 73, 100: 67). ERA5-Land is Open-Meteo's `era5_land` (archive API), the archive's source; IFS is Open-Meteo's `ecmwf_ifs` from its historical-forecast API (each run's first hours: the model's own soil climate, not its forecast skill at long leads), both at the station's location. Water content is volumetric, m³/m³ (0.30 is 30% of the soil's volume). Bias is the source minus the station.

The stations' CS655 sensors see only liquid water, so in frozen soil they read low while the models carry the frozen water too. Hours with the station's soil at the sensor at or below 0.5 °C (ERA5-Land's layer where the station has no temperature) are counted as frozen and left out of every table but the frozen column. Readings outside 0.02–0.65 m³/m³ and one-hour spikes of more than 0.08 are dropped; Wisconet doesn't QC its soil data.

Modeled soil water is for the model's soil over a ~9 km cell, with its texture from a global map, not the station's soil. Two columns judge the sources apart from that: the MAE with each station's own mean difference taken out ("MAE, own bias out"), and the median over stations of the correlation of daily means with the station's (Pearson r, and rank r: what a percentile against other years depends on).

## Conclusions

- **ERA5-Land is the better source of the two, by timing.** Its daily soil water follows the stations' better at every depth (median r 0.65–0.73 against IFS's 0.40–0.65); IFS is weakest in summer and at 50 cm. ERA5-Land reads wetter than the stations (0.040–0.089 m³/m³ on average, MAE 0.104–0.124), but most of that is a lasting difference of level at each station: with each station's own mean difference taken out, its MAE is 0.032–0.048 m³/m³.
- **The level at a place is not a field's.** The stations' own mean differences run from about −0.2 to +0.3 m³/m³ in either model (the model's soil for its ~9 km cell against the station's): a map of water content shows where soils are wetter or drier than usual only roughly, and a value at a site can be off by a soil's whole range. A percentile against the archive's own years (the next step) depends only on timing, where ERA5-Land does well.
- **Layers, not depths.** Interpolating between the layers' middles, as soil temperature is, changes ERA5-Land's r by no more than 0.02 at any depth (IFS's by up to 0.07, at 50 cm), so the archive keeps each layer's water as the model computes it (0–7, 7–28 and 28–100 cm), which is also what plant-available water needs.
- **Frozen soil.** About a fifth of the shallow sensors' hours are frozen, when the sensors see only the unfrozen water: ERA5-Land reads +0.19 m³/m³ above them then, against +0.09 in thawed hours. Winter values compare with nothing on the ground; the archive carries the models' total water.
- **IFS needs the seam shift.** IFS is drier than ERA5-Land by 0.04–0.07 m³/m³ on average (from May to December most), and the difference lasts for weeks. Shifting IFS by the difference in ERA5-Land's last hour, faded by D55's fitted weights, cuts the difference 3 days on by about half in the top layer and by about 70% and 90% in the two below it (the seam table below).
- **HRRR isn't better.** On a sample of days its analysed soil water is drier than the stations and correlates with them no better than ERA5-Land at any depth (its own table, at the end), so it isn't added as a source.

## By depth: layer or interpolated (unfrozen hours)

Each sensor against the layer that holds it (5 cm in 0–7, 10 and 20 cm in 7–28, 50 cm in 28–100), and against the layers taken to the sensor's depth linearly between their middles (3.5, 17.5 and 64 cm), as soil temperature is.

| Sensor | Source | taken as | bias | MAE | MAE, own bias out | Pearson r (daily) | rank r (daily) | stations |
|---|---|---|---|---|---|---|---|---|
| 5 cm | ERA5-Land | layer | +0.089 | 0.113 | 0.048 | 0.72 | 0.72 | 78 |
| 5 cm | ERA5-Land | interpolated | +0.089 | 0.113 | 0.047 | 0.73 | 0.73 | 78 |
| 5 cm | IFS | layer | +0.030 | 0.089 | 0.055 | 0.65 | 0.64 | 78 |
| 5 cm | IFS | interpolated | +0.030 | 0.088 | 0.054 | 0.66 | 0.65 | 78 |
| 10 cm | ERA5-Land | layer | +0.075 | 0.104 | 0.040 | 0.73 | 0.73 | 77 |
| 10 cm | ERA5-Land | interpolated | +0.075 | 0.104 | 0.041 | 0.74 | 0.74 | 77 |
| 10 cm | IFS | layer | +0.016 | 0.086 | 0.049 | 0.63 | 0.60 | 77 |
| 10 cm | IFS | interpolated | +0.017 | 0.086 | 0.049 | 0.65 | 0.63 | 77 |
| 20 cm | ERA5-Land | layer | +0.065 | 0.107 | 0.035 | 0.70 | 0.71 | 76 |
| 20 cm | ERA5-Land | interpolated | +0.064 | 0.106 | 0.035 | 0.70 | 0.72 | 76 |
| 20 cm | IFS | layer | +0.007 | 0.092 | 0.049 | 0.60 | 0.60 | 76 |
| 20 cm | IFS | interpolated | +0.006 | 0.092 | 0.048 | 0.61 | 0.60 | 76 |
| 50 cm | ERA5-Land | layer | +0.040 | 0.124 | 0.032 | 0.65 | 0.60 | 72 |
| 50 cm | ERA5-Land | interpolated | +0.043 | 0.124 | 0.031 | 0.68 | 0.63 | 72 |
| 50 cm | IFS | layer | -0.033 | 0.124 | 0.051 | 0.40 | 0.34 | 72 |
| 50 cm | IFS | interpolated | -0.024 | 0.121 | 0.048 | 0.46 | 0.41 | 72 |

The 100 cm sensor sits on the boundary between the third and fourth layers:

| Sensor | Source | layer | bias | MAE | MAE, own bias out | Pearson r (daily) | rank r (daily) | stations |
|---|---|---|---|---|---|---|---|---|
| 100 cm | ERA5-Land | 28–100cm | +0.037 | 0.126 | 0.036 | 0.60 | 0.57 | 67 |
| 100 cm | ERA5-Land | 100–255cm | +0.068 | 0.136 | 0.024 | 0.49 | 0.53 | 67 |
| 100 cm | IFS | 28–100cm | -0.034 | 0.128 | 0.055 | 0.42 | 0.32 | 67 |
| 100 cm | IFS | 100–255cm | +0.010 | 0.127 | 0.029 | 0.32 | 0.35 | 67 |

## By season (bias / MAE, m³/m³; each sensor against the layer that holds it)

Seasons count unfrozen hours only; the frozen column is every frozen hour, to show what the sensors do then.

| Sensor | Source | Mar–May | Jun–Aug | Sep–Nov | Dec–Feb | frozen | station mean, unfrozen |
|---|---|---|---|---|---|---|---|
| 5 cm | ERA5-Land | +0.063 / 0.105 | +0.094 / 0.116 | +0.109 / 0.122 | +0.053 / 0.092 | +0.187 / 0.202 | 0.225 |
| 5 cm | IFS | +0.015 / 0.086 | +0.015 / 0.089 | +0.056 / 0.090 | +0.043 / 0.085 | +0.199 / 0.211 | 0.225 |
| 10 cm | ERA5-Land | +0.062 / 0.100 | +0.075 / 0.104 | +0.091 / 0.109 | +0.051 / 0.092 | +0.187 / 0.197 | 0.237 |
| 10 cm | IFS | +0.023 / 0.087 | -0.007 / 0.088 | +0.035 / 0.083 | +0.015 / 0.084 | +0.185 / 0.195 | 0.237 |
| 20 cm | ERA5-Land | +0.055 / 0.102 | +0.062 / 0.109 | +0.080 / 0.111 | +0.052 / 0.099 | +0.185 / 0.194 | 0.248 |
| 20 cm | IFS | +0.016 / 0.089 | -0.020 / 0.097 | +0.025 / 0.091 | +0.021 / 0.089 | +0.185 / 0.194 | 0.248 |
| 50 cm | ERA5-Land | +0.059 / 0.123 | +0.026 / 0.128 | +0.037 / 0.123 | +0.041 / 0.117 | +0.150 / 0.173 | 0.267 |
| 50 cm | IFS | +0.007 / 0.121 | -0.065 / 0.133 | -0.039 / 0.123 | -0.018 / 0.113 | +0.111 / 0.149 | 0.267 |

Share of the stations' hours counted as frozen: 5 cm 21%, 10 cm 19%, 20 cm 17%, 50 cm 10%.

## Correlation by season (median over stations of Pearson r of daily means, unfrozen days)

| Sensor | Source | all | Mar–May | Jun–Aug | Sep–Nov | Dec–Feb |
|---|---|---|---|---|---|---|
| 5 cm | ERA5-Land | 0.72 | 0.84 | 0.69 | 0.67 | 0.78 |
| 5 cm | IFS | 0.65 | 0.82 | 0.56 | 0.63 | 0.78 |
| 10 cm | ERA5-Land | 0.73 | 0.85 | 0.72 | 0.68 | 0.85 |
| 10 cm | IFS | 0.63 | 0.79 | 0.49 | 0.60 | 0.86 |
| 20 cm | ERA5-Land | 0.70 | 0.82 | 0.70 | 0.66 | 0.86 |
| 20 cm | IFS | 0.60 | 0.77 | 0.47 | 0.60 | 0.87 |
| 50 cm | ERA5-Land | 0.65 | 0.71 | 0.53 | 0.65 | 0.70 |
| 50 cm | IFS | 0.40 | 0.43 | -0.01 | 0.38 | 0.53 |

## Each station's mean difference (unfrozen hours, m³/m³)

The spread of the stations' own mean differences: how much of the MAE is a lasting difference of level between the model's cell and the station's soil.

| Sensor | Source | lowest | 10th pct | median | 90th pct | highest |
|---|---|---|---|---|---|---|
| 5 cm | ERA5-Land | -0.085 | -0.027 | +0.099 | +0.204 | +0.294 |
| 5 cm | IFS | -0.152 | -0.068 | +0.031 | +0.134 | +0.223 |
| 10 cm | ERA5-Land | -0.121 | -0.051 | +0.070 | +0.183 | +0.290 |
| 10 cm | IFS | -0.185 | -0.095 | +0.010 | +0.122 | +0.229 |
| 20 cm | ERA5-Land | -0.231 | -0.067 | +0.075 | +0.197 | +0.286 |
| 20 cm | IFS | -0.186 | -0.110 | +0.010 | +0.132 | +0.215 |
| 50 cm | ERA5-Land | -0.221 | -0.122 | +0.047 | +0.216 | +0.316 |
| 50 cm | IFS | -0.261 | -0.216 | -0.042 | +0.143 | +0.212 |

## ERA5-Land minus IFS: the step at the seam

Where the archive hands over from ERA5-Land to IFS (its last hour, ~5 days behind), the soil water steps by ERA5-Land − IFS. By month, the mean over the stations' cells, and the spread of the stations' own means over the whole period:

| Layer | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | stations' means: 10th / median / 90th pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0–7cm | -0.02 | -0.01 | +0.01 | +0.02 | +0.09 | +0.09 | +0.08 | +0.07 | +0.06 | +0.05 | +0.04 | +0.01 | +0.01 / +0.05 / +0.07 |
| 7–28cm | +0.01 | +0.00 | +0.00 | +0.01 | +0.08 | +0.10 | +0.08 | +0.07 | +0.07 | +0.05 | +0.04 | +0.04 | +0.01 / +0.05 / +0.08 |
| 28–100cm | +0.05 | +0.04 | +0.03 | +0.03 | +0.07 | +0.10 | +0.10 | +0.08 | +0.08 | +0.08 | +0.07 | +0.07 | +0.02 / +0.07 / +0.11 |

How much of the step is still there later: the weight on the difference in ERA5-Land's last hour that best predicts the difference at each lead (`agdata.soil_seam.fit`, as D55 fitted it for temperature), fitted on 2025's hours and tested on the later ones, with the RMSE (m³/m³) of ERA5-Land − IFS at that lead: unshifted, shifted by the whole difference, and by the fitted weight.

| Layer | lead (d) | weight | none | whole | weighted |
|---|---|---|---|---|---|
| 0–7cm | 3 | 0.87 | 0.079 | 0.045 | 0.043 |
| 0–7cm | 6 | 0.82 | 0.080 | 0.052 | 0.049 |
| 0–7cm | 9 | 0.79 | 0.080 | 0.056 | 0.053 |
| 0–7cm | 12 | 0.78 | 0.080 | 0.057 | 0.054 |
| 0–7cm | 15 | 0.77 | 0.080 | 0.058 | 0.054 |
| 0–7cm | 18 | 0.75 | 0.081 | 0.060 | 0.056 |
| 0–7cm | 21 | 0.72 | 0.081 | 0.062 | 0.057 |
| 0–7cm | 24 | 0.72 | 0.081 | 0.064 | 0.059 |
| 7–28cm | 3 | 0.96 | 0.075 | 0.024 | 0.023 |
| 7–28cm | 6 | 0.93 | 0.075 | 0.032 | 0.031 |
| 7–28cm | 9 | 0.90 | 0.075 | 0.037 | 0.036 |
| 7–28cm | 12 | 0.88 | 0.075 | 0.041 | 0.039 |
| 7–28cm | 15 | 0.86 | 0.076 | 0.044 | 0.042 |
| 7–28cm | 18 | 0.84 | 0.076 | 0.046 | 0.044 |
| 7–28cm | 21 | 0.83 | 0.076 | 0.048 | 0.046 |
| 7–28cm | 24 | 0.82 | 0.076 | 0.050 | 0.048 |
| 28–100cm | 3 | 0.99 | 0.086 | 0.010 | 0.010 |
| 28–100cm | 6 | 0.99 | 0.085 | 0.015 | 0.015 |
| 28–100cm | 9 | 0.98 | 0.085 | 0.019 | 0.019 |
| 28–100cm | 12 | 0.97 | 0.085 | 0.023 | 0.023 |
| 28–100cm | 15 | 0.96 | 0.085 | 0.026 | 0.026 |
| 28–100cm | 18 | 0.95 | 0.085 | 0.029 | 0.029 |
| 28–100cm | 21 | 0.94 | 0.085 | 0.032 | 0.032 |
| 28–100cm | 24 | 0.93 | 0.085 | 0.035 | 0.034 |

The table written (`ifs_soil_seam.json`, version 2) holds the moisture layers' weights fitted on every year; soil temperature's are unchanged.

## HRRR on a sample of days

HRRR's analysed soil moisture (`SOILW`, `wrfprs` f00 at 12Z, every third day) at the HRRR point nearest each station, at its levels of 4, 10, 30 and 60 cm (20 cm linear between 10 and 30, 50 cm between 30 and 60), against the station's hour ending 12Z; ERA5-Land and IFS (the layer holding the sensor) on the same hours, for a like comparison. Unfrozen hours. Correlations are the median over stations of r over the sampled hours.

| Sensor | Source | bias | MAE | MAE, own bias out | Pearson r | rank r | stations |
|---|---|---|---|---|---|---|---|
| 5 cm | HRRR | -0.020 | 0.083 | 0.052 | 0.60 | 0.64 | 78 |
| 5 cm | ERA5-Land | +0.090 | 0.115 | 0.048 | 0.69 | 0.71 | 78 |
| 5 cm | IFS | +0.032 | 0.089 | 0.055 | 0.64 | 0.64 | 78 |
| 10 cm | HRRR | -0.032 | 0.080 | 0.043 | 0.66 | 0.69 | 77 |
| 10 cm | ERA5-Land | +0.076 | 0.104 | 0.040 | 0.73 | 0.74 | 77 |
| 10 cm | IFS | +0.017 | 0.086 | 0.049 | 0.63 | 0.61 | 77 |
| 20 cm | HRRR | -0.049 | 0.090 | 0.036 | 0.69 | 0.73 | 76 |
| 20 cm | ERA5-Land | +0.065 | 0.107 | 0.035 | 0.70 | 0.71 | 76 |
| 20 cm | IFS | +0.008 | 0.092 | 0.048 | 0.61 | 0.61 | 76 |
| 50 cm | HRRR | -0.080 | 0.126 | 0.027 | 0.58 | 0.58 | 72 |
| 50 cm | ERA5-Land | +0.040 | 0.124 | 0.032 | 0.65 | 0.60 | 72 |
| 50 cm | IFS | -0.032 | 0.124 | 0.051 | 0.39 | 0.33 | 72 |
