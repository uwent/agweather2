# Cabbage looper (`cabbage-looper`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/cabbage_looper.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `cabbage_looper.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's two larval feeding windows, 50/90 °F degree days from May 15, reproduced exactly; VDIFN's own code was run on this model's table in the test. The generations are 790 degree days apart, close to the egg-to-adult time the review notes attribute to Toba et al. 1973 (791.5), not yet confirmed in the paper. Not compared with field observations.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `cabbage-looper`) | Thresholds 50/90 °F, biofix May 15, two windows (325, 520, 750) and (1115, 1310, 1540); text: first small larvae around 325 after May 15 | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | USPest's cabbage looper model (`cbl`) from Toba et al. 1973: single sine 50/90 °F, biofix at the first pheromone-trap catch | Nothing yet |
| Toba et al. 1973 ([doi:10.1093/aesa/66.5.965](https://doi.org/10.1093/aesa/66.5.965); in `tmp/references/insects/`) | Laboratory development rates at constant temperatures (Riverside, California); no development of the immature stages at 7.2 °C, no normal adults after 10.0 or 12.7 °C | Nothing directly; the review notes put its egg-to-adult time at 791.5 degree days, matching VDIFN's spacing (1115 − 325 = 790), a figure not found in the paper's text at a glance |

## Choices and differences

- **Degree days:** single sine, 50/90 °F, from May 15, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (325, 520, 750) and (1115, 1310, 1540), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside; where two windows touch, the later one's value.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Biofix:** a fixed May 15. Loopers migrate north each year, so the first trap catch (the source's biofix) varies; May 15 has no source (`docs/insect-models.md`).
- **Generations:** two of equal width (425 degree days each), as VDIFN had them; no third.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generations, (325, 520, 750) and (1115, 1310, 1540), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. One of the four (`generations_2`) is this model's own table, so VDIFN's code was run on exactly these numbers.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50/90 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generations are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The 791.5 egg-to-adult figure comes from the review notes, which took it from USPest's summary; confirm it in Toba et al.'s tables before using it as a check.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** Wisconsin pheromone-trap first catches of cabbage looper (UW Vegetable Entomology's or DATCP's records, if they keep them: to find) against May 15, then larval scouting against the windows.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
