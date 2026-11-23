# Soil moisture against Wisconet

**Status: stub (2026-11-23).** A placeholder for Phase 6 step 6's soil moisture check (F9; `docs/plans/phase-6-frontend-plan-and-data.md`, "Soil moisture"). The archive holds no soil moisture yet. This page records what to compare, which fields to read, and a first look at Open-Meteo's two models from the data pulled for the Wisconet team. It will be replaced by a generated report, as `soil.md` was for temperature.

## What to compare

- **Sources**, the same ones soil temperature uses (D52–D55):
  - ERA5-Land's volumetric soil water (`swvl1`–`swvl4`; layers 0–7, 7–28, 28–100 and 100–255 cm), added to the CDS request `agdata.sources.era5land` already makes.
  - IFS's soil moisture from Open-Meteo's open data (check that the bucket holds it), and from the point API for points.
  - HRRR's inside the box, if it compares better.
- **Stations:** Wisconet's CS655 sensors at 5, 10, 20, 50 and 100 cm (named 2, 4, 8, 20 and 40 in), the same sensors as the temperature check.
  - Hourly: `60min_soil_moisture_pct_avg@{2,4,8,20,40}in` (field ids 34, 22, 25, 28, 33). These are percent; check against the daily fields that the percent is volumetric water content × 100.
  - Daily: `daily_soil_moisture_{5,10,20,50,100}cm_m3m-3_avg` (ids 123–127), already in m³/m³.
  - QC as for temperature: Wisconet doesn't QC its soil data. Watch for frozen soil, when the CS655 reads only liquid water, so its winter values drop. Compare with the model's liquid water, or leave out frozen hours (the station's soil temperature ≤ 0 °C).
- **Questions to answer:**
  - Each source's bias and error by depth and season, as `soil.md`'s first table does.
  - Whether a station-specific offset dominates. Modeled soil water is for the model's soil over about 9 km, not the station's, so judge it by anomaly and percentile agreement (correlation of departures from each one's own mean, rank of a day within its years) as well as by absolute value. The page will show water content and a percentile against other years (F9).
  - The step between ERA5-Land and IFS at the seam, and whether D55's shift by lead carries over to moisture.
  - Which IFS layer and depth mapping matches the stations, as for temperature (`soil_at_depths`).

## First look: Open-Meteo's ERA5-Land and IFS (2026-11-23)

Data pulled for the Wisconet team (`tmp/om-soil-for-wisconet/`, `fetch_om_soil.py`): hourly soil temperature and moisture for all four layers from Open-Meteo, `era5_land` (archive API) and `ecmwf_ifs` (historical-forecast API, the first hours of each run). Open-Meteo's elevation adjustment is turned off (`elevation=nan`). The data run from 2023-10-01 to 2026-11-22 (ERA5-Land through 2026-11-17 23Z), at 131 locations: the 81 Wisconet stations and the 50 sites in `validation_sites_50.csv`. No station data is compared yet. These are the two models against each other, over the hours both have:

| Layer | ERA5-Land mean (m³/m³) | IFS mean (m³/m³) | Mean absolute difference, hour by hour (m³/m³) | IFS − ERA5-Land, each location's mean: lowest / median / highest (m³/m³) |
| --- | --- | --- | --- | --- |
| 0–7 cm | 0.310 | 0.282 | 0.054 | −0.31 / −0.03 / +0.22 |
| 7–28 cm | 0.310 | 0.279 | 0.054 | −0.31 / −0.04 / +0.23 |
| 28–100 cm | 0.301 | 0.254 | 0.067 | −0.31 / −0.05 / +0.22 |
| 100–255 cm | 0.325 | 0.283 | 0.057 | −0.33 / −0.04 / +0.21 |

- IFS is a little drier on average, but at some locations the two differ by 0.2–0.3 m³/m³ throughout. Not yet looked into. A likely cause is the two models giving the cell different soil texture, which sets each model's field capacity and wilting point. If so, a percentile within each source's own years would agree better than the values, and the seam needs a shift (or a hand-off in percentile) to avoid a step.
- A spot check at Antigo (July 1, 2025, 12Z): ERA5-Land 0.340 at 0–7 cm, IFS 0.188.
- `elevation=nan` changed no moisture value at Antigo and only the 100–255 cm temperature (by 0.1 °C).
- Over the same hours, IFS's soil temperature averages 0.8–1.2 °C below ERA5-Land's (colder in the deeper layers), consistent with `soil.md`.
