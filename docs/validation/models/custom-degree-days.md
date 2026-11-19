# Custom degree days (`custom-degree-days`): validation

Model version 0.2, written 2026-11-18 (D98); 0.2 (2026-11-19) lets the simple average take an upper threshold. The model: `packages/agmodels/src/agmodels/models/custom_degree_days.py`, over the degree-day functions every model uses (`packages/agmodels/src/agmodels/degree_days.py`); its page: `custom_degree_days.md` beside it. Built in Phase 3 (PLAN.md, "Custom degree days").

**In short:** degree days by single sine (Baskerville and Emin 1969), simple average or modified average, with any base, upper threshold and start date. The sine's closed form matches a numerical integral of its own curve, and all three methods match the old AgWeather API's calculator to within 0.000001 degree days on 11,781 cases. On the archive's weather, a season's total at Waunakee came within 0.6 % of the old API's. There's nothing further to check against: a degree-day total is a definition, not a prediction.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Baskerville and Emin 1969 | The single-sine method: the day's temperature as a sine through the minimum and maximum, its area above a threshold in closed form | The sine method, with a horizontal cutoff at the upper threshold |
| The old AgWeather API's degree-day calculator (`../ag-weather`, `DegreeDaysCalculator`) | Sine, simple average and modified average at the threshold pairs its callers used | Compared only: v2's methods were written to give the same values, and do (below) |

## Choices and differences

- **Units:** thresholds may be given in °F or °C; degree days are linear in the temperature scale, so they're computed in °F with the thresholds converted and returned in °F·d (°C·d are 5/9 of them, converted for display).
- **Upper threshold:** every method takes one. The simple average caps both the minimum and the maximum at it before averaging (Funderburk et al. 1984's seedcorn maggot thermal units, and the API's degree-day calculator); the modified average also raises a minimum below the base to the base. Until 0.2 the model refused an upper threshold with the simple average, so its default (86 °F) made the simple average fail, while the API's calculator accepted one.
- **Missing days:** a missing day has no value and adds nothing to the running total.
- **Days:** midnight to midnight CST in the grid's box (D74); the old API's followed daylight saving time.

## Checks

### Against the method and the old API

Run in CI (`packages/agmodels/tests/test_degree_days.py`, `test_custom_degree_days.py`):

- `test_sine_matches_the_numerical_integral_of_its_curve`: the closed-form sine against a 200,000-step integral of Baskerville and Emin's (1969) curve, in 8 cases (below the base, crossing it, above the upper, crossing both, with no daily range, and in °C): within 0.0002 degree days. `test_sine_day_crossing_the_base_by_hand`: a day of 45 and 65 °F at base 50 gives 6.0899, worked by hand.
- `test_modified_average_by_hand` and `test_simple_average_by_hand`: the averages' rules at the base and upper threshold.
- `test_matches_the_old_api`: all three methods against the old API's calculator (recorded by `packages/agmodels/tests/fixtures/make_degree_days_legacy.rb`) at 17 threshold pairs × 231 minimum and maximum pairs from −10 to 110 °F, 11,781 cases: within 0.000001 degree days in every one. The old API is a reference, not the truth (D54).
- `test_custom_degree_days.py`: °C thresholds give the same °F·d as their °F equivalents, each method and option reaches the right function, and the simple average with an upper threshold caps both temperatures (a day of 60 and 100 °F at 50/86 gives 23, without the upper 30). The old API's simple average had no upper threshold, so the comparison with it covers the simple average without one.

### On the archive's weather

`scripts/compare_v1_dd_table.py`, in `docs/validation/legacy/v1-dd-table.md`: at Waunakee, Wisconsin, January 1 to October 31, 2026 (304 days), v2's single-sine totals against the old API's on its own weather:

| Setting | Old API | v2 | Difference |
| --- | --- | --- | --- |
| 50/86 °F | 3,203 | 3,184 | −0.6 % |
| 32 °F, no upper | 7,203 | 7,167 | −0.5 % |

The daily values differ by 0.29 and 0.40 °F·d on average (absolute); the daily minimums differ more than the maximums, mostly because v1's days followed daylight saving time (same report). The method is the same in both.

## Limits and open questions

- A degree-day total only means something with the thresholds, method and start a published model was built with; the user chooses them.
- Daily minimum and maximum can't capture days whose temperature curve isn't sine-like (a front passing), as hourly integration would.
- **Cheapest independent comparison:** degree days computed from Wisconet's hourly air temperature at its stations (by sine from the stations' daily extremes and by hourly integration) against the archive at their cells; this tests the weather behind the totals, which is where the error lies.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_degree_days.py packages/agmodels/tests/test_custom_degree_days.py
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
uv run python scripts/compare_v1_dd_table.py --start 2026-01-01 --end 2026-10-31   # needs the archive and the old API
```
