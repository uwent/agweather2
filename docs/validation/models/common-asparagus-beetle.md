# Common asparagus beetle (`common-asparagus-beetle`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/common_asparagus_beetle.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `common_asparagus_beetle.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's one larval window, 105 to 405 degree days (50/86 °F) from January 1, reproduced exactly. Its source isn't known, it covers the first generation only, and it hasn't been compared with any observations.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `common-asparagus-beetle`) | Thresholds 50/86 °F, biofix January 1, one window (105, 250, 405); text: egg hatch begins around 105, larvae peak around 250 and end around 405, adults peak around 570; two to three generations a season | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | A link to UW Vegetable Entomology's page only | Nothing |
| Taylor and Harcourt 1978 ([doi:10.4039/Ent11057-1](https://doi.org/10.4039/Ent11057-1)) | Laboratory development rates of the immature stages (a candidate source, `docs/insect-models.md`) | Nothing yet: not in hand |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (105, 250, 405), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **One generation:** only the first generation's larvae, though VDIFN's own text says two to three generations a season; the adults' peak (570 by the text) isn't modelled.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generation, (105, 250, 405), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generation are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.
- The weather itself: VDIFN read its degree days from the old AgWeather API's daily grid; v2 reads its own archive. At Waunakee, January 1 to October 31, 2026, v2's single-sine 50/86 °F total was 3,184 against the old API's 3,203 (−0.6 %; `docs/validation/legacy/v1-dd-table.md`).

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The source of 105, 250 and 405 isn't identified.
- VDIFN's text describes overwintered adults feeding on spears in spring and summer feeding on ferns; neither is in the model.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** Taylor and Harcourt 1978's development rates turned into degree days from egg laying to the end of the larval stage, against the window's width (a published check, once the paper is in hand); no Wisconsin field record is known.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
