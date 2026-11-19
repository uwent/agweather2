# Crucifer flea beetle (`crucifer-flea-beetle`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/crucifer_flea_beetle.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `crucifer_flea_beetle.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's two summer-generation adult windows, base 50 °F from January 1, reproduced exactly. The overwintered adults that feed on seedlings in spring aren't in the model, the source isn't identified, and it hasn't been compared with any observations.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `crucifer-flea-beetle`) | Threshold 50 °F, no upper, biofix January 1, two windows (820, 965, 1155) and (1640, 1785, 1975); text: adults most damaging, two generations typical in Wisconsin, first-generation adults from 820, second from 1,640 | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | UC IPM's crucifer flea beetle page | Nothing yet: not read |
| Ulmer and Dosdall 2006 ([doi:10.1016/j.cropro.2005.03.003](https://doi.org/10.1016/j.cropro.2005.03.003)) | Emergence of overwintered and new-generation adults (a candidate source) | Nothing yet: not in hand |

## Choices and differences

- **Degree days:** single sine, 50 °F with no upper threshold, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (820, 965, 1155) and (1640, 1785, 1975), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside; where two windows touch, the later one's value.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Spring adults:** the windows start at 820, the new generation's adults; the overwintered adults' emergence and feeding before then isn't modelled.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generations, (820, 965, 1155) and (1640, 1785, 1975), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50 °F (no upper) match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generations are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The source isn't identified, and the spring flight of overwintered adults, isn't covered; VDIFN's own text calls flea beetles an early-season pest whose heavy feeding on young plants can reduce yields or kill them.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** Ulmer and Dosdall 2006's emergence of overwintered and new-generation adults, in degree days, against the windows (a published check, once the paper is in hand).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
