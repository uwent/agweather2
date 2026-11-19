# European corn borer (`european-corn-borer`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/european_corn_borer.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `european_corn_borer.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's two moth flights, 50/86 °F degree days from January 1, reproduced exactly. Its source isn't identified; the page's description gives the wrong numbers for the first flight; and it hasn't been compared with Wisconsin's black light trap counts or NEWA's model.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `european-corn-borer`) | Thresholds 50/86 °F, biofix January 1, two flights (550, 740, 900) and (1660, 1950, 2190); a text whose first-flight numbers (329, 472, 636) are corn rootworm's | The thresholds and flights, unchanged; the text as the page's summary (a slip, below) |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | University of Kentucky's EF-106 | Nothing yet: not read |
| Matteson and Decker 1965 ([doi:10.1093/jee/58.2.344](https://doi.org/10.1093/jee/58.2.344)); Anderson et al. 1982 ([doi:10.1093/ee/11.6.1307](https://doi.org/10.1093/ee/11.6.1307)) | Development at constant and variable temperatures; postdiapause development and spring emergence | Nothing yet (both in `tmp/references/insects/`, not read for this report) |
| Enviroweather (MSU), European corn borer (`docs/enviroweather-models.md`) | Single sine 50 °F, no upper, from March 1: flights at 450–950, 1,450–1,950 and 2,450–2,950 ("rough numbers" in its code) | Compared only (below) |
| NEWA's European corn borer model | The standard where sources conflict (D95) | Not yet compared |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (550, 740, 900) and (1660, 1950, 2190), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside; where two windows touch, the later one's value.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Against Enviroweather** (thresholds compared, not run): MSU's first flight starts 100 degree days earlier (450) and ends 50 later (950); its second runs 1,450–1,950 against 1,660–2,190; it adds a third flight that it expects in few years.
- **Two flights**, no third, as VDIFN's text has two generations in most of Wisconsin.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generations, (550, 740, 900) and (1660, 1950, 2190), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generations are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.
- The weather itself: VDIFN read its degree days from the old AgWeather API's daily grid; v2 reads its own archive. At Waunakee, January 1 to October 31, 2026, v2's single-sine 50/86 °F total was 3,184 against the old API's 3,203 (−0.6 %; `docs/validation/legacy/v1-dd-table.md`).

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- **A slip in the page's text:** the summary in `european_corn_borer.md` (VDIFN's text) says the first flight starts at 329, peaks at 472 and ends at 636 degree days, which are corn rootworm's numbers; the model's first flight is 550, 740 and 900. Fix the text when the page is rewritten (part I2).
- The source of 550/740/900 and 1660/1950/2190 isn't identified.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** DATCP's weekly Pest Bulletin black light trap counts of European corn borer moths, 2020–2026 (both flights, many sites a year), against the flights; then NEWA's European corn borer model on the same weather.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
