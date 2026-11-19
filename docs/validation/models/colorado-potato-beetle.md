# Colorado potato beetle (`colorado-potato-beetle`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/colorado_potato_beetle.py`, a stage table run by the insect engine (`agmodels.phenology`, `InsectModel`); its page: `colorado_potato_beetle.md` beside it. Ported from the Crop Risk Tool on 2026-10-28 (PLAN.md Phase 3 D3; the tool's `insect_models$cpb` in `tmp/shiny/crop-risk-tool/src/models.R`). Two other models predict the same beetle from VDIFN's generation curves, `colorado-potato-beetle-adults` and `colorado-potato-beetle-larvae`, with their own reports.

**In short:** the model reproduces the Crop Risk Tool on the same weather: at Eau Claire in 2025 the level agrees on 363 of 365 days, and on the other 2 a stage begins a day later than in the tool. Its thresholds come from an unpublished analysis of 10 years of scouting data in Wisconsin's Central Sands (Bradford and Groves, UW–Madison Vegetable Entomology), which isn't in the project, so there is nothing published to reproduce and no comparison with observations beyond the fit's own data. The numbers on the model's page don't match its stage table (below).

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `cpb`; doc page `docs/insects/cpb.md`) | Single sine 10/30 °C from January 1, in °F·d; a stage table: 1st generation adult colonization 200, egg hatch 350, peak adults 600, peak larvae 800, pupation 935; 2nd generation adult emergence 1100, peak adults 1470, feeding continues 1800, adults begin dispersing 1970, mostly dispersed 2265, with severities 1, 2, 3, 4, 2, 3, 4, 3, 2, 1; the end-of-season freeze rule | All of it: the model |
| Bradford and Groves, unpublished analysis (cited on the model) | The tool's text: "derived from 10 years of scouting data in the Central Sands"; the risk score "represents the estimated total abundance of adults and larvae"; first colonization around 265, first-generation peak around 895, a decline through 1115, a second peak around 1375 | The citation; the analysis and its data aren't in the project |
| VDIFN, `cpb` (`../ag-vdifn/db/seeds.rb`) | Two sine-ramped generations, (265, 895, 1115) and (1115, 1375, 2500), 50/86 °F from January 1, with the same text | Not used for this model: these are the numbers the text describes (below) |
| VDIFN, `cpb-old` (`db/seeds.rb`) | An older model: 52 °F from May 1 or first egg masses; peak egg hatch 120 after first egg laying, larval instars to 400, second-generation adults from about 800 | Not used |
| Enviroweather (MSU), ColoradoPotatoBeetle (`docs/enviroweather-models.md`) | Single sine 52 °F, no upper, from March 1: generation 1 adults from 372 (peak 607), eggs from 459 (peak 699), larvae from 699 (peak 930); generation 2 adults peak 1376, flight ends 1780; abundance tables; no source cited | Compared only: its base and start differ, so its numbers aren't directly comparable with ours |

## Choices and differences

- **Degree days:** single sine, 50 °F, cutoff 86 °F, from January 1: the tool's thresholds. Which method and thresholds the scouting analysis used isn't recorded (`docs/insect-models.md`, a question for Ben).
- **One intended difference from the tool:** its `gdd_sine` skips the upper cutoff on days whose minimum is above the base; v2 keeps the Baskerville–Emin formula (PLAN.md Phase 3 D3).
- **Risk:** the stage table's step severities, less the shared end-of-season freeze reduction (after day 250, the number of days in the last 14 at or below −2 °C; the tool's rule, PLAN.md Phase 3 D3). The table's last stage (severity 1 from 2265) has no end (at Eau Claire in 2025 it began on September 9), so the reduction is what takes the level to 0 in fall.
- **Three models of one beetle:** this one (total adults and larvae as one score), and VDIFN's adults and larvae separately. Crop presets show this one and leave out the adults model beside it (`test_presets.py`).

## Checks

### Against the Crop Risk Tool on the same weather

`packages/agmodels/tests/test_insects.py::test_crop_risk_tool_insects_match_over_a_year[cpb-colorado-potato-beetle]`, run in CI, on fixtures made by the tool's own R code (`make_crt_fixtures.R`) for one cell at Eau Claire, Wisconsin, through 2025 (365 days: `crt_daily_eau_claire_2025.csv`, `crt_insect_cpb_eau_claire_2025.csv`):

- Each day's degree days equal the tool's (to 1e-9) on all but 14 days. On those 14 the minimum is above the base and the maximum above 86 °F; the tool's value is (min + max) / 2 − base, without the cutoff, and ours is lower, as the test asserts.
- Given the tool's own running totals, our severity, freeze reduction and stage label equal the tool's on all 365 days.
- End to end (computed from the same two fixtures; the test asserts the parts above, not this): the tool's season total runs ahead of ours by 4.3 degree days by June 30 and 7.7 by August 31, and stays 7.7 ahead. Two stages begin a day later in ours: first-generation peak larvae (800) on June 25 against the tool's June 24, and "2nd gen adults mostly dispersed" (2265) on September 9 against September 8. The level differs on those 2 days only, and agrees on the other 363.

The tool is the system v2 replaces, a reference rather than the truth (D54): this shows the port is faithful, not that the model is right.

### Against its sources and observations

None. The source is an unpublished analysis whose results and data aren't in the project, so there are no published numbers to reproduce, and no scouting or trap data outside the fit has been compared.

## Limits and open questions

- **The page doesn't match the model:** the model's page (and the tool's text it was copied from) gives first colonization around 265, a first-generation peak around 895, a decline through 1115 and a second peak around 1375. Those are VDIFN's `cpb` generations, (265, 895, 1115) and (1115, 1375, 2500). The stage table this model runs puts colonization at 200, the first-generation peak (severity 4) at 800, the gap at 935–1100 and the second peak at 1470. Which numbers the scouting analysis gave is a question for Ben; the page is rewritten in part I2.
- **Unknown method:** the analysis's degree-day method, base and start aren't recorded, so the model may count degree days differently from the fit.
- **Region:** fitted to the Central Sands, Wisconsin's main potato region; elsewhere the timing is untested.
- **What the score means:** the tool calls it estimated total abundance of adults and larvae, but the table is steps of severity, not a fitted abundance curve, and doesn't say how many beetles to expect.
- **Cheapest independent comparison:** the Vegetable Entomology Lab's Central Sands scouting records for years the fit didn't use (later years, or years held out of a refit), compared with the stage dates on the archive's weather at each field. The fit itself, if it can be recovered, would also settle the method and the page's numbers.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py -k crop_risk_tool   # the parity test
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # rebuild the fixtures from the tool (PLAN.md Phase 3 F)
```

The end-to-end figures: run `model("colorado-potato-beetle").outputs()` on `crt_daily_eau_claire_2025.csv`'s minimum and maximum (with the day of year) and compare `dd_total` and `risk()` with `crt_insect_cpb_eau_claire_2025.csv`'s `cum_gdd` and `severity`.
