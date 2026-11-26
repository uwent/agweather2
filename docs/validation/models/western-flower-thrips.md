# Western flower thrips (`western-flower-thrips`): validation

**Retired 2026-11-21 (version 0.2; Ben, part H of `docs/plans/models.md`):** the thrips doesn't overwinter outdoors in Wisconsin, so degree days from January 1 don't time it in the field, and its source (USPest's model) is still under development. The report below describes version 0.1 as it was.

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/western_flower_thrips.py`, VDIFN's generation table run by the insect engine (`agmodels.phenology`; Phase 3 D, step 3); its page: `western_flower_thrips.md` beside it (VDIFN's text). The insect review that will replace or confirm the numbers is `docs/plans/models.md` part H, with `docs/insect-models.md` as its work list.

**In short:** ported from VDIFN unchanged. Given the same degree days its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read. That shows a faithful port, not a right answer: the timing hasn't been checked against its source or against field data in Wisconsin. Which species the numbers are for is unclear (below); USPest's model was marked under development, and no paper is identified.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's `db/seeds.rb` (`../ag-vdifn`) | Base 45 °F, no upper, January 1; four generations (340, 675, 1010), (1010, 1350, 1685), (1685, 2025, 2360), (2360, 2700, 3375); the text; a link to UW Vegetable Entomology's onion thrips page | Everything |
| The VDIFN Models spreadsheet (`tmp/references/insects/VDIFN Models v20210407.xlsx`) and the USPest.org model it links, as summarized in `docs/insect-models.md` | USPest's `wft` model (an Oregon State analysis, marked "under development"): single sine 45/104 °F | Nothing yet |

## Choices and differences

- **Degree days:** single sine (Baskerville–Emin), 45 °F, no upper threshold, from January 1: VDIFN's thresholds, computed as the old AgWeather API did.
- **Risk:** VDIFN's: 4 generations, (340, 675, 1010), (1010, 1350, 1685), (1685, 2025, 2360), (2360, 2700, 3375) degree days (°F) as (start, peak, end); severity rises along a half sine from start to peak and falls from peak to end, rounded up to the 0–4 levels, and is 0 outside. VDIFN's text: thrips have several overlapping generations a year in Wisconsin, peaking about 675, 1,350, 2,025 and 2,700 degree days (°F).
- **Freezes:** after day 250 (early September), severity is lowered by the number of days in the last 14 at or below −2 °C (28.4 °F), the Crop Risk Tool's rule, used for every insect still on a legacy table; VDIFN subtracted freezing days only from November (Phase 3 D, step 3).
- **Generations that touch:** each ends where the next starts (1,010, 1,685 and 2,360), so severity falls to Low between peaks and rises again; a later generation overrides where they meet, as in VDIFN.
- **Which thrips:** VDIFN's description (thrips scarring cabbage heads) and its link are about onion thrips, while the name and the spreadsheet's USPest model are western flower thrips'.
- **Season (D128):** a migrant, so its season opens on the calendar, April 15, everywhere, and ends after October 31.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Numbers:** the thresholds, biofix and table are VDIFN's `db/seeds.rb` entry, read against it again for this report: identical. No test compares them with the seeds file.
- **Severity:** VDIFN's own Ruby code (`Insect#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_insect_severity_sweep.csv`) on four generation tables, every 5 degree days from 0 to 3,500 (701 totals each, 2,804 in all), without freezes: our severity is identical at every total (`test_insects.py::test_vdifn_generations_match_its_severity`). One of the four tables is this insect's own four generations.
- **Degree days:** the old AgWeather API's calculator (`../ag-weather`, VDIFN's source of degree days), single sine at 45 °F, on 231 pairs of daily minimum and maximum around the thresholds: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`, fixture from `fixtures/make_degree_days_legacy.rb`).
- **Not compared:** the freeze reduction (the rules differ, above), and VDIFN's results on real weather. VDIFN read the old API's grid and v2 reads its own archive; for scale, v2's single-sine 50/86 °F total from January 1 to October 31, 2026 at Waunakee was 0.6% below the old API's (`docs/validation/legacy/v1-dd-table.md`).

### Against its sources and the field

None yet: no test reproduces a published number for this insect, and it hasn't been compared with trap counts or scouting records.

## Limits and open questions

- Which species the numbers are for is unclear (above); USPest's model was marked under development, and no paper is identified.
- The dips to Low between generations are an artifact of the table; real generations overlap (VDIFN's own text says so).
- No check against Wisconsin field data.
- The 0–4 levels are VDIFN's display rule, not an estimate of numbers: 4 means near the table's peak, and every generation counts alike (D37).
- **Cheapest independent comparison:** Settle the species and read USPest's source against the table (reading, no data); then thrips counts from Wisconsin vegetable or greenhouse scouting, none known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb  # rebuilds the old API's degree days; needs ../ag-weather
```
