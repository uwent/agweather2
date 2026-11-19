# Corn growth stages (`corn-stages`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/corn_stages.py`, run through `agmodels.crops` (D32–D34); its page: `corn_stages.md` beside it. Built in Phase 3 (PLAN.md, Phase 3's crop growth stages, step 4).

**In short:** the stage thresholds reproduce their published sources (NCH-40's table for a 2700 GDD hybrid within 2.1 %, Ohio State's V9 within 10 GDD). On the four field seasons Yang et al. (2004) published, run on reanalysis weather at each site, emergence and silking came within 3 days of the observed dates. There is no check against Wisconsin fields, and no legacy parity: the old AgWeather site's corn table was never vetted.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Neild and Newman 1987, National Corn Handbook NCH-40 (Purdue) | GDD from planting to each reproductive stage for a 2700 GDD hybrid (Table 3: silking 1400, blister 1660, dough 1925, kernels denting 2190, dented 2450, black layer 2700); maturity classes early 2100–2400, mid 2400–2800, full 2900–3200 | R2, R4, R5 and R5.5 as fractions of the time from R1 to R6; the maturity presets (2100 to 3100) |
| Yang et al. 2004, Hybrid-Maize (eq. 12, 107 hybrids) | Silking from a hybrid's GDD total: 100 + 0.445 × GDD (°C·d, base 10 °C, from emergence), less 50 °C·d for irrigated fields at yield potential; Table 1's field seasons | R1 = 180 + 0.445 × GDD from emergence to black layer, in °F·d, without the irrigated offset; the four seasons as a check |
| Nielsen, "Use thermal time to predict leaf stage development in corn" (Purdue) | Emergence in 100–120 GDD; a leaf collar every 82 GDD to V10, then every 50 (from Wuethrich's 14 hybrids) | VE at 110; the V-stages |
| Nielsen, "Grain fill stages in corn" (Purdue) | Milk stage about 900 GDD before black layer; R5 at 31–33 days after silking | R3's fraction; R5 at the start of denting |
| Abendroth et al. 2011, PMR 1009 (Iowa State) | Staging definitions; most hybrids have 18–21 leaves | Stage descriptions; a check on the leaf count |

## Choices and differences

- **Degree days:** modified 50/86 °F (the minimum raised to 50, both capped at 86), from planting.
- **R1 (silking):** Yang et al.'s fit, not NCH-40's 1400, so silking moves with the hybrid's rating. For a 2700 GDD hybrid it falls at 1442.5 GDD from planting. The fit's 50 °C·d offset for irrigated fields at yield potential isn't taken: fields in general are the fit's own population.
- **VT (tasseling):** one leaf interval (50 GDD) before R1, flagged as estimated. This assumption gives the last leaf as V13, V15, V17, V19, V21 and V22 for the 2100 to 3100 GDD presets; PMR 1009 says most hybrids have 18–21. It's to be checked against PMR 1009 (PLAN.md).
- **Grain fill:** R2 to R6 at NCH-40's fractions of the GDD from R1 to R6, so they scale with the hybrid. R5 is NCH-40's "kernels denting", R5.5 (half milk line) its "kernels dented"; Nielsen's older article labels these R4.5 and R5.
- **Leaf counts:** NCH-40's leaf numbers (6 leaves at 475 GDD) count leaf tips and run ahead of the collar method, so they aren't used.
- **Gating margin:** 3 days either side of a disease's stage window (tar spot, gray leaf spot, Gibberella ear rot), the error seen on Yang et al.'s seasons (below).
- **No legacy parity:** the old AgWeather site's corn table (V8 at 600 … R6 at 2400–2600 from May 15) predates current staff and isn't vetted (PLAN.md), so v2 isn't compared with it.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_crops.py::test_corn_matches_nch40_for_a_2700_gdd_hybrid`, run in CI. Thresholds for a 2700 GDD hybrid, GDD from planting (the test's tolerance in brackets):

| Stage | Ours | Source | Tolerance |
| --- | --- | --- | --- |
| VE | 110 | Nielsen, 100–120 | exact |
| V9 | 848 | Ohio State AGF-0101, 838 | 20 GDD |
| R1 | 1442.5 | NCH-40, 1400 (ours from Yang et al.) | 5 % |
| R2 | 1694 | NCH-40, 1660 | 3 % |
| R4 | 1950 | NCH-40, 1925 | 3 % |
| R5 | 2207 | NCH-40, 2190 | 3 % |
| R5.5 | 2458 | NCH-40, 2450 | 3 % |
| R6 | 2700 | NCH-40, 2700 | 3 % |

R2 to R6 come within 2.1 % of NCH-40 (R2 the farthest, 1694 against 1660; R1, from Yang et al. instead, is 3 % later than its 1400), and V9 within 10 GDD of Ohio State's 838. `test_corn_leaves_and_stages_scale_with_maturity`: thresholds rise stage by stage for every preset, a 2700 GDD hybrid has 19 leaves (inside 18–21), and earlier hybrids have fewer.

### Against Yang et al.'s field seasons

`test_crops.py::test_corn_seasons_from_yang_et_al`, run in CI: the four seasons of Yang et al. (2004) Table 1, Lincoln, Nebraska (1999, 2000, 2001) and Manchester, Iowa (2002), run as the paper ran them, with each season's own GDD from planting to maturity as the hybrid's rating. The weather is ERA5 reanalysis from Open-Meteo at each site (`packages/agmodels/tests/fixtures/phenology_weather.csv`), not the sites' own stations. The test allows 3 days for emergence and silking and 1 for black layer; the differences it found (ours − observed, days):

| Season | Rating (GDD) | VE | R1 | R6 |
| --- | --- | --- | --- | --- |
| Lincoln 1999 | 2752 | −1 | +2 | −1 |
| Lincoln 2000 | 2631 | +2 | −1 | −1 |
| Lincoln 2001 | 2828 | −1 | +3 | −1 |
| Manchester 2002 | 2665 | +3 | +2 | 0 |

Emergence and silking came within 3 days in all 4 seasons. Black layer isn't an independent check: the rating is the season's own GDD to maturity, so R6 lands within a day of maturity by construction. These seasons were published with the model whose silking fit we use, so they show the port reproduces it, not how it does on new fields.

## Limits and open questions

- No Wisconsin comparison: neither observed stage dates nor a crop progress series has been compared with the model.
- VT's placement and the leaf counts it implies are assumptions until checked against PMR 1009.
- The rating on a seed bag is a seed company's own GDD figure, and companies compute it differently; the model's dates can only be as good as the rating.
- Maps use the default 2500 GDD hybrid everywhere until location-adjusted maturity (D66, parked) is built.
- **Cheapest independent comparison:** USDA NASS's weekly Crop Progress for Wisconsin (percent emerged, silking, dough, dented, mature), run from the same weeks' typical planting dates over 2016–2025 (state-wide percentages, so a check on the season's timing rather than on any field); better, a few Wisconsin fields with recorded planting dates, ratings and stage dates.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_crops.py
uv run python packages/agmodels/tests/fixtures/make_phenology_weather.py   # the ERA5 seasons (needs the network)
```
