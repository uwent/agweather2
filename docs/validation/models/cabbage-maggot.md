# Cabbage maggot (`cabbage-maggot`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/cabbage_maggot.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `cabbage_maggot.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** VDIFN's two generations (adult flight through egg laying), 42.8/86 °F degree days from January 1, reproduced exactly. Against the Wisconsin field study the numbers most likely come from (Eckenrode and Chapman 1972), spring flies start within the range it found, but the second generation comes about 345 degree days later than its generation time puts it. NEWA runs a cabbage maggot model, which is the standard where sources conflict (D95), and hasn't been compared yet.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `cabbage-maggot`) | Thresholds 42.8/86 °F, biofix January 1, two windows (360, 600, 1521) and (1881, 2121, 3042); text: adults from 360, peak 600, egg laying 750–1,500 peaking near 1,050; second generation from 1,880, peak 2,120, egg laying 2,270–3,040; two generations typical | All of it, unchanged |
| Eckenrode and Chapman 1972 ([doi:10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151); in `tmp/references/insects/`) | Trap catches at Kenosha and Arlington, Wisconsin: spring flies emerged at 290–365 air thermal units (max-min, 43 °F, Arnold's 1960 correction) over five years; later generations a mean 1,176 apart (12 field life cycles; 1,058 at Kenosha in 1965, 1,261 at Arlington in 1966) | A check (below) |
| Eckenrode and Chapman 1971 ([doi:10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)) | Laboratory development rates behind the 43 °F threshold | Nothing yet (in `tmp/references/insects/`, not read for this report) |
| VDIFN's model spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`), as summarized in `docs/insect-models.md` | USPest's model (`cm1`): single sine 39.7/86 °F | Nothing yet |
| Enviroweather (MSU), cabbage maggot (`docs/enviroweather-models.md`) | Single sine 43 °F, no upper, from March 1: emergence 300–564, spring peak flight 565–716 (high risk), summer peak flights 1,476–1,728 and 2,652–2,887 (low risk); no source cited | Compared only (below) |
| NEWA's cabbage maggot model | The standard where sources conflict (D95) | Not yet compared |

## Choices and differences

- **Degree days:** single sine, 42.8/86 °F, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (360, 600, 1521) and (1881, 2121, 3042), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside; where two windows touch, the later one's value.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **One window per generation** spans adult flight and egg laying (360 to 1,521), so severity peaks with the flight (600) rather than with egg laying (about 1,050 by VDIFN's text), when the maggots that do the damage hatch.
- **Against Enviroweather** (thresholds compared, not run): MSU starts on March 1 with no upper threshold and peaks the spring flight at 565–716, near VDIFN's 600; its two summer flights (peaks from 1,476 and 2,652) bracket VDIFN's second generation (peak 2,121). MSU labels the spring flight high risk and the summer ones low, which VDIFN's equal ramps don't.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generations, (360, 600, 1521) and (1881, 2121, 3042), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 42.8/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generations are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

### Against Eckenrode and Chapman 1972

Read from the paper for this report (its abstract and results), not a test. Their thermal units are air degree days above 43 °F from daily maximum and minimum with Arnold's correction, close to but not the same as v2's single sine at 42.8/86 °F, so these are approximate comparisons.

- Spring flies: the model's first generation starts at 360 degree days; Eckenrode and Chapman's spring emergence came at 290 to 365 thermal units over five years in Wisconsin.
- Generation time: the model's second generation starts 1,521 degree days after the first (1,881 − 360); the paper's mean generation time in the field was 1,176 (12 life cycles; 1,058 to 1,261 by site and year). By this source the model's second flight is about 345 degree days late.

## Limits and open questions

- The second generation's timing disagrees with the Wisconsin field study (above); the review (part H) should take its generation time or NEWA's model (D95).
- Eckenrode and Chapman trapped adults of three generations in a season (spring, F1 and F2), and MSU shows two summer flights after the spring one; the model has two generations.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** NEWA's cabbage maggot model on the same weather, recomputed from its published rules on Wisconsin station hours as codling moth's comparison was (`scripts/newa_reference.py`'s approach); no observations needed.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
