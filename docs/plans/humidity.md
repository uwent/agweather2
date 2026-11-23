# Open-Meteo's humidity outside Wisconsin: plan

A short plan of its own (Ben, 2026-11-19), from D100's follow-up ([decisions.md](../decisions.md)). Results go in `docs/validation/weather/openmeteo-humidity.md`; this file says what to do next and why.

## Status

**Updated 2026-11-21.** Branch `phase-6`.

- **Where things stand:** D100 keeps D51's humidity map to a lat/lon box around the Upper Midwest (`agdata.sources.openmeteo.RH_MAP_AREA`) and counts pecan scab's 90 % at D50's 88 %, after five Oklahoma Mesonet stations showed the map made spring 2–4 times too humid there. The box is a stopgap with a cliff at its edge. Ben chose to replace it with a statistical correction from the hour's own weather (below), adopted only if it clearly beats the simplest option: no map, raw Open-Meteo counted at one threshold.
- **Downloads complete (2026-11-21):** `data/urma-sample/` holds URMA's hourly TMP and DPT at 9,365 lattice cells (every 20th row and column of the NDFD grid, ~50 km) and the five Oklahoma stations' cells for every day of 2024 and 2025 and 2026-01-01 to 2026-11-15 (`scripts/fetch_urma_sample.py`; logs `fetch-<year>*.log`). About two dozen hours failed on dropped connections (9 in 2024, a few in 2025 and 2026) and stay NaN inside their days' files; rerunning skips written days, so they'd need the day's file deleted first, which a statistical fit doesn't need.
- **Next:** step 1.

## Why not a simpler fix

- **A height correction doesn't apply:** Open-Meteo's `temperature_2m` and `relative_humidity_2m` are 2 m values, as are URMA's and the stations' (FAO-56's 10 m → 2 m step is for wind). The undercount is smoothing: a model cell's humidity rarely saturates the way a sensor does on a calm, clear night.
- **Elevation is a possible terrain effect:** Open-Meteo moves temperature to a point's elevation (about 0.2 °C at Madison, CLAUDE.md); if the dew point isn't moved the same way, RH shifts with elevation. Elevation is a predictor below.
- **A lattice or climate regions** (the first proposal) was dropped: not terrain-aware, and more data at run time for an uncertain payoff (Ben).

## Steps

### 1. Is URMA the right target outside Wisconsin? (S)

D50's 88 % was established for the archive (URMA) at Wisconet. Count URMA's hours at the five Oklahoma stations' cells (in `data/urma-sample/`, named in `cells.npz`) at 84–92 % against the stations' 90 % (the Mesonet files cached in `tmp/pecan-check/mesonet/`; reuse `tmp/pecan-check/analyze.py`'s station reading), March–August 2024 and 2025, as the pecan check did for Open-Meteo: matching threshold pooled and by station-season, by month, crossing dates.

- If URMA matches near 88 %: URMA is a sound national target; go on.
- If not: D50 is itself regional, and the target (and D50) need rethinking before any fit. Stop and decide with Ben.

### 2. The statistical correction (M)

A correction from the hour's own weather, with no lookup data at run time:

- **Response:** Open-Meteo's dew point depression (temperature − dew point) transformed to URMA's, keeping temperature (as D51 does), so RH is recomputed.
- **Predictors**, all in Open-Meteo's own response: the dew point depression, 10 m wind speed, cloud cover, solar hour and day of year (as smooth cycles), and the point's elevation (the API returns the one it used). Calm, clear nights near saturation are where the humid hours go missing; these describe them anywhere.
- **Form:** a small monotone transform, for example `corrected = a · depression^b` with `a` and `b` linear in the predictors (or smooth terms with few degrees of freedom); fitted so the distribution of corrected depressions matches URMA's (quantile loss or a distributional fit), not just the mean, since hours past a threshold are what count. A handful of coefficients, kept in `agdata/data/` as a versioned table with `agdata.corrections` describing it.
- **Data:** a fixed-seed random sample of land cells (inside a US county) from the lattice: ~500 to fit and ~200 held out, never used in fitting. Open-Meteo hourly at each (v2's own fetch, NBM then best_match, through the commercial key, paced and cached; hundreds of requests). Fit on 2025; test on 2026 (NBM in both; 2024's Open-Meteo history is best_match, a different model). Refit on both years once the test passes.
- **Code** (only if adopted): `calibration` gains the transform; `openmeteo.correct` applies it everywhere and `RH_MAP_AREA` goes; D51's map table retires; `agdata.corrections`, `docs/corrections.md`, D101.

### 3. Adopt only if it clearly wins (S)

Compare three options at the held-out cells (2026, against URMA), the five Oklahoma stations (against the Mesonet, reusing the pecan check: season ratio, crossing dates, spray count) and Wisconet's 80 stations (against `openmeteo.md`'s numbers):

1. no map: raw Open-Meteo counted at one threshold (fitted on the same data; about 86–87 % from the two regions so far);
2. the box (D100, now);
3. the statistical correction.

Measures: hours a day at the counting threshold by region and season (bias and spread), threshold-crossing dates for a model like pecan scab, and continuity (no jump between neighbouring points). Adopt 3 only if it beats 1 clearly at held-out cells and at both station networks; otherwise adopt 1 (the box and D51's RH map go). Record the choice as D101 and the numbers in `docs/validation/weather/openmeteo-humidity.md`.

## Sizing and risks

- **Size:** M overall (step 1 S; the fit script and the comparison M; the code change S if adopted). No archive rebuild: corrections apply as hours are read from the cache.
- **Risks:** URMA may not match stations outside Wisconsin (step 1 decides); Open-Meteo's humidity changes from year to year (D51 saw ±1 h a day), so one year's fit carries that; the West's mountains and coasts may need more predictors or a caveat; NBM's history in Open-Meteo starts within 2025, so tests mix models before then.
- **Alternatives kept in view:** fading D51's map with distance from Wisconsin (S, still a guess); per-region maps (dropped).
