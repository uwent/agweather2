# Corn earworm (`corn-earworm`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/corn_earworm.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `corn_earworm.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's larval window, 70 to 440 degree days (55/92 °F) after August 1, reproduced exactly. August 1 stands in for the moth flight or first silk that the sources count from, and the model hasn't been compared with Wisconsin's trap counts.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `corn-earworm`) | Thresholds 55/92 °F, biofix August 1, one window (70, 275, 440); text: set the biofix to the date first eggs or adults are seen; eggs hatch around 70, larvae and damage peak around 275, larvae leave the ears around 440 | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | USPest's model (`cew`) from Hartstack et al. 1976 (MOTHZV-2, a USDA report); single sine 55/92 °F with the biofix at first silk | Nothing yet |

## Choices and differences

- **Degree days:** single sine, 55/92 °F, from August 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (70, 275, 440), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Biofix:** a fixed August 1, VDIFN's default. VDIFN's text asks growers to set it to the date first eggs or adults are seen, and USPest counts from first silk; a grower can set their own date at a point.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generation, (70, 275, 440), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 55/92 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generation are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The source's events (MOTHZV-2) haven't been read; Butler 1976 ([doi:10.1093/ee/5.3.520](https://doi.org/10.1093/ee/5.3.520)) is only a guess at the laboratory work behind them.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** DATCP's weekly Pest Bulletin trap counts of corn earworm moths, 2020–2026: each year's first significant flight against August 1, and the window counted from that flight.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
