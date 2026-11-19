# Carrot foliar blight disease severity values (TOMCAST) (`carrot-foliar-dsv`): validation

Model version 0.4, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/carrot_foliar.py`, reading the daily features `hours_rh_over_90_from_6pm` and `temperature_mean_rh_over_90_from_6pm`; its page: `carrot_foliar.md` beside it. The notes this condenses are PLAN.md Phase 3 D (step 1 and "TOMCAST to FAST's table"), D50, D74, and `docs/enviroweather-models.md`'s TOMCAST entry.

**In short:** TOMCAST's daily disease severity values (DSV, 0–4) from hours of leaf wetness, taken as RH ≥ 90 %, and their mean temperature, with risk from the last 7 days' total, for Alternaria and Cercospora leaf blights of carrot. The table is FAST's (Madden, Pennypacker and MacNab 1978, Table 1), checked cell by cell in a test; where the Crop Risk Tool's table is an hour off from FAST's, v2 follows FAST, and everywhere else it matches the tool. The risk levels are the tool's and VDIFN's; nothing in this round compares the model with carrot leaf blight in the field.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Madden, Pennypacker and MacNab 1978 (Phytopathology 68), FAST (`tmp/references/diseases/`) | Table 1: the hours of leaf wetness at which each band of mean temperature during wetness (13–17, 18–20, 21–25, 26–29 °C) earns 1 to 4 severity values; a 7-day total of them (CS), with spray limits of 11 to 16 tried in one season's trial on tomato in Pennsylvania (Table 3) | The table, and the 7-day total |
| Pitblado 1992, TOM-CAST (Ridgetown College, Ontario) | FAST's severity values without its second (rating) model, summed to time sprays on processing tomato | The method's name and use (the report isn't in `tmp/references/`) |
| The Crop Risk Tool (`calc_alternaria_dsv`, `risk_for_alternaria`) | The table with its first steps an hour late and its band edges one way; risk from the 7-day total | The 7-day risk levels; parity tests below |
| VDIFN (`../ag-vdifn/app/models/diseases/carrot_foliar.rb`) | The same 7-day levels (5, 10, 15, 20) | The same levels |
| Old AgWeather API (`../ag-weather/app/models/pest_models.rb`) | FAST's table with v2's band edges | Compared only |
| Enviroweather (MSU) TOMCAST (`docs/enviroweather-models.md`) | Wet periods split within a noon-to-11 am day, sensor wetness, 0 above 29 °C, cumulative since the last spray with cautions at 15, 18 and 20 | Compared only |

## Choices and differences

- **Table (FAST's):** 13 °C to under 18: 1 DSV from 7 hours, 2 from 16, 3 from 21 (no 4); 18 to under 21: 1 from 4, 2 from 9, 3 from 16, 4 from 23; 21 to under 26: 1 from 3, 2 from 6, 3 from 13, 4 from 21; from 26: as at 18–20. Below 13 °C a day earns nothing. The bands are FAST's whole degrees read as half-open ranges on unrounded temperature.
- **Above 29 °C:** FAST's table stops at 29 °C; v2 keeps its last row above 29, as the tool does (the module says TOMCAST keeps it, but Pitblado 1992 hasn't been read in this round), where Enviroweather scores 0. Wet periods above 29 °C are rare in Wisconsin carrot season.
- **Against the tool:** its first step is an hour late at 13–17 °C (8 hours; FAST 7) and 18–20 °C (5 hours; FAST 4), and its band edges put 18, 21 and 26 °C in the band below. Ben confirmed FAST's table from the paper (PLAN.md Phase 3 D); the old API already had it right.
- **The day:** all hours with RH ≥ 90 % in the day from 6 pm (readings 19:00–18:00 CST, D74) and their mean temperature, as for late blight; the tool counts the hours over the calendar day and their temperature from 8 pm. FAST and Enviroweather score separate wet periods; v2 adds all humid hours in the day into one. Gridded RH is counted from 88 % (D50; on the archive at Eau Claire, May 15–September 30, 2025, this raised the season's DSVs from 130 to 150, PLAN.md Phase 4's humidity note).
- **Risk:** the last 7 days' total, as the tool and VDIFN have it: Very low below 5, Low from 5, Moderate from 10, High from 15, Very high from 20. FAST's own spray rule is a 7-day total too, at limits between 11 and 16 in its trial; TOMCAST as Enviroweather runs it is the total since the last spray, at 15 to 20. The season total since planting or the last spray (June 1 by default) is an output but doesn't set the risk.
- **Missing data:** a day without its inputs has no DSV; no humid hours gives 0.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_vegetable_diseases.py::test_tomcast_table_is_fasts`, run in CI: FAST's Table 1 (Madden et al. 1978), written into the test as the hours at which each band reaches each value, against the model at the bottom of each of the four bands, half a degree above it and just under its top (17.9, 20.9, 25.9 and 29.9 °C) and every whole hour from 0 to 24; and 0 at every hour at 12.9 °C, below the table's 13. All match.

### Against the Crop Risk Tool

`packages/agmodels/tests/test_vegetable_diseases.py`, run in CI, on the tool's fixtures (written by `make_crt_fixtures.R` from its R code and its recorded 2025 weather at one grid cell near Eau Claire, Wisconsin):

- **The table:** of 3,775 combinations of mean temperature (5 to 35 °C by 0.2) and humid hours (0 to 24), every one matches the tool's except those where FAST's table differs from the tool's (the late first steps and the band edges, named in the test's `fast_differs`), and those do differ.
- **A season from the tool's inputs:** the daily DSVs match the tool's on every day of 2025 except where FAST's table differs; given the tool's daily values, the 7-day totals and risk levels match on every day. FAST's table changes 2 days of that season, from 99 to 101 DSVs between May 15 and September 30 (PLAN.md Phase 3 D).
- **The pairing change:** from the tool's hourly weather, with the threshold held at 90 %, v2's May 15 to September 30 total is within 20 % of the tool's (with the earlier day from 8 pm, 97 against 99, PLAN.md Phase 3 D).

The tool is the model v2 replaces: this shows the port is faithful where intended, not that the tool is right (D54).

## Limits and open questions

- **No field comparison:** the 7-day levels (5, 10, 15, 20) come from the tool and VDIFN; nothing in this round ties them to carrot leaf blight in Wisconsin or to a spray trial. FAST was developed for early blight of tomato in Pennsylvania; its use for carrot leaf blights rests on extension practice, not on a comparison here.
- **Above 29 °C:** whether TOMCAST keeps FAST's last row above 29 °C (v2, the tool) or scores 0 (Enviroweather) should be checked in Pitblado 1992.
- **RH ≥ 90 % as leaf wetness,** with the D50 shift fitted on station RH and leaf wetness counts, not on disease; one humid count a day rather than FAST's wet periods.
- **Cheapest independent comparison:** Enviroweather's TOMCAST code (inventoried in `docs/enviroweather-models.md`) on Wisconet stations' leaf wetness hours against ours on the archive at the same cells, which tests the RH proxy and the day together; then UW Vegetable Pathology's carrot foliar blight trials or scouting (first symptoms) against the 7-day levels.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_vegetable_diseases.py -k "tomcast or carrot or pairing"
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/R/crop-risk-tool
```
