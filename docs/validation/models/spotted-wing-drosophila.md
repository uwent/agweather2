# Spotted wing drosophila (`spotted-wing-drosophila`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/spotted_wing_drosophila.py`, VDIFN's generation table run by the insect engine (`agmodels.phenology`; PLAN.md Phase 3 D, step 3); its page: `spotted_wing_drosophila.md` beside it (VDIFN's text). The insect review that will replace or confirm the numbers is `docs/models-plan.md` part H, with `docs/insect-models.md` as its work list.

**In short:** ported from VDIFN unchanged. Given the same degree days its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read. That shows a faithful port, not a right answer: the timing hasn't been checked against its source or against field data in Wisconsin. Kamiyama et al. 2020, VDIFN's own link and the UW group's work, isn't in the model's citations and hasn't been read against the table; it was fitted in tart cherry orchards, while the model's crops are blackberry, cherry and raspberry.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Single sine 45/86 °F, January 1; one span (1276, 3180, 4000); the text; a link to Kamiyama et al. 2020 | Everything |
| Kamiyama, Bradford, Groves and Guédot 2020 (PLOS ONE, open access; UW–Madison) | Degree-day models of the fly's seasonal phenology in Midwest tart cherry orchards | Nothing checked: not read against the table, and not in the model's citations |
| MSU Enviroweather's SWD model (`docs/enviroweather-models.md`) | Tart cherry fruit stages from bloom (base 39.2 °F) and insecticide wash-off | Nothing: a different kind of model (host susceptibility, not the fly's numbers) |

## Choices and differences

- **Degree days:** single sine (Baskerville–Emin), 45 to 86 °F, from January 1: VDIFN's thresholds, computed as the old AgWeather API did.
- **Risk:** VDIFN's: one generation, (1276, 3180, 4000) degree days (°F) as (start, peak, end); severity rises along a half sine from start to peak and falls from peak to end, rounded up to the 0–4 levels, and is 0 outside. VDIFN's text: overwintered adults start laying eggs in mid to late June, about 1,276 degree days (°F), complete a generation every 8 to 12 days, and peak about 3,100.
- **Freezes:** after day 250 (early September), severity is lowered by the number of days in the last 14 at or below −2 °C (28.4 °F), the Crop Risk Tool's rule, used for every insect still on a legacy table; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D, step 3).
- **One span for many generations:** VDIFN treats the whole season as one ramp from egg laying's start (1,276) to a peak at 3,180, so risk keeps rising through the summer, as populations do.
- **Peak:** the table's 3,180 against the text's "about 3,100"; we keep the table.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Numbers:** the thresholds, biofix and table are VDIFN's `db/seeds.rb` entry, read against it again for this report: identical. No test compares them with the seeds file.
- **Severity:** VDIFN's own Ruby code (`Insect#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_insect_severity_sweep.csv`) on four generation tables, every 5 degree days from 0 to 3,500 (701 totals each, 2,804 in all), without freezes: our severity is identical at every total (`test_insects.py::test_vdifn_generations_match_its_severity`). The four tables aren't this insect's; its own (1276, 3180, 4000) is checked against a Python copy of VDIFN's sine ramp at every 0.01 degree day from start to end and at 2,000 random totals: identical (`test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`).
- **Degree days:** the old AgWeather API's calculator (`../ag-weather`, VDIFN's source of degree days), single sine at 45/86 °F, on 231 pairs of daily minimum and maximum around the thresholds: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`, fixture from `fixtures/make_degree_days_legacy.rb`).
- **Not compared:** the freeze reduction (the rules differ, above), and VDIFN's results on real weather. VDIFN read the old API's grid and v2 reads its own archive; for scale, v2's single-sine 50/86 °F total from January 1 to October 31, 2026 at Waunakee was 0.6% below the old API's (`docs/validation/legacy/v1-dd-table.md`).

### Against its sources and the field

None yet: no test reproduces a published number for this insect, and it hasn't been compared with trap counts or scouting records.

## Limits and open questions

- Kamiyama et al. 2020, VDIFN's own link and the UW group's work, isn't in the model's citations and hasn't been read against the table; it was fitted in tart cherry orchards, while the model's crops are blackberry, cherry and raspberry.
- No check against Wisconsin field data.
- The 0–4 levels are VDIFN's display rule, not an estimate of numbers: 4 means near the table's peak, and every generation counts alike (D37).
- **Cheapest independent comparison:** Read Kamiyama et al. 2020 (open access): its trap captures and degree-day events, at its thresholds, against the table (reading, no data); its orchards' trap captures would then be the field check.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb  # rebuilds the old API's degree days; needs ../ag-weather
```
