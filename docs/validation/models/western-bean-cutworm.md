# Western bean cutworm (`western-bean-cutworm`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/western_bean_cutworm.py`, VDIFN's generation table run by the insect engine (`agmodels.phenology`; PLAN.md Phase 3 D, step 3); its page: `western_bean_cutworm.md` beside it (VDIFN's text). The insect review that will replace or confirm the numbers is `docs/models-plan.md` part H, with `docs/insect-models.md` as its work list.

**In short:** ported from VDIFN unchanged. Given the same degree days its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read. That shows a faithful port, not a right answer: the timing hasn't been checked against its source or against field data in Wisconsin. It runs on a different degree-day method from its source's (below).

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Base 50 °F, no upper, from May 1; one span (1320, 1420, 1535); the text; a link to UW Vegetable Entomology's black cutworm page | Everything |
| The VDIFN Models spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`) and the USPest.org model it links, as summarized in `docs/insect-models.md` | USPest's `wbc` model (Nebraska IPM): simple average, 50 °F; UNL CropWatch 2016; UW publication A3856 | Nothing yet: the method differs (below) |
| Hanson et al. 2015 (`tmp/references/insects/`) | Degree-day prediction models of the moth's flight, compared by their concordance with observed flight | Read 2026-11-19: Ahmad's (1979) 25, 50 and 75 % flight at 733, 790 and 853 °C·d (1,319, 1,422 and 1,535 °F·d), from the daily average with no upper threshold; on 36 Nebraska site-years (1981–2009) Ahmad's model ran 3 days late on average (7 early to 12 late), and a model from March 1 did better. The table's 1,319 to 1,535 are these points |

## Choices and differences

- **Degree days:** single sine (Baskerville–Emin), 50 °F, no upper threshold, from May 1: VDIFN's thresholds, computed as the old AgWeather API did.
- **Risk:** VDIFN's: one generation, (1320, 1420, 1535) degree days (°F) as (start, peak, end); severity rises along a half sine from start to peak and falls from peak to end, rounded up to the 0–4 levels, and is 0 outside. VDIFN's text: 25% of adult moths have emerged about 1,320 degree days (°F) after May 1, emergence peaks about 1,420 and ends about 1,535.
- **Freezes:** after day 250 (early September), severity is lowered by the number of days in the last 14 at or below −2 °C (28.4 °F), the Crop Risk Tool's rule, used for every insect still on a legacy table; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D, step 3).
- **Method:** single sine, as VDIFN computed every insect; USPest's (Nebraska's) model uses the simple average (`docs/insect-models.md`). By D37 a model should run on its source's method; the sine counts more on cool days (70–100 °F·d more by May from January 1 at Eau Claire in 2025, `docs/insect-models.md`), so the events likely come earlier than the source's.
- **The ramp:** severity starts at 25% emergence (1,320), so the first quarter of the flight shows as no risk, and it is 0 after 1,535.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Numbers:** the thresholds, biofix and table are VDIFN's `db/seeds.rb` entry, read against it again for this report: identical. No test compares them with the seeds file.
- **Severity:** VDIFN's own Ruby code (`Insect#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_insect_severity_sweep.csv`) on four generation tables, every 5 degree days from 0 to 3,500 (701 totals each, 2,804 in all), without freezes: our severity is identical at every total (`test_insects.py::test_vdifn_generations_match_its_severity`). The four tables aren't this insect's; its own (1320, 1420, 1535) is checked against a Python copy of VDIFN's sine ramp at every 0.01 degree day from start to end and at 2,000 random totals: identical (`test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`).
- **Degree days:** the old AgWeather API's calculator (`../ag-weather`, VDIFN's source of degree days), single sine at 50 °F, on 231 pairs of daily minimum and maximum around the thresholds: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`, fixture from `fixtures/make_degree_days_legacy.rb`).
- **Not compared:** the freeze reduction (the rules differ, above), and VDIFN's results on real weather. VDIFN read the old API's grid and v2 reads its own archive; for scale, v2's single-sine 50/86 °F total from January 1 to October 31, 2026 at Waunakee was 0.6% below the old API's (`docs/validation/legacy/v1-dd-table.md`).

### Against its sources and the field

None yet: no test reproduces a published number for this insect, and it hasn't been compared with trap counts or scouting records.

## Limits and open questions

- It runs on a different degree-day method from its source's (above).
- No check against Wisconsin field data.
- The 0–4 levels are VDIFN's display rule, not an estimate of numbers: 4 means near the table's peak, and every generation counts alike (D37).
- **Cheapest independent comparison:** DATCP's weekly Pest Bulletin black light trap counts of western bean cutworm moths, 2020–2026: the dates of 25% and peak cumulative catch against the model's 1,320 and 1,420 (public data, a script like codling moth's trap check).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb  # rebuilds the old API's degree days; needs ../ag-weather
```
