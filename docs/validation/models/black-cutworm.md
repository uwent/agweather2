# Black cutworm (`black-cutworm`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/black_cutworm.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `black_cutworm.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's leaf-cutting window, 300 to 1,000 degree days (50/86 °F) after May 15, reproduced exactly. Its source isn't identified with certainty, May 15 stands in for the moth flight the sources time it from, and it hasn't been compared with Wisconsin's trap counts or cutting reports.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `black-cutworm`) | Thresholds 50/86 °F, biofix May 15, one window (300, 700, 1000); text: egg hatch around 180, leaf cutting and larval development from 300 through 1,000 | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | USPest's black cutworm model (`bcw`, UC Davis with MSU's events): single sine 50/86 °F with the biofix at peak pheromone-trap captures | Nothing yet |
| Luckmann et al. 1976 ([doi:10.1093/jee/69.3.386](https://doi.org/10.1093/jee/69.3.386)); Story et al. 1984 ([doi:10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)); Kaster and Showers 1984 ([doi:10.1093/ee/13.2.384](https://doi.org/10.1093/ee/13.2.384)) | Per the review notes: a threshold of 10.4 °C (50.7 °F); Story et al. found field larvae "far ahead" of lab-based predictions | Nothing yet (the first two are in `tmp/references/insects/`, not read for this report) |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, from May 15, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (300, 700, 1000), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Biofix:** a fixed May 15, VDIFN's default. The sources count from a significant moth capture, so May 15 is a stand-in; a grower can set their own date at a point.
- **Risk:** the larval cutting window only; egg hatch (about 180 by VDIFN's text) isn't modelled.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generation, (300, 700, 1000), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 50/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generation are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.
- The weather itself: VDIFN read its degree days from the old AgWeather API's daily grid; v2 reads its own archive. At Waunakee, January 1 to October 31, 2026, v2's single-sine 50/86 °F total was 3,184 against the old API's 3,203 (−0.6 %; `docs/validation/legacy/v1-dd-table.md`).

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The capture the sources count from comes on a different date each year; a fixed date can't follow it.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** DATCP's weekly Pest Bulletin black light trap counts of black cutworm moths, 2020–2026: the date of each site's first significant capture against May 15, and the bulletin's reports of cutting against the window counted from that capture.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
