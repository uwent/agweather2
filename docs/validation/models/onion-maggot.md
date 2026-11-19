# Onion maggot (`onion-maggot`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/onion_maggot.py`, VDIFN's generation table run by the insect engine (`agmodels.phenology`; PLAN.md Phase 3 D, step 3); its page: `onion_maggot.md` beside it (VDIFN's text). The insect review that will replace or confirm the numbers is `docs/models-plan.md` part H, with `docs/insect-models.md` as its work list.

**In short:** ported from VDIFN unchanged. Given the same degree days its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read. That shows a faithful port, not a right answer: the timing hasn't been checked against its source or against field data in Wisconsin. The table's source isn't identified ("XHT1087"); Eckenrode et al. 1975 and Liu et al. 1982 are in hand but not read against it.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Single sine 39.2/86 °F, January 1; two generations (510, 680, 850) and (1460, 1950, 2435); the text; a link to UW Vegetable Entomology's onion maggot page | Everything |
| The VDIFN Models spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`) and the USPest.org model it links, as summarized in `docs/insect-models.md` | The spreadsheet gives 40/86 °F and cites "XHT1087" (not identified) | Nothing: the base differs by 0.8 °F |
| Eckenrode, Vea and Stone 1975; Liu, McEwen and Ritcey 1982 (both in `tmp/references/insects/`) | Onion maggot flight against thermal units in the field; Liu et al. use single sine at 4.4 °C (39.9 °F) | Nothing yet; not read against the table |
| NEWA's onion maggot model | A model of the same pest, the standard where sources conflict (D95) | Not compared yet |

## Choices and differences

- **Degree days:** single sine (Baskerville–Emin), 39.2 to 86 °F, from January 1: VDIFN's thresholds, computed as the old AgWeather API did.
- **Risk:** VDIFN's: 2 generations, (510, 680, 850), (1460, 1950, 2435) degree days (°F) as (start, peak, end); severity rises along a half sine from start to peak and falls from peak to end, rounded up to the 0–4 levels, and is 0 outside. VDIFN's text: first-generation adult flight peaks about 680 degree days (°F) and the second about 1,950.
- **Freezes:** after day 250 (early September), severity is lowered by the number of days in the last 14 at or below −2 °C (28.4 °F), the Crop Risk Tool's rule, used for every insect still on a legacy table; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D, step 3).
- **Base:** 39.2 °F (4 °C), as in VDIFN; the spreadsheet says 40 °F and Liu et al. 1982 39.9 °F (`docs/insect-models.md`). The difference is under a degree.
- **NEWA:** NEWA runs an onion maggot model, which D95 makes the standard for this pest; it hasn't been compared yet.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Numbers:** the thresholds, biofix and table are VDIFN's `db/seeds.rb` entry, read against it again for this report: identical. No test compares them with the seeds file.
- **Severity:** VDIFN's own Ruby code (`Insect#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_insect_severity_sweep.csv`) on four generation tables, every 5 degree days from 0 to 3,500 (701 totals each, 2,804 in all), without freezes: our severity is identical at every total (`test_insects.py::test_vdifn_generations_match_its_severity`). The four tables aren't this insect's; its own (510, 680, 850), (1460, 1950, 2435) is checked against a Python copy of VDIFN's sine ramp at every 0.01 degree day from start to end and at 2,000 random totals: identical (`test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`).
- **Degree days:** the old AgWeather API's calculator (`../ag-weather`, VDIFN's source of degree days), single sine at 39.2/86 °F, on 231 pairs of daily minimum and maximum around the thresholds: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`, fixture from `fixtures/make_degree_days_legacy.rb`).
- **Not compared:** the freeze reduction (the rules differ, above), and VDIFN's results on real weather. VDIFN read the old API's grid and v2 reads its own archive; for scale, v2's single-sine 50/86 °F total from January 1 to October 31, 2026 at Waunakee was 0.6% below the old API's (`docs/validation/legacy/v1-dd-table.md`).

### Against its sources and the field

None yet: no test reproduces a published number for this insect, and it hasn't been compared with trap counts or scouting records.

## Limits and open questions

- The table's source isn't identified ("XHT1087"); Eckenrode et al. 1975 and Liu et al. 1982 are in hand but not read against it.
- No check against Wisconsin field data.
- The 0–4 levels are VDIFN's display rule, not an estimate of numbers: 4 means near the table's peak, and every generation counts alike (D37).
- **Cheapest independent comparison:** NEWA's onion maggot model recomputed from its published rules on the same weather at Wisconsin stations, as done for codling moth (`scripts/newa_reference.py` would gain its rules); per D95 this is also the comparison that decides the model's method.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb  # rebuilds the old API's degree days; needs ../ag-weather
```
