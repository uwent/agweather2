# Corn rootworm (`corn-rootworm`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/corn_rootworm.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `corn_rootworm.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's larval feeding window, 329 to 636 degree days (base 52 °F) from January 1, reproduced exactly. Which rootworm species and which temperature (air or soil) its numbers were made for isn't recorded, and it hasn't been compared with any observations.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `corn-rootworm`) | Threshold 52 °F, no upper, biofix January 1, one window (329, 472, 636); text: first larvae around 329 with light feeding, a peak around 472 with heavy feeding, the larval stage over by 636 | All of it, unchanged |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | UC IPM's northern corn rootworm page (events with 90 % ranges) | Nothing yet: not read |
| Jackson and Elliott 1988 ([doi:10.1093/ee/17.2.166](https://doi.org/10.1093/ee/17.2.166)) | Laboratory development of western corn rootworm (a candidate source) | Nothing yet: not in hand |

## Choices and differences

- **Degree days:** single sine, 52 °F with no upper threshold, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (329, 472, 636), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Temperature:** air temperature, as for every VDIFN insect. The eggs and larvae live in the soil; whether the source's numbers were counted from air or soil temperature isn't recorded (the review's step 2 asks this).
- **Species:** VDIFN's text covers northern and western corn rootworm together (their larvae can't be told apart in the field) and says larvae feed on crown roots from June to August; one window serves both.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generation, (329, 472, 636), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 52 °F (no upper) match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generation are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The source, species and temperature basis are unknown (above).
- Only larval feeding is modelled; adult emergence and egg laying aren't.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** Read UC IPM's page and Jackson and Elliott 1988 for the source's events and temperature basis (a published check); no Wisconsin observations of larval hatch are known.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
