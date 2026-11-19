# Mint root borer (`mint-root-borer`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/mint_root_borer.py`, VDIFN's generation table run by the insect engine (`agmodels.phenology`; PLAN.md Phase 3 D, step 3); its page: `mint_root_borer.md` beside it (VDIFN's text). The insect review that will replace or confirm the numbers is `docs/models-plan.md` part H, with `docs/insect-models.md` as its work list.

**In short:** ported from VDIFN unchanged. Given the same degree days its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read. That shows a faithful port, not a right answer: the timing hasn't been checked against its source or against field data in Wisconsin. Its numbers and April 1 start are the events of Oregon State's model on USPest (`mrb`, Berry et al.; partly validated), whose underlying paper isn't identified; the model was developed in the Pacific Northwest's mint, not Wisconsin's.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Base 50 °F, no upper, from April 1; one generation (430, 1280, 2150); the text; a link to Wikipedia's page on the genus | Everything |
| The VDIFN Models spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`) and the USPest.org model it links, as summarized in `docs/insect-models.md` | USPest's `mrb` model from Berry et al. (Oregon State): single sine 50 °F | Nothing yet: the paper isn't identified |
| Tollerup, Marcum, Wilson and Godfrey 2013 (open access) | The biology of mint root borer on California peppermint | Nothing yet; not read against the table |

## Choices and differences

- **Degree days:** single sine (Baskerville–Emin), 50 °F, no upper threshold, from April 1: VDIFN's thresholds, computed as the old AgWeather API did.
- **Risk:** VDIFN's: one generation, (430, 1280, 2150) degree days (°F) as (start, peak, end); severity rises along a half sine from start to peak and falls from peak to end, rounded up to the 0–4 levels, and is 0 outside. VDIFN's text: the first moth catch comes about 430 degree days (°F) after April 1, egg hatch peaks about 1,280, and risk ends about 2,150, when the larvae have formed their overwintering chambers (hibernacula). (USPest's event at 2,150 is half the larvae in their chambers, not all; the model page's text overstates it.)
- **Freezes:** after day 250 (early September), severity is lowered by the number of days in the last 14 at or below −2 °C (28.4 °F), the Crop Risk Tool's rule, used for every insect still on a legacy table; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D, step 3).
- **Biofix:** April 1, as in VDIFN and in USPest's `mrb` model (https://uspest.org/cgi-bin/ddmodel2.pl?spp=mrb), which counts from April 1 at 50 °F: first moths at 430 degree days, egg hatch peaking at 1,280, and half the larvae in their winter chambers (hibernacula) at 2,150. All three of the model's numbers are USPest's events (checked 2026-11-19 for the topic page).

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Numbers:** the thresholds, biofix and table are VDIFN's `db/seeds.rb` entry, read against it again for this report: identical. No test compares them with the seeds file.
- **Severity:** VDIFN's own Ruby code (`Insect#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_insect_severity_sweep.csv`) on four generation tables, every 5 degree days from 0 to 3,500 (701 totals each, 2,804 in all), without freezes: our severity is identical at every total (`test_insects.py::test_vdifn_generations_match_its_severity`). The four tables aren't this insect's; its own (430, 1280, 2150) is checked against a Python copy of VDIFN's sine ramp at every 0.01 degree day from start to end and at 2,000 random totals: identical (`test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`).
- **Degree days:** the old AgWeather API's calculator (`../ag-weather`, VDIFN's source of degree days), single sine at 50 °F, on 231 pairs of daily minimum and maximum around the thresholds: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`, fixture from `fixtures/make_degree_days_legacy.rb`).
- **Not compared:** the freeze reduction (the rules differ, above), and VDIFN's results on real weather. VDIFN read the old API's grid and v2 reads its own archive; for scale, v2's single-sine 50/86 °F total from January 1 to October 31, 2026 at Waunakee was 0.6% below the old API's (`docs/validation/legacy/v1-dd-table.md`).

### Against its sources and the field

None yet: no test reproduces a published number for this insect, and it hasn't been compared with trap counts or scouting records.

## Limits and open questions

- Its numbers and April 1 start are the events of Oregon State's model on USPest (`mrb`, Berry et al.; partly validated), whose underlying paper isn't identified; the model was developed in the Pacific Northwest's mint, not Wisconsin's.
- No check against Wisconsin field data.
- The 0–4 levels are VDIFN's display rule, not an estimate of numbers: 4 means near the table's peak, and every generation counts alike (D37).
- **Cheapest independent comparison:** Read Tollerup et al. 2013 (open access) and USPest's source for their degree-day events and biofix, and compare them with the table (reading, no data). No Wisconsin trap records of mint root borer are known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb  # rebuilds the old API's degree days; needs ../ag-weather
```
