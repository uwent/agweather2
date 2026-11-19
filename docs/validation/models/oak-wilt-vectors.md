# Oak wilt vector flight (`oak-wilt-vectors`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/oak_wilt.py`, ported from VDIFN's `app/models/insects/oak_wilt.rb`; its page: `oak_wilt.md` beside it.

**In short:** ported from VDIFN. Given the same degree days and date, its risk matches VDIFN's exactly, and its degree days match the old AgWeather API's that VDIFN read; the one intended difference is the July dates in leap years. The flight bounds are Jagemann et al. 2018's percentiles of *C. truncatus*'s flight (Table 4, °C·d × 1.8: 231, 283, 388, 913, 1792, 2172), read against the paper on 2026-11-19; the old AgWeather website's 368 at 25% flight was a slip.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Jagemann, Juzwik, Tobin and Raffa 2018 | Seasonal flight of the two main sap beetle vectors in Wisconsin (*Colopterus truncatus*, then *Carpophilus sayi*) and degree-day models of it | Through VDIFN: base 41 °F from January 1, and the flight percentiles behind the bounds: Table 4's degree days for *C. truncatus* (base 5 °C) × 1.8 give 231, 283, 388, 913, 1792 and 2172 exactly; 180 is the paper's ~100 °C·d before first flight. *C. sayi* (611 and 4,218 °F·d at its 5% and 95%) isn't followed. The paper counted with Allen's modified sine, the model a single sine with no upper threshold |
| VDIFN's `app/models/insects/oak_wilt.rb` and `db/seeds.rb` (`../ag-vdifn`) | Levels by degree days: 0 below 180, 1 to 231 (under 5% of *C. truncatus* flying), 2 to 283 (5–10%), 3 to 388 (10–25%), 4 to 913 (25–75%), 3 to 1792 (75–90%), 2 to 2172 (90–95%), 1 after; from July 15 two levels lower and at most 1, from July 22 one lower again; the text | Everything |
| The old AgWeather website's oak wilt page (`../soils-ag-wx`, `app/models/oak_wilt.rb`) | Base 41 °F from January 1 through the old API; the restricted period begins at 231; bounds 231 (5% flight), 368 (25%), 638 (50%), 913 (75%), 2172 (95%); low after July 15 | Compared only, below |

## Choices and differences

- **Degree days:** single sine, base 41 °F, no upper threshold, from January 1, as the old API computed VDIFN's `dd_41`. Jagemann et al.'s own method hasn't been checked (`docs/insect-models.md`: "method only").
- **July reductions in leap years:** VDIFN compared the day of the year with 196 and 203, which fall on July 14 and 21 in a leap year; ours fall on July 15 and 22 every year (0.2, 2026-11-01; found by the test review after Phase 4, PLAN.md). Version 0.2 also made the reductions apply to runs, not only the explorer.
- **No freeze reduction:** VDIFN's subtracted freezing days from November, when risk is already Very low after the July reductions, so it never changed a level; ours has none.
- **Against the old website:** the two old tools agree on 231 (5%), 913 (75%) and 2172 (95%), but put 25% flight at 368 (website) and 388 (VDIFN). The paper settles it: 388 (its Table 4: 215.8 °C·d × 1.8); the website's 368 was a slip.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces, so this compares with a reference, not with the truth (D54). In `packages/agmodels/tests/`, run in CI:

- **Risk:** VDIFN's own Ruby code (`OakWilt#total_to_severity`, loaded over a stub by `fixtures/make_vdifn_fixtures.rb` into `vdifn_oak_wilt_sweep.csv`) every 10 degree days from 0 to 2,500 on seven days of a common year (days 120, 180, 195, 196, 202, 203 and 250: before and after July 15 and July 22), 1,757 cases: our risk is identical in every one (`test_insects.py::test_oak_wilt_matches_vdifn`).
- **Degree days:** the old AgWeather API's calculator, single sine from 41 °F, on 231 pairs of daily minimum and maximum around the threshold: within 0.000001 °F·d (`test_degree_days.py::test_matches_the_old_api`).
- **Dates:** in 2024 and 2025, a cool year's risk is Very high on July 14, Low on July 15 and 21, and Very low on July 22 (`test_oak_wilts_july_reductions_apply_to_runs_and_follow_the_calendar_in_leap_years`), so leap years follow the calendar.
- **Not compared:** VDIFN's results on real weather (VDIFN read the old API's grid, v2 its own archive).

### Against its sources and the field

None yet: no test reproduces Jagemann et al.'s numbers, and the model hasn't been compared with trap catches.

## Limits and open questions

- The bounds follow *C. truncatus* only; Jagemann et al. found 27% (south) to 64% (north) of *C. sayi* flying after July 15 and suggested revisiting the July 15 end. The paper's degree days are Allen's modified sine; ours single sine with no upper threshold (not compared).
- The July 15 and July 22 steps are VDIFN's rule, not a fit to data; July 15 is where the old website's page ends Wisconsin's restricted oak harvesting period, in both its north and south zones.
- Valid only where the oak wilt fungus and its vectors occur, and developed in Wisconsin.
- **Cheapest independent comparison:** Jagemann et al. 2018's trap catches by site and year, on the archive's weather (the bounds are already checked against its Table 4).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py -k oak_wilt
uv run pytest packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb      # rebuilds VDIFN's sweep; needs ../ag-vdifn
```
