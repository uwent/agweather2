# Cercospora leaf spot daily infection values (`cercospora-beet-div`): validation

Model version 0.3, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/cercospora_beet.py`, reading the daily features `hours_rh_over_90_from_6pm` and `temperature_mean_rh_over_90_from_6pm`; its page: `cercospora_beet.md` beside it. The notes this condenses are PLAN.md Phase 3 D (step 1), D50 and D74.

**In short:** a port of the Crop Risk Tool's Cercospora leaf spot model for beet: daily infection values (DIV, 0–7) from Windels et al.'s (1998) table of humid hours and their mean temperature in °F, with risk from the higher of the last 2 days' and last 7 days' mean. From the tool's inputs, v2 reproduces its table, daily values, 7-day means and risk exactly. The table hasn't been checked in a test against Windels et al.'s paper, and the model hasn't been compared with Cercospora leaf spot in the field.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Windels, Lamey, Hilde, Widner and Knudsen 1998 (Plant Disease 82) | The sugar beet industry's model in Minnesota and North Dakota: a table of daily infection values from hours of RH ≥ 90 % and their mean temperature in °F, and spray advice from 2-day and 7-day values | The method, through the tool (the paper isn't in `tmp/references/`) |
| The Crop Risk Tool (`calc_cercospora_div`, `risk_for_cercospora`) | The table in code (°F bands, taking °C), and five risk levels on the 2-day and 7-day means | The table and the levels; parity tests below |
| VDIFN (`../ag-vdifn/app/models/diseases/cercospora_leaf_spot.rb`) | The same levels, citing Windels et al. | The same levels |
| Old AgWeather API (`../ag-weather/app/models/pest_models.rb`) | The same table over the calendar day; 0 for a day without data | Compared only |
| Cornell Vegetables' table beet fact sheet | Cercospora leaf spot of table beet and its management | Background for table beet |

## Choices and differences

- **Table:** no DIV at or below 60 °F; from 61 °F the hours needed fall as it warms (61 °F: 1 DIV from 22 hours; 66–71 °F: 1 from 4 hours up to 6 from 22); from 74 °F every humid day starts at 1, and above 82 °F the steps come every 1 to 2 hours up to 7. Temperatures in °C are converted to °F and read into the table's whole-degree bands (each band up to and including its upper degree).
- **The day:** humid hours and their temperature both from the day from 6 pm (readings 19:00–18:00 CST, D74), as for late blight; the tool counts the hours over the calendar day and their temperature from 8 pm. Gridded RH is counted from 88 % (D50; on the archive at Eau Claire, May 15–September 30, 2025, this raised the season's DIVs from 124 to 158, PLAN.md Phase 4's humidity note).
- **No humid hours give 0.** The tool's table starts its warm bands at 1, so with 0 humid hours at a warm temperature it gives 1; that can't happen in its own runs (no humid hours, no temperature), and v2 gives 0.
- **Risk:** the tool's and VDIFN's levels: Very high when the last 7 days average 5 or more or the last 2 days 5.5; High from 3 or 3.5; Moderate from 1.5 or 2; Low from 0.5 or 1. Days count from planting (June 1 by default).
- **Crops:** the spec lists sugar beet only, though the summary and the tool's page speak of table and sugar beet.

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_vegetable_diseases.py`, run in CI, on the tool's fixtures (written by `make_crt_fixtures.R` from its R code and its recorded 2025 weather at one grid cell near Eau Claire, Wisconsin):

- **The table:** all 12,024 combinations of mean temperature (10 to 35 °C by 0.05, about 0.1 °F) and 1 to 24 humid hours give the tool's DIV exactly (the sweep's 501 rows at 0 hours are left out, above).
- **A season from the tool's inputs:** the daily DIVs, their 7-day means (to rounding) and the risk levels match the tool's on all 365 days of 2025.
- **The pairing change:** from the tool's hourly weather, with the threshold held at 90 %, v2's May 15 to September 30 total is within 20 % of the tool's (with the earlier day from 8 pm, 102 against 100, PLAN.md Phase 3 D).

The tool is the model v2 replaces: this shows the port is faithful where intended, not that the tool is right (D54).

## Limits and open questions

- **The table and levels against the paper:** Windels et al. 1998 isn't in `tmp/references/`; both are the tool's and VDIFN's, unchecked against the source in this round.
- **Developed for sugar beet in the Red River Valley,** with in-field stations; its use for table beet in Wisconsin, and the D50 shift (fitted on station RH and leaf wetness counts, not on disease), are untested.
- **No field comparison** in Wisconsin.
- **Cheapest independent comparison:** NDAWN's Cercospora leaf spot daily infection values for sugar beet (Windels' model as the industry runs it on its stations in Minnesota and North Dakota) against ours at the same places for a season; then table beet scouting records, if UW Vegetable Pathology has them.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_vegetable_diseases.py -k "cercospora or pairing"
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/shiny/crop-risk-tool
```
