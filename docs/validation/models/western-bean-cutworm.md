# Western bean cutworm (`western-bean-cutworm`): validation

Model version 0.3, written 2026-11-21 (D98; part H2 of `docs/plans/models.md`). The model: `packages/agmodels/src/agmodels/insects/western_bean_cutworm.py`, run by the insect engine (`agmodels.phenology`, D36, D37); its page: `western_bean_cutworm.md` beside it. Versions 0.1–0.2 were VDIFN's ramp (single sine above 50 °F from May 1, (1320, 1420, 1535), Ahmad 1979's 25, 50 and 75 % flight), reported in this file's history.

**In short:** rebuilt on Hanson et al. 2015's flight model, which NEWA also runs (D95): the simple average with the daily mean capped, 38/75 °F from March 1, and a curve following their log-logistic flight within 2.3 percentage points. Against DATCP's Wisconsin pheromone traps (286 trap-years, 2021–2026, not used to build it) half the flight falls a median 3 days before the end of the trap's week, inside the week in about half the trap-years and within a week of it in 95 %. NEWA's deployed model counts fewer degree days than Hanson's method on hot days and puts the flight a median 3 days later than ours.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Hanson et al. 2015 ([doi:10.1093/jee/tov110](https://doi.org/10.1093/jee/tov110); read in full, every number here confirmed against the paper 2026-11-23) | Daily black light catches at Aurora, Clay Center, Concord and North Platte, Nebraska, 1981–2009 (73 site-years with ≥ 25 moths, half for development, half for validation). A grid search of 15,910 degree-day models by the concordance of predicted and observed 25 % flight; best: the simple method, the daily mean (not each temperature) capped at the upper threshold, 3.3 and 23.9 °C (38 and 75 °F), from March 1 (validation: 1.4 days late on average, SD 3.8, −7 to +7; Ahmad's 3.1, SD 4.6, −7 to +12). The whole flight as a log-logistic in °C·d, μ 7.315, s 0.044 (Table 4: 5, 10, 25, 50, 75, 90, 95 % at 2,377, 2,456, 2,577, 2,704, 2,838, 2,977, 3,077 °F·d). Scouting for egg masses between 25 and 50 % flight, 1,432 to 1,502 °C·d (p. 1737) | The method, start and thresholds; the flight curve |
| NEWA's western bean cutworm model (newa.cornell.edu/western-bean-cutworm, read 2026-11-21; methods and constants only) | Hanson's Table 4 with 10 % 2,455 and 90 % 2,977; counting days of year 60–305 in °C, base 3.3 °C; the daily formula caps the maximum at 23.9 °C before averaging, and as deployed rounds each day's max and min to a whole °C and passes them in the wrong order (`tmp/references/insects/notes/newa-insects.md`) | The 10 and 90 % levels; compared on the same weather |
| UW–Madison (A3646 2025; UW Vegetable Entomology, adapted from A3856) | Eggs hatch 5 to 7 days after they're laid (UW Vegetable Entomology; A3646 has eggs tan for 2–5 days, then deep purple 12–24 hours before hatch); scout from 25 % flight or the first moths caught nearby until 7–10 days after the peak; thresholds 5 % (field corn; A3646, where UW Vegetable Entomology's page still gives 8 %) and 4 % (processing sweet corn) of plants with egg masses or small larvae; the flight usually peaks in the second or third week of July in the Upper Midwest | The egg period (converted to degree days, below); the window's span; the page's advice |
| DATCP's black light and western bean cutworm pheromone trap networks, 2020–2026 (`docs/validation/data/datcp-blacklight-traps/`) | Weekly counts by site | A check (below), not used to build the model |
| VDIFN (versions 0.1–0.2) | Ahmad 1979's 25/50/75 % on single sine 50 °F from May 1 | Compared on the normals |

## Choices and differences

- **Method (D37, D95):** Hanson's simple method as their paper specifies it, `average_capped_mean`: min((min + max) / 2, 75) − 38, at least 0, from March 1 (a running total kept per model; no shared stored total). Hanson et al. warn that simple degree days computed another way (capping each temperature first) can mispredict.
- **NEWA's code differs** from Hanson's method in two ways, which we don't reproduce: its formula caps the day's maximum at 23.9 °C before averaging (fewer degree days on hot days than capping the mean), and as deployed it rounds each day's max and min to whole °C and passes them to the formula swapped (a day whose rounded minimum is below 3.3 °C counts nothing; the cap applies only when the minimum is above 23.9 °C). The swap alone hardly matters in Wisconsin (below); the cap on the maximum moves NEWA's flight about 3 days later. Recorded for the courtesy note to NEWA (D95: NEWA's source, followed as published, shows its code's formula off).
- **Adult flight:** a PERT (2,247, 2,685, 3,285) fitted to the log-logistic over 1,800–3,800 °F·d (2026-11-21): maximum difference 2.2 percentage points, RMSE 1.2; 5/10/25/50/75/90/95 % at 2,402, 2,455, 2,564, 2,705, 2,853, 2,978, 3,043. Weight 0: moths do no damage.
- **Egg masses (the risk, weight 1):** a derived stage from each moth's emergence (no pre-oviposition delay; none in degree days was found) for 200 °F·d: UW–Madison's 5 to 7 days to hatch, six days at about 33 °F·d a day, the rate of this method at Arlington on the normals from July 15 to August 1 (2,312 to 2,872 °F·d). No source gives the egg period in degree days. Egg masses peak at 2,787, about 80 after the middle of the flight.
- **Scouting window:** "Scout corn for egg masses", adult flight 5 % to 90 %: 2,402 to 2,977 °F·d. It opens at the first moths (the first level Hanson tabulates) and closes at 90 %, about 8 days after the middle of the flight at Arlington's late-July rate, matching UW–Madison's "7–10 days after the peak". Hanson's own advice (25–50 %) is narrower.
- **One generation; the start is locked at March 1** (Ben, 2026-11-23). Hanson et al. chose the thresholds (38/75 °F) by how well degree days counted from March 1 predicted the flight, so the thresholds and the flight curve have no meaning counted from another day: the model takes no grower's date. Its biofix label is plain "March 1", as for the January 1 insects, and the API refuses a `biofix` sent for this model (`Insect.biofix_fixed`, the spec's `Biofix.fixed`; discovery reports it as fixed).
- **Training area:** Nebraska, 1981–2009 (`trained`); Wisconsin points get the training-area warning, though the checks below find the model on time in Wisconsin's traps.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from March 1) reach 2,284, the first adult flight (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: July 7 at Madison, July 14 at Hancock, July 27 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) July 3. Where we don't have the normals it opens on June 15. It ends after September 30 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_western_bean_cutworm.py`, run in CI:

- Hanson's Table 4 is the log-logistic (μ 7.315, s 0.044) within 0.6 percentage points at each level.
- Our flight curve follows the log-logistic within 2.3 percentage points from 1,800 to 3,800 (RMSE at most 1.3), and passes 5, 50 and 95 % at 2,402, 2,705 and 3,043 against Table 4's 2,377, 2,704 and 3,077 (each level within 40).
- The daily degree days cap the mean, not the maximum: a 60/100 °F day counts 75 − 38 = 37.
- The window opens at 5 % and closes at 90 % (within 2 of NEWA's 2,977); egg masses carry the risk, peaking between 50 and 75 % of the flight.

### Against NEWA on the same weather

`scripts/check_western_bean_cutworm.py`, part 1; full table in [western-bean-cutworm/weather.md](western-bean-cutworm/weather.md). NEWA's model as deployed and as its formula is written, recomputed from its page's rules, on the hours of Wisconsin's NEWA stations, 2024 and 2025 (66 station-years), against ours on the same days and on the archive at each station's cell.

| Later (+) or earlier (−) than NEWA as deployed, days | 25 %          | 50 %          | 75 %          |
| ---------------------------------------------------- | ------------- | ------------- | ------------- |
| NEWA's formula without the swap and rounding         | 0 (−2 to +2)  | 0 (−2 to +2)  | +1 (−1 to +2) |
| Hanson's method at NEWA's totals                     | −4 (−6 to −2) | −3 (−7 to −2) | −3 (−6 to −2) |
| Ours, station days                                   | −4 (−7 to −2) | −3 (−7 to −2) | −3 (−6 to −1) |
| Ours, archive                                        | −5 (−9 to −1) | −4 (−8 to −1) | −3 (−8 to 0)  |

Medians, with the 10th–90th percentiles. By August 1 the station-years averaged 2,794 °F·d from March 1 by NEWA as deployed, 2,774 as its formula is written, and 2,915 by Hanson's method. So NEWA's argument swap moves dates by about a day either way, while its cap on the maximum, rather than the mean, puts the flight about 3 days after Hanson's method.

### Typical dates in Wisconsin

`scripts/check_western_bean_cutworm.py`, part 2: the day the 1996–2025 normal running total (each year's own from March 1, averaged; computed from the climatology store as `/api/v2/climate/normals` does, since the capped mean isn't one of its methods) reaches each event.

| Event                                         | Degree days                                | Arlington               | Hancock                | Rhinelander             |
| --------------------------------------------- | ------------------------------------------ | ----------------------- | ---------------------- | ----------------------- |
| 5 % of the moths have flown; the window opens | 2,402                                      | Jul 18                  | Jul 23                 | Aug 2                   |
| 25 %                                          | 2,564                                      | Jul 23                  | Jul 28                 | Aug 8                   |
| 50 %                                          | 2,705                                      | Jul 27                  | Aug 2                  | Aug 13                  |
| Most egg masses                               | 2,787                                      | Jul 30                  | Aug 4                  | Aug 16                  |
| 75 %                                          | 2,853                                      | Aug 1                   | Aug 6                  | Aug 18                  |
| 90 %; the window closes                       | 2,978                                      | Aug 5                   | Aug 10                 | Aug 23                  |
| Old (VDIFN) 25 / 50 / 75 %                    | 1,320 / 1,420 / 1,535 (sine 50 from May 1) | Jul 24 / Jul 29 / Aug 3 | Jul 29 / Aug 3 / Aug 9 | Aug 9 / Aug 15 / Aug 23 |

On the normals the new model's flight comes 1–2 days before the old one's in the middle, and its window covers the whole flight rather than 25–75 %. UW–Madison describes the flight peaking in the second or third week of July; the normals put the middle of the flight in late July in the south and mid-August in the north, but DATCP's traps in 2021–2026 (warmer years) agree with the model's dates (below).

### Against Wisconsin's traps

`scripts/check_western_bean_cutworm.py`, part 3; full tables in [western-bean-cutworm/weather.md](western-bean-cutworm/weather.md); data in [../data/datcp-blacklight-traps/](../data/datcp-blacklight-traps/README.md). For each site-year with at least 25 moths (Hanson's rule), the week in which the season's catch passed 25, 50 and 75 %, against the day our curve passes the same level on the archive at the trap's approximate location. A week's catch is dated by its last day, so −6 to 0 days is inside the week; "within a week" is −13 to +7. The model wasn't fitted to these data: they test it.

| Ours − the trap's week end, days                                           | 25 %          | 50 %          | 75 %           |
| -------------------------------------------------------------------------- | ------------- | ------------- | -------------- |
| Pheromone traps, 286 trap-years, 2021–2026: median (10th–90th percentile)  | −3 (−9 to +5) | −3 (−8 to +4) | −2 (−8 to +6)  |
| inside the week / within a week of it                                      | 145 / 268     | 135 / 273     | 163 / 263      |
| Black light traps, 38 site-years, 2020–2026: median (10th–90th percentile) | 0 (−6 to +8)  | +2 (−3 to +9) | +3 (−4 to +12) |
| inside the week / within a week of it                                      | 18 / 34       | 17 / 30       | 9 / 29         |

- In the pheromone network the model's dates fall inside the trap's week at the median at every level. Pheromone traps catch males only, and males may fly later than females (Hanson et al. 2015, citing Mahrt et al. 1987), which would make the model look early here, not late.
- The black light traps, the kind the model was fitted to, are few (6–13 sites) and catch few moths; at those, the model runs a median 0–3 days after the trap's week. All seven of 2020's site-years run late (+6 to +23 days at 50 %; 2020's counts come from the weekly bulletins, with a week in late June missing); without them the medians are −1, 0 and +2 days (31 site-years).
- Trap locations are approximate (town centres or DATCP's 2026 survey points), and blanks in 2024–2025 are read as zeros (the data's README).

## Limits and open questions

- **Egg masses** are timed by a duration given in days, not degree days (UW–Madison's 5–7 days), and with no pre-oviposition delay; how long young larvae stay exposed before entering the ear isn't modeled.
- **Fitted in Nebraska.** Hanson et al. asked for validation in other states; DATCP's traps are that check for Wisconsin and find the model on time, but by the trap's week only.
- **Migration** (moths moved by storms) is beyond any degree-day model.
- **The start can't be the grower's:** a local first catch can't restart the count (the curve is cumulative from March 1). A grower with traps reads the model's flight against their own catches instead.
- **NEWA's difference** (its formula and code) is recorded for the courtesy note to NEWA; agreement with NEWA isn't expected until NEWA's code follows Hanson.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_western_bean_cutworm.py
uv run python scripts/fetch_newa.py                  # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_western_bean_cutworm.py  # needs the archive in data/, the station hours and the trap data
```
