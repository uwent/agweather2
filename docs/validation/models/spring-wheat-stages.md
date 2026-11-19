# Spring wheat growth stages (`spring-wheat-stages`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/spring_wheat_stages.py`, run through `agmodels.crops` (D32–D34); its page: `spring_wheat_stages.md` beside it. Built in Phase 3 (PLAN.md, Phase 3's wheat growth stages, step 7).

**In short:** Bauer et al.'s (1984) Haun stages by growing degree days, as North Dakota's NDAWN runs them: the degree-day rule and NDAWN's stage table are reproduced exactly. Nothing else has been checked: there is no published error for the dates, no comparison with observed stages, and no legacy tool.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Bauer et al. 1984, NDSU Extension EB-37 | Haun stages of spring wheat by GDD from planting, base 32 °F | The method (through NDAWN's statement of it) |
| NDAWN, "Wheat growing degree days" (NDSU) | Daily GDD = mean of the maximum and minimum less 32 °F, both raised to 32, the maximum capped at 70 °F until Haun 2.0 and 95 °F after; a table from emergence (Haun 0.5, 180 GDD) through watery-ripe kernels (Haun 12.0, 1825) | The rule and the 17 stages of the table, unchanged |

## Choices and differences

- **Stages:** NDAWN's table only: emergence at 180 GDD, a leaf every 143 GDD from leaf 2 (395, 538, …), flag leaf, boot, heading from 1567 (Haun 10.2), flowering from 1739 to 1768 (Haun 11.4 to 11.6), watery ripe at 1825 (Haun 12.0). The table stops there, so grain fill and maturity aren't modelled.
- **The cap's switch:** the 70 °F cap applies on each day that starts with fewer than 395 GDD; the day that crosses Haun 2.0 is still counted with it.
- **Gating margin:** 3 days, borrowed from corn, because no error is published for these dates. Wheat scab isn't gated on these stages yet (PLAN.md's model review).
- **Winter wheat** isn't covered (D7; it waits for sources).

## Checks

### Against NDAWN's table and rule

NDAWN's statement of Bauer et al.'s (1984) method. `packages/agmodels/tests/test_crops.py::test_spring_wheat_gdd_rules_and_ndawn_table`, run in CI:

- On days of 59 and 86 °F, a day before Haun 2.0 counts (70 + 59) / 2 − 32 = 32.5 GDD and a day after it (86 + 59) / 2 − 32 = 40.5; a day of −10 and −1 °C counts 0 (both raised to 32 °F).
- The thresholds are NDAWN's (Haun 0.5 at 180, 2.0 at 395, 10.2 at 1567, 11.4 at 1739) and rise stage by stage.

`test_spring_wheat_over_a_season` is only a sanity check: planted April 21 on Lincoln, Nebraska's 2004 reanalysis weather, flowering begins on day 165 (June 13), inside the test's mid-June to mid-July range.

These show the code holds NDAWN's rule and numbers; they don't test the dates against a field.

## Limits and open questions

- No published error for the stage dates and no comparison with observations.
- Grain fill and maturity need another source (PLAN.md's model review).
- The table was developed in North Dakota; how well it fits spring wheat varieties grown in Wisconsin and Minnesota isn't known.
- **Cheapest independent comparison:** USDA NASS's weekly Crop Progress for spring wheat in Minnesota and North Dakota (percent emerged, jointed, headed, coloring), run from the same weeks' planting progress; or NDAWN's own wheat stage predictions for a North Dakota station, run on that station's weather (a check of the port, not of the dates).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_crops.py
```
