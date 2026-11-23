# Alfalfa growth since cutting (`alfalfa-growth`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/alfalfa_growth.py`, run through `agmodels.crops`; its page: `alfalfa_growth.md` beside it. Ported in Phase 3 (Phase 3 step 5) from the UW alfalfa tool (an R Shiny app; copy in `tmp/R/alfalfa-tool/`), which it replaces.

**In short:** growing degree days (single sine, 41/86 °F) from January 1 or the last cutting, with the tool's cutting window of 900–1100 GDD. The degree days are the tool's formula exactly. Neither the window nor the degree days has been compared with alfalfa growth or forage quality measured in Wisconsin fields.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| The UW alfalfa tool (`tmp/R/alfalfa-tool/app/global.R`) | GDD base 41 °F as `gdd_sine(41) − gdd_sine(86)` from the old AgWeather API's daily minimum and maximum; cut at 900–1100 GDD since January 1 or the last cutting; fall guidance (under 360 GDD, or enough to reach maturity again, before a killing freeze); cut scheduling on climate averages | The degree days and the cutting window |
| Newell, "Managing fall alfalfa cutting for persistence" (UW–Madison Extension) | The fall rule only: a last cut should leave under 360 or over 900 GDD (base 41 °F) before the killing freeze (from Canadian research reported in base 5 °C); it doesn't give the 900–1100 cutting window, which is the tool's own and has no published source found so far | The window; the fall rule waits (below) |
| Iowa State University Extension, "Should I take a late fall alfalfa cutting?" | The 900 and 360 GDD fall rule | Cited for the fall rule |
| UW–Madison Extension, "Timing of fall alfalfa harvest can impact long-term viability of the stand" | Fall cutting and stand persistence | Background |

## Choices and differences

- **Degree days:** single sine with a horizontal cutoff, 41/86 °F. The tool subtracts the sine above 86 °F from the sine above 41 °F, which is the same quantity (D26). Its `gdd_sine` has one ordering slip: when the minimum is above the base it returns the plain mean less the base without cutting the maximum at the upper threshold. The tool only calls it with its default upper of 150 °F, which no day reaches, so on real days its values match ours (the plans, `docs/plans/`).
- **Stages:** Growing, Ready to cut (900–1100 GDD), Past the cut window (over 1100). The tool's own text gives 800–1100 in one place and 900–1100 in the others; we follow 900–1100.
- **Not yet ported:** the fall rule and the tool's cut scheduling, which need the climatology and a projection to the end of the season (Phase 6). The tool's text puts the upper fall figure at 800 GDD; Newell's article at 900.
- **Against Enviroweather (MSU):** MSU's first-cutting model uses the simple average, base 41 °F without an upper, from March 1, with targets of 680, 750 and 970 GDD by silo type and fiber (`docs/enviroweather-models.md`). The averaging method gives fewer GDD on cool spring days, which partly explains its lower targets; which thresholds to keep is part F of `docs/plans/models.md`.

## Checks

### Against the UW alfalfa tool

`packages/agmodels/tests/test_crops.py::test_alfalfa_gdd_are_the_tools_difference_of_sines`, run in CI: over Lincoln, Nebraska's 2004 season (reanalysis weather, April to October), our daily GDD equal the tool's formula, the 41 °F sine less the 86 °F sine, within 1e-9 °F·d on every day. The tool's formula is re-expressed with our sine function, not run in R; the slip in its R function (above) can't arise below 150 °F. The test also checks the stage boundaries at 900 and 1100 GDD.

`packages/agmodels/tests/test_degree_days.py::test_matches_the_old_api`: our single sine matches the old AgWeather API's calculator within 0.000001 °F·d. The tool read its daily minimum and maximum from the old API's grid; at Waunakee, January 1 to October 31, 2026, v2's archive gave 3,184 single-sine 50/86 °F degree days against the old API's 3,203 (−0.6 %; `docs/validation/legacy/v1-dd-table.md`). The old API is a reference, not the truth (D54).

## Limits and open questions

- The 900–1100 window is a rule of thumb for forage quality and regrowth; no comparison with measured quality (RFV, NDF) or stage at cutting has been made.
- GDD from January 1 count warm winter days before green-up.
- The fall rule and the cut schedule aren't available yet.
- **Cheapest independent comparison:** county Scissors Cut programs' spring samples in Wisconsin (the date and forage quality of fields before first cutting), against GDD from January 1 on the archive at each field.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_crops.py packages/agmodels/tests/test_degree_days.py
```
