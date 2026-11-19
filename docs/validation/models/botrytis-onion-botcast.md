# Botrytis leaf blight (BOTCAST) (`botrytis-onion-botcast`): validation

Model version 0.3, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/botcast.py`, reading the daily features `hours_rh_over_90_from_6pm`, `temperature_mean_rh_over_90_from_6pm`, `hours_temperature_over_30c`, `hours_rh_under_70` and `precipitation_sum`, with "hot in the last 5 days" and "dry" from `agmodels.features.across_days`; its page: `botcast.md` beside it. The notes this condenses are PLAN.md Phase 3 D (step 1), D50 and D74.

**In short:** a port of the Crop Risk Tool's BOTCAST (Sutton, James and Rowell 1986): a daily inoculum value (0 or 1) times a daily infection value (0–2), summed from emergence, with the tool's risk levels on the season total. From the tool's inputs, v2 reproduces its inoculum and infection tables exactly and its daily index on every day it scores; v2 leaves a day missing where an input that decides it is missing, where the tool scores it. Nothing in this round checks the tables against Sutton et al.'s paper, and the model hasn't been compared with Botrytis leaf blight in Wisconsin onion fields.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Sutton, James and Rowell 1986 (Agriculture, Ecosystems and Environment 18) | BOTCAST: an inoculum value from the last days' heat, dryness and humid hours, and an infection value from the wet period's length and temperature; their product is the daily disease severity index (DSI), summed to time the first spray | The method, through the tool (the paper isn't in `tmp/references/`) |
| The Crop Risk Tool (`botcast_dinov`, `botcast_dinfv`, `calc_botrytis_dsi`, `risk_for_botrytis`) | The two tables in code, the season total and five risk levels | The tables, the total and the levels; parity tests below |
| VDIFN (`../ag-vdifn/app/models/diseases/botrytis_leaf_blight.rb`) | Its own levels: Low below 21, "Threshold 1" (Moderate) 21–30, "Threshold 2" (High) 31–39, Very high from 40; 0 after a freeze | Compared only |
| Old AgWeather API (`../ag-weather/app/models/pest_models.rb`) | An infection table "read from the chart in the paper" and an inoculum value without the heat and dry-day conditions | Compared only (not run side by side) |

## Choices and differences

- **Inoculum (0 or 1),** tested in Sutton et al.'s order as the tool does: 0 after a hot spell (4 or more hours at or above 30 °C on any of the last 5 days); 0 with fewer than 5 humid hours; 1 with more than 12; otherwise 0 if the day before was dry (6 or more hours below 70 % RH and under 1 mm of rain) and 1 if not. The day before the first day read counts as not dry.
- **Infection (0–2)** from the humid hours and their mean temperature: 0 with 6 hours or fewer, below 6 °C or above 28 °C; at 8 °C or below, 1 from 13 hours and 2 from 23; 2 with 15 or more hours at 8–25 °C, 14 or more at 11–16.5 °C, or 11 or more at 13.5–16.5 °C; 0 for short warm periods (15 hours or fewer at 27 °C or above, 7 or fewer at 24 °C or above) and where hours − 12 ≤ 9 − temperature; 1 otherwise. The old API's reading of the same chart gives 2 from 10 hours at 13.5–16.5 °C and draws its last line strictly; v2 follows the tool's reading, which the parity test fixes.
- **The day:** humid hours and their temperature both from the day from 6 pm (readings 19:00–18:00 CST, D74), as for late blight; the tool counts the hours over the calendar day and their temperature from 8 pm. Leaf wetness is taken as RH ≥ 90 %, with gridded RH counted from 88 % (D50; on the archive at Eau Claire, May 15–September 30, 2025, this raised the season's DSI from 65 to 78, PLAN.md Phase 4's humidity note).
- **Missing data:** a day whose deciding inputs are missing has no DSI. The tool's R `case_when` treats a missing condition as false and can score such a day.
- **Risk:** the tool's levels on the season total from emergence (May 15 by default): Very low up to 10, Low above 10, Moderate above 20, High above 30, Very high above 40. Since the daily index is a whole number, Moderate starts at 21 and High at 31, VDIFN's two thresholds; VDIFN's Very high starts at 40 rather than 41, and its Low covers everything from 1.

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_vegetable_diseases.py`, run in CI, on the tool's fixtures (written by `make_crt_fixtures.R` from its R code and its recorded 2025 weather at one grid cell near Eau Claire, Wisconsin):

- **The tables:** the infection value matches the tool's in all 3,225 combinations of mean temperature (0 to 32 °C by 0.25) and humid hours (0 to 24), and the inoculum value in all 100 combinations of hot spell, dry day and humid hours.
- **A season from the tool's inputs:** the daily index matches the tool's on every day of 2025 that v2 scores; the only days v2 leaves missing are those with more than 6 humid hours and no temperature for them (the tool's pairing of calendar-day hours with 8 pm temperatures), which the test counts.
- **The pairing change, measured:** from the tool's hourly weather, with the threshold held at 90 %, v2's May 15 to September 30 total is within 20 % of the tool's. With the earlier day from 8 pm it was 46 against the tool's 44 (PLAN.md Phase 3 D); the day from 6 pm hasn't been summed in a note.

The tool is the model v2 replaces: this shows the port is faithful where intended, not that the tool is right (D54).

## Limits and open questions

- **The tables against the paper:** the infection table is a reading of a figure in Sutton et al. 1986, and the tool and the old API read it differently in places (above). Checking both tables against the paper is the first thing to do once it is in `tmp/references/`.
- **The risk levels** are the tool's; Sutton et al.'s own spray threshold on the season total hasn't been checked in this round (VDIFN's "Threshold 1" at 21 suggests it).
- **RH ≥ 90 % as leaf wetness,** as for late blight; the D50 shift was fitted on station RH and leaf wetness counts, not on disease. Onion fields on muck soils may stay wetter than the grid shows.
- **No field comparison:** nothing compares the model with first Botrytis leaf blight lesions in Wisconsin.
- **Cheapest independent comparison:** UW Vegetable Pathology's onion scouting records (first leaf blight lesions by field and date) in the muck-soil onion areas against the date the season's DSI passed 20; NEWA's onion disease tools, if one runs BOTCAST, on the same weather.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_vegetable_diseases.py -k botcast
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/R/crop-risk-tool
```
