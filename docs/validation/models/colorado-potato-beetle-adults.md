# Colorado potato beetle, adults (`colorado-potato-beetle-adults`): validation

**Retired 2026-11-18 (version 0.2):** `colorado-potato-beetle` now gives adults as one of its outputs, from the analysis's own fits on degree days 52/86 °F; see [its report](colorado-potato-beetle.md). What follows is the report as written for version 0.1.

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/colorado_potato_beetle_adults.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `colorado_potato_beetle_adults.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's adult abundance curve, fitted by UW–Madison's Vegetable Entomology lab to 10 years of scouting in Wisconsin's Central Sands (Bradford and Groves, unpublished), reproduced exactly, including the day the two generations meet. The fit hasn't been published or checked on years it wasn't fitted to.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `cpbad`) | Thresholds 50/86 °F, biofix January 1, two windows (275, 690, 1090) and (1090, 1690, 2500); text: derived from 10 years of Central Sands scouting; first colonization around 275, first-generation adults peak around 690, a low at 1,090, second-generation adults peak around 1,695 and decline to about 2,500 | All of it, unchanged |
| Bradford and Groves, Vegetable Entomology Lab, UW–Madison, unpublished analysis (cited in the spec) | The fit behind VDIFN's numbers | Cited; the analysis itself isn't in the repository |
| Enviroweather (MSU), Colorado potato beetle (`docs/enviroweather-models.md`) | Single sine 52 °F, no upper, from March 1: first-generation adults from 372, peak 607; second-generation adult peak 1,376, flight ends 1,780; no source cited | Compared only: a different base, start and population, so its numbers aren't directly comparable |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (275, 690, 1090) and (1090, 1690, 2500), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside; where two windows touch, the later one's value.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Text and curve:** the description puts the second-generation peak at 1,695; the curve peaks at 1,690, as VDIFN's did. A slip of 5 degree days in the text.
- **Siblings:** `colorado-potato-beetle-larvae` is the same lab's larval curve, and `colorado-potato-beetle` the Crop Risk Tool's stage table (the same lab's later work, with its own report). The three agree in shape, not in numbers: the Crop Risk Tool's table peaks first-generation adults at 600 and second-generation adults at 1,470 (`docs/enviroweather-models.md`).

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generations, (275, 690, 1090) and (1090, 1690, 2500), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. One of the four (`touching`) has two generations that share an end and a start, as this model's do at 1,090, so the rule for that day (the later generation's ramp, which starts at 0) is checked.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generations are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.
- The weather itself: VDIFN read its degree days from the old AgWeather API's daily grid; v2 reads its own archive. At Waunakee, January 1 to October 31, 2026, v2's single-sine 50/86 °F total was 3,184 against the old API's 3,203 (−0.6 %; `docs/validation/legacy/v1-dd-table.md`).

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The fit is unpublished: its data, method and goodness of fit aren't in the repository. Ben is an author and can supply them.
- Fitted in the Central Sands; elsewhere in Wisconsin, and outside it, the timing is untested.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** UW Vegetable Entomology's Central Sands scouting counts of adults for years after the fit, against the curve: held-out years of the lab's own data.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
