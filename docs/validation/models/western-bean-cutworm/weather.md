# Western bean cutworm: NEWA on the same weather, typical dates in Wisconsin, and DATCP's traps

Written by `scripts/check_western_bean_cutworm.py`. Ours: Hanson et al. 2015's simple degree days (the daily mean capped at 75 °F, base 38 °F) from March 1, and a curve following their log-logistic flight. Station days are NEWA's on the local clock; the archive's are CST.

## 1. NEWA's model against ours, on the station's hours and the archive's

Our curve passes 5, 10, 25, 50, 75, 90 and 95 % of the flight at 2,402, 2,455, 2,564, 2,705, 2,853, 2,978, 3,043 °F·d (Hanson's Table 4 and NEWA: 2,378, 2,455, 2,578, 2,704, 2,839, 2,977, 3,076). Dates of 25, 50 and 75 % of the flight: NEWA as deployed / NEWA as intended / ours on the station's days / ours on the archive.

| Station                         | Year | 25 %                              | 50 %                              | 75 %                              |
| ------------------------------- | ---- | --------------------------------- | --------------------------------- | --------------------------------- |
| Baileys Harbor                  | 2024 | Aug 14 / Aug 10 / Aug 6 / Aug 5   | Aug 18 / Aug 15 / Aug 12 / Aug 11 | Aug 23 / Aug 19 / Aug 17 / Aug 16 |
| Baileys Harbor                  | 2025 | Aug 17 / Aug 16 / Aug 13 / Aug 12 | Aug 22 / Aug 20 / Aug 17 / Aug 16 | Aug 27 / Aug 26 / Aug 22 / Aug 21 |
| Belgium                         | 2024 | Jul 26 / Jul 26 / Jul 23 / Jul 23 | Jul 30 / Jul 30 / Jul 28 / Jul 28 | Aug 2 / Aug 3 / Aug 1 / Aug 1     |
| Belgium                         | 2025 | Aug 7 / Aug 5 / Jul 31 / Jul 29   | Aug 10 / Aug 9 / Aug 5 / Aug 3    | Aug 14 / Aug 13 / Aug 10 / Aug 8  |
| Belmont                         | 2024 | Jul 12 / Jul 15 / Jul 10 / Jul 14 | Jul 16 / Jul 19 / Jul 14 / Jul 19 | Jul 20 / Jul 24 / Jul 19 / Jul 24 |
| Belmont                         | 2025 | Jul 16 / Jul 19 / Jul 12 / Jul 16 | Jul 19 / Jul 23 / Jul 16 / Jul 21 | Jul 23 / Jul 27 / Jul 21 / Jul 25 |
| Brighton                        | 2024 | Jul 13 / Jul 16 / Jul 12 / Jul 12 | Jul 17 / Jul 20 / Jul 16 / Jul 16 | Jul 21 / Jul 25 / Jul 20 / Jul 21 |
| Brighton                        | 2025 | Jul 23 / Jul 24 / Jul 19 / Jul 19 | Jul 26 / Jul 28 / Jul 23 / Jul 23 | Jul 30 / Aug 1 / Jul 27 / Jul 27  |
| Brooklyn                        | 2024 | Jul 15 / Jul 16 / Jul 12 / Jul 13 | Jul 19 / Jul 20 / Jul 16 / Jul 17 | Jul 23 / Jul 25 / Jul 21 / Jul 22 |
| Brooklyn                        | 2025 | Jul 19 / Jul 20 / Jul 15 / Jul 16 | Jul 22 / Jul 24 / Jul 20 / Jul 21 | Jul 26 / Jul 28 / Jul 24 / Jul 25 |
| Brodhead                        | 2024 | Jul 13 / Jul 13 / Jul 10 / Jul 11 | Jul 16 / Jul 17 / Jul 14 / Jul 15 | Jul 21 / Jul 22 / Jul 18 / Jul 20 |
| Brodhead                        | 2025 | Jul 18 / Jul 19 / Jul 14 / Jul 15 | Jul 22 / Jul 23 / Jul 19 / Jul 20 | Jul 26 / Jul 27 / Jul 23 / Jul 24 |
| Burlington (Munster)            | 2024 | Jul 16 / Jul 18 / Jul 13 / Jul 12 | Jul 20 / Jul 23 / Jul 17 / Jul 16 | Jul 25 / Jul 28 / Jul 22 / Jul 21 |
| Burlington (Munster)            | 2025 | Jul 26 / Jul 25 / Jul 19 / Jul 19 | Jul 29 / Jul 29 / Jul 23 / Jul 23 | Aug 2 / Aug 3 / Jul 28 / Jul 27   |
| Chippewa Falls                  | 2024 | Jul 25 / Jul 25 / Jul 21 / Jul 22 | Jul 29 / Jul 29 / Jul 26 / Jul 27 | Aug 2 / Aug 2 / Jul 30 / Jul 31   |
| Chippewa Falls                  | 2025 | Jul 27 / Jul 27 / Jul 23 / Jul 23 | Jul 30 / Jul 31 / Jul 27 / Jul 27 | Aug 4 / Aug 5 / Jul 31 / Aug 1    |
| Colgate                         | 2024 | Jul 25 / Jul 25 / Jul 20 / Jul 20 | Jul 29 / Jul 29 / Jul 25 / Jul 25 | Aug 2 / Aug 2 / Jul 30 / Jul 30   |
| Colgate                         | 2025 | Jul 31 / Jul 30 / Jul 26 / Jul 24 | Aug 5 / Aug 4 / Jul 30 / Jul 28   | Aug 8 / Aug 8 / Aug 4 / Aug 2     |
| Eau Claire                      | 2024 | Jul 30 / Jul 29 / Jul 25 / Jul 21 | Aug 2 / Aug 2 / Jul 29 / Jul 26   | Aug 7 / Aug 7 / Aug 2 / Jul 30    |
| Eau Claire                      | 2025 | Jul 31 / Jul 30 / Jul 25 / Jul 22 | Aug 5 / Aug 4 / Jul 29 / Jul 26   | Aug 8 / Aug 8 / Aug 3 / Jul 30    |
| Eau Clair (Ferguson's Orchards) | 2024 | Jul 27 / Jul 25 / Jul 22 / Jul 22 | Jul 30 / Jul 29 / Jul 26 / Jul 26 | Aug 3 / Aug 2 / Jul 30 / Jul 31   |
| Eau Clair (Ferguson's Orchards) | 2025 | Jul 26 / Jul 27 / Jul 23 / Jul 23 | Jul 29 / Jul 30 / Jul 27 / Jul 26 | Aug 3 / Aug 4 / Jul 31 / Jul 31   |
| Edgar                           | 2024 | Aug 8 / Aug 6 / Aug 2 / Aug 3     | Aug 13 / Aug 12 / Aug 7 / Aug 8   | Aug 18 / Aug 17 / Aug 13 / Aug 14 |
| Edgar                           | 2025 | Aug 11 / Aug 9 / Aug 5 / Aug 5    | Aug 15 / Aug 13 / Aug 9 / Aug 10  | Aug 19 / Aug 18 / Aug 14 / Aug 15 |
| Fort Atkinson (Warm Belly Farm) | 2024 | Jul 15 / Jul 16 / Jul 12 / Jul 12 | Jul 19 / Jul 20 / Jul 16 / Jul 16 | Jul 23 / Jul 24 / Jul 21 / Jul 21 |
| Fort Atkinson (Warm Belly Farm) | 2025 | Jul 21 / Jul 22 / Jul 16 / Jul 17 | Jul 25 / Jul 25 / Jul 21 / Jul 21 | Jul 28 / Jul 29 / Jul 25 / Jul 25 |
| Galesville (Ferguson)           | 2025 | Jul 22 / Jul 22 / Jul 17 / Jul 19 | Jul 25 / Jul 26 / Jul 21 / Jul 23 | Jul 28 / Jul 30 / Jul 25 / Jul 27 |
| Galesville                      | 2024 | Jul 25 / Jul 23 / Jul 18 / Jul 18 | Jul 29 / Jul 27 / Jul 23 / Jul 22 | Aug 1 / Jul 31 / Jul 28 / Jul 27  |
| Galesville                      | 2025 | Jul 23 / Jul 23 / Jul 19 / Jul 17 | Jul 26 / Jul 26 / Jul 23 / Jul 21 | Jul 30 / Jul 30 / Jul 27 / Jul 25 |
| Gays Mills                      | 2024 | Jul 19 / Jul 19 / Jul 16 / Jul 14 | Jul 23 / Jul 23 / Jul 20 / Jul 18 | Jul 27 / Jul 28 / Jul 25 / Jul 23 |
| Gays Mills                      | 2025 | Jul 20 / Jul 21 / Jul 17 / Jul 15 | Jul 24 / Jul 25 / Jul 21 / Jul 20 | Jul 27 / Jul 29 / Jul 25 / Jul 24 |
| Genoa City                      | 2024 | Jul 11 / Jul 14 / Jul 10 / Jul 13 | Jul 15 / Jul 18 / Jul 14 / Jul 17 | Jul 19 / Jul 23 / Jul 18 / Jul 21 |
| Genoa City                      | 2025 | Jul 23 / Jul 23 / Jul 19 / Jul 19 | Jul 26 / Jul 27 / Jul 23 / Jul 23 | Jul 29 / Jul 31 / Jul 27 / Jul 27 |
| Gays Mills (Sandcreek)          | 2024 | Jul 18 / Jul 18 / Jul 15 / Jul 16 | Jul 22 / Jul 22 / Jul 20 / Jul 20 | Jul 27 / Jul 27 / Jul 24 / Jul 25 |
| Gays Mills (Sandcreek)          | 2025 | Jul 19 / Jul 20 / Jul 16 / Jul 18 | Jul 23 / Jul 24 / Jul 20 / Jul 22 | Jul 27 / Jul 28 / Jul 25 / Jul 26 |
| Malone                          | 2024 | Jul 21 / Jul 22 / Jul 18 / Jul 20 | Jul 25 / Jul 26 / Jul 22 / Jul 24 | Jul 29 / Jul 30 / Jul 27 / Jul 29 |
| Malone                          | 2025 | Jul 28 / Jul 27 / Jul 24 / Jul 27 | Jul 31 / Jul 31 / Jul 28 / Jul 31 | Aug 4 / Aug 5 / Aug 1 / Aug 5     |
| Mauston (Northwoods)            | 2024 | Jul 20 / Jul 21 / Jul 16 / Jul 20 | Jul 24 / Jul 25 / Jul 21 / Jul 25 | Jul 28 / Jul 29 / Jul 26 / Jul 29 |
| Mauston (Northwoods)            | 2025 | Jul 23 / Jul 24 / Jul 19 / Jul 22 | Jul 27 / Jul 27 / Jul 23 / Jul 26 | Jul 30 / Aug 1 / Jul 27 / Jul 30  |
| Mequon (Barthel)                | 2024 | Jul 25 / Jul 26 / Jul 22 / Jul 19 | Jul 30 / Jul 30 / Jul 27 / Jul 23 | Aug 2 / Aug 3 / Jul 31 / Jul 28   |
| Mequon (Barthel)                | 2025 | Aug 6 / Aug 3 / Jul 29 / Jul 26   | Aug 10 / Aug 7 / Aug 3 / Jul 30   | Aug 14 / Aug 11 / Aug 8 / Aug 4   |
| Merrill (Helenes)               | 2024 | Aug 9 / Aug 6 / Aug 1 / Aug 3     | Aug 14 / Aug 12 / Aug 6 / Aug 8   | Aug 19 / Aug 17 / Aug 13 / Aug 14 |
| Merrill (Helenes)               | 2025 | Aug 13 / Aug 10 / Aug 6 / Aug 6   | Aug 17 / Aug 14 / Aug 10 / Aug 10 | Aug 22 / Aug 19 / Aug 15 / Aug 15 |
| Mount Horeb (Atoms to Apples)   | 2024 | Jul 18 / Jul 20 / Jul 15 / Jul 13 | Jul 22 / Jul 24 / Jul 20 / Jul 17 | Jul 27 / Jul 29 / Jul 25 / Jul 22 |
| Mount Horeb (Atoms to Apples)   | 2025 | – / – / – / Jul 16                | – / – / – / Jul 20                | – / – / – / Jul 25                |
| Mt Horeb                        | 2024 | Jul 19 / Jul 19 / Jul 15 / Jul 13 | Jul 23 / Jul 24 / Jul 20 / Jul 16 | Jul 28 / Jul 28 / Jul 25 / Jul 21 |
| Mt Horeb                        | 2025 | Jul 24 / Jul 23 / Jul 18 / Jul 15 | Jul 28 / Jul 27 / Jul 23 / Jul 19 | Aug 1 / Aug 1 / Jul 27 / Jul 24   |
| Niagara                         | 2024 | Aug 12 / Aug 9 / Aug 3 / Aug 5    | Aug 16 / Aug 14 / Aug 8 / Aug 11  | Aug 21 / Aug 19 / Aug 14 / Aug 16 |
| Niagara                         | 2025 | Aug 15 / Aug 13 / Aug 7 / Aug 9   | Aug 20 / Aug 17 / Aug 11 / Aug 13 | Aug 25 / Aug 22 / Aug 16 / Aug 18 |
| Plymouth (Log Cabin)            | 2024 | Jul 24 / Jul 25 / Jul 20 / Jul 22 | Jul 28 / Jul 29 / Jul 24 / Jul 27 | Aug 1 / Aug 2 / Jul 29 / Jul 31   |
| Plymouth (Log Cabin)            | 2025 | Aug 4 / Aug 3 / Jul 27 / Jul 28   | Aug 8 / Aug 7 / Jul 31 / Aug 2    | Aug 12 / Aug 11 / Aug 5 / Aug 7   |
| Grafton (Dream Apple)           | 2024 | Jul 30 / Jul 30 / Jul 28 / Jul 24 | Aug 2 / Aug 3 / Aug 1 / Jul 29    | Aug 6 / Aug 7 / Aug 5 / Aug 2     |
| Grafton (Dream Apple)           | 2025 | Aug 6 / Aug 7 / Aug 4 / Aug 1     | Aug 10 / Aug 11 / Aug 8 / Aug 6   | Aug 14 / Aug 15 / Aug 13 / Aug 10 |
| Richland Center (Oakwood)       | 2024 | Jul 20 / Jul 20 / Jul 16 / Jul 15 | Jul 24 / Jul 24 / Jul 21 / Jul 20 | Jul 28 / Jul 29 / Jul 26 / Jul 25 |
| Richland Center (Oakwood)       | 2025 | Jul 22 / Jul 23 / Jul 18 / Jul 18 | Jul 26 / Jul 26 / Jul 23 / Jul 22 | Jul 29 / Jul 31 / Jul 27 / Jul 26 |
| Rochester (Ela)                 | 2024 | Jul 25 / Jul 24 / Jul 19 / Jul 13 | Jul 29 / Jul 28 / Jul 23 / Jul 17 | Aug 2 / Aug 1 / Jul 29 / Jul 22   |
| Rochester (Ela)                 | 2025 | Jul 31 / Jul 29 / Jul 24 / Jul 20 | Aug 5 / Aug 3 / Jul 28 / Jul 24   | Aug 8 / Aug 8 / Aug 2 / Jul 28    |
| Spring Valley                   | 2024 | Jul 28 / Jul 27 / Jul 23 / Jul 25 | Aug 1 / Jul 31 / Jul 28 / Jul 29  | Aug 4 / Aug 4 / Aug 1 / Aug 2     |
| Spring Valley                   | 2025 | Jul 26 / Jul 27 / Jul 23 / Jul 25 | Jul 29 / Aug 1 / Jul 27 / Jul 29  | Aug 3 / Aug 6 / Jul 31 / Aug 3    |
| Trempealeau (Ecker)             | 2024 | Jul 28 / Jul 26 / Jul 21 / Jul 16 | Jul 31 / Jul 30 / Jul 25 / Jul 21 | Aug 4 / Aug 3 / Jul 29 / Jul 26   |
| Trempealeau (Ecker)             | 2025 | Jul 24 / Jul 25 / Jul 20 / Jul 16 | Jul 28 / Jul 29 / Jul 24 / Jul 20 | Jul 31 / Aug 2 / Jul 28 / Jul 25  |
| Verona (West Mad Ag Sta)        | 2024 | Jul 17 / Jul 17 / Jul 14 / Jul 15 | Jul 21 / Jul 22 / Jul 19 / Jul 20 | Jul 25 / Jul 26 / Jul 23 / Jul 25 |
| Verona (West Mad Ag Sta)        | 2025 | Jul 21 / Jul 22 / Jul 18 / Jul 19 | Jul 25 / Jul 25 / Jul 22 / Jul 23 | Jul 28 / Jul 29 / Jul 26 / Jul 27 |
| Wabasha                         | 2024 | Jul 17 / Jul 18 / Jul 15 / Jul 16 | Jul 21 / Jul 22 / Jul 19 / Jul 20 | Jul 25 / Jul 27 / Jul 24 / Jul 25 |
| Wabasha                         | 2025 | Jul 20 / Jul 22 / Jul 18 / Jul 18 | Jul 24 / Jul 25 / Jul 22 / Jul 22 | Jul 27 / Jul 29 / Jul 26 / Jul 26 |
| Waupaca                         | 2024 | Jul 30 / Jul 29 / Jul 25 / Jul 22 | Aug 3 / Aug 2 / Jul 29 / Jul 27   | Aug 7 / Aug 7 / Aug 2 / Jul 31    |
| Waupaca                         | 2025 | Aug 3 / Aug 2 / Jul 28 / Jul 25   | Aug 7 / Aug 6 / Aug 1 / Jul 29    | Aug 11 / Aug 11 / Aug 6 / Aug 4   |

Days later (+) or earlier (−) than NEWA as deployed (median, 10th–90th percentile, range, n):

- NEWA as intended (the code's slip alone), 5 %: +0 (-3 to +1; -4 to +2), n = 66
- NEWA as intended (the code's slip alone), 25 %: +0 (-2 to +2; -4 to +3), n = 66
- NEWA as intended (the code's slip alone), 50 %: +0 (-2 to +2; -3 to +4), n = 66
- NEWA as intended (the code's slip alone), 75 %: +1 (-1 to +2; -4 to +4), n = 66
- NEWA as intended (the code's slip alone), 95 %: +2 (-1 to +3; -5 to +6), n = 66
- Hanson's simple method at NEWA's totals (the method alone), 5 %: -4 (-7 to -2; -8 to -1), n = 66
- Hanson's simple method at NEWA's totals (the method alone), 25 %: -4 (-6 to -2; -8 to -1), n = 66
- Hanson's simple method at NEWA's totals (the method alone), 50 %: -3 (-7 to -2; -9 to -1), n = 66
- Hanson's simple method at NEWA's totals (the method alone), 75 %: -3 (-6 to -2; -10 to -1), n = 66
- Hanson's simple method at NEWA's totals (the method alone), 95 %: -3 (-7 to -2; -15 to -1), n = 66
- ours on the station's days (method and curve), 5 %: -3 (-6 to -1; -7 to -1), n = 66
- ours on the station's days (method and curve), 25 %: -4 (-7 to -2; -9 to -1), n = 66
- ours on the station's days (method and curve), 50 %: -3 (-7 to -2; -9 to -1), n = 66
- ours on the station's days (method and curve), 75 %: -3 (-6 to -1; -9 to -1), n = 66
- ours on the station's days (method and curve), 95 %: -4 (-8 to -3; -16 to -2), n = 66
- ours on the archive, 5 %: -3 (-8 to +0; -11 to +3), n = 66
- ours on the archive, 25 %: -5 (-9 to -1; -12 to +2), n = 66
- ours on the archive, 50 %: -4 (-8 to -1; -12 to +3), n = 66
- ours on the archive, 75 %: -3 (-8 to +0; -11 to +4), n = 66
- ours on the archive, 95 %: -5 (-11 to -1; -13 to +3), n = 66

Degree days (°F) from March 1 to August 1, mean over the station-years: NEWA as deployed 2,794, as intended 2,774, Hanson's method 2,915.

## 2. Typical dates on the 1996–2025 normals

The day the normal running total (each year's own, averaged over the 30 years, at the archive's cell) reaches each event. Ours: Hanson's simple method, 38/75 °F from March 1. Old: VDIFN's model, single sine above 50 °F from May 1.

| Event                        | Degree days     | Arlington | Hancock | Rhinelander |
| ---------------------------- | --------------- | --------- | ------- | ----------- |
| 5 % of the moths have flown  | 2,402           | Jul 18    | Jul 23  | Aug 2       |
| 25 % of the moths have flown | 2,564           | Jul 23    | Jul 28  | Aug 8       |
| 50 % of the moths have flown | 2,705           | Jul 27    | Aug 2   | Aug 13      |
| 75 % of the moths have flown | 2,853           | Aug 1     | Aug 6   | Aug 18      |
| 90 % of the moths have flown | 2,978           | Aug 5     | Aug 10  | Aug 23      |
| Scouting window opens        | 2,402           | Jul 18    | Jul 23  | Aug 2       |
| Most egg masses in fields    | 2,787           | Jul 30    | Aug 4   | Aug 16      |
| Scouting window closes       | 2,977           | Aug 5     | Aug 10  | Aug 23      |
| Old: 25 % flown              | 1,320 (sine 50) | Jul 24    | Jul 29  | Aug 9       |
| Old: 50 % flown              | 1,420 (sine 50) | Jul 29    | Aug 3   | Aug 15      |
| Old: 75 % flown              | 1,535 (sine 50) | Aug 3     | Aug 9   | Aug 23      |

## 3. DATCP's traps

From `docs/validation/data/datcp-blacklight-traps/` (DATCP's weekly counts; see its README). Each site-year with at least 25 moths (Hanson et al.'s rule): the week (its last day) in which the season's catch passed 25, 50 and 75 %, against the day our curve passes the same level on the archive at the trap's approximate location. A week's catch is dated by its last day, so a difference from −6 to 0 days falls inside the week. Hanson's model was fitted to black light traps, which catch both sexes; pheromone traps catch males, whose flight can peak later (Hanson et al. 2015, citing Mahrt et al. 1987).

### Black light traps

Ours − the trap's week end, days (median, 10th–90th percentile; inside the week, −6 to 0; within a week either side, −13 to +7; n):

- 25 %: +0 (-6 to +8; inside 18, within a week 34), n = 38
- 50 %: +2 (-3 to +9; inside 17, within a week 30), n = 38
- 75 %: +3 (-4 to +12; inside 9, within a week 29), n = 38

| Site         | Year | Moths | 25 % week / ours − it | 50 %         | 75 %         |
| ------------ | ---- | ----- | --------------------- | ------------ | ------------ |
| Antigo       | 2020 | 27    | Jul 29 / +17          | Jul 29 / +23 | Aug 12 / +13 |
| Beaver Dam   | 2020 | 94    | Jul 29 / +1           | Jul 29 / +7  | Jul 29 / +11 |
| East Troy    | 2020 | 268   | Jul 22 / +4           | Jul 22 / +8  | Jul 29 / +7  |
| Hancock      | 2020 | 29    | Jul 22 / +11          | Jul 22 / +17 | Jul 22 / +22 |
| Pardeeville  | 2020 | 192   | Jul 22 / +6           | Jul 22 / +10 | Jul 22 / +16 |
| Ripon        | 2020 | 169   | Jul 29 / +1           | Jul 29 / +6  | Jul 29 / +11 |
| Wausau       | 2020 | 47    | Jul 29 / +12          | Jul 29 / +17 | Aug 5 / +15  |
| Beaver Dam   | 2021 | 235   | Jul 21 / -1           | Jul 21 / +3  | Jul 21 / +7  |
| East Troy    | 2021 | 479   | Jul 14 / +2           | Jul 21 / +0  | Jul 21 / +4  |
| Marshfield   | 2021 | 91    | Jul 21 / +7           | Jul 28 / +5  | Jul 28 / +10 |
| Pardeeville  | 2021 | 566   | Jul 14 / +4           | Jul 14 / +8  | Jul 21 / +5  |
| Ripon        | 2021 | 210   | Jul 21 / -1           | Jul 21 / +3  | Jul 28 / +0  |
| Sparta       | 2021 | 169   | Jul 21 / +2           | Jul 21 / +6  | Jul 21 / +10 |
| Wausau       | 2021 | 42    | Jul 21 / +7           | Aug 4 / -2   | Aug 4 / +3   |
| Beaver Dam   | 2022 | 29    | Jul 28 / -2           | Aug 4 / -5   | Aug 11 / -7  |
| East Troy    | 2022 | 632   | Jul 28 / -6           | Jul 28 / -2  | Jul 28 / +3  |
| Pardeeville  | 2022 | 116   | Jul 14 / +10          | Jul 21 / +8  | Jul 28 / +6  |
| Ripon        | 2022 | 164   | Jul 28 / -1           | Aug 4 / -3   | Aug 4 / +1   |
| Beaver Dam   | 2023 | 64    | Jul 27 / -4           | Jul 27 / +0  | Aug 3 / -2   |
| East Troy    | 2023 | 274   | Jul 27 / -6           | Jul 27 / -2  | Jul 27 / +2  |
| Marshfield   | 2023 | 73    | Jul 27 / +5           | Jul 27 / +9  | Aug 3 / +7   |
| Ripon        | 2023 | 90    | Jul 27 / -2           | Aug 3 / -6   | Aug 3 / -1   |
| Wausau       | 2023 | 100   | Aug 3 / +0            | Aug 10 / -3  | Aug 10 / +2  |
| Wausau North | 2023 | 36    | Aug 3 / -2            | Aug 3 / +2   | Aug 10 / +0  |
| Beaver Dam   | 2024 | 36    | Jul 18 / +0           | Jul 25 / -3  | Aug 1 / -5   |
| East Troy    | 2024 | 236   | Jul 18 / -4           | Jul 18 / +0  | Jul 18 / +5  |
| Marshfield   | 2024 | 101   | Jul 25 / +5           | Aug 1 / +2   | Aug 1 / +7   |
| Ripon        | 2024 | 339   | Jul 25 / -6           | Jul 25 / -2  | Jul 25 / +3  |
| Wausau       | 2024 | 137   | Aug 1 / -1            | Aug 1 / +3   | Aug 8 / +2   |
| Wausau North | 2024 | 38    | Aug 8 / -10           | Aug 8 / -6   | Aug 22 / -14 |
| East Troy    | 2025 | 62    | Jul 24 / -5           | Jul 24 / +0  | Jul 24 / +4  |
| Marshfield   | 2025 | 43    | Jul 31 / -1           | Jul 31 / +4  | Aug 7 / +2   |
| Ripon        | 2025 | 40    | Jul 31 / -7           | Jul 31 / -3  | Jul 31 / +2  |
| Wausau       | 2025 | 85    | Jul 31 / +3           | Aug 7 / +1   | Aug 7 / +5   |
| Wausau North | 2025 | 85    | Aug 7 / -6            | Aug 7 / -1   | Aug 14 / -4  |
| Beaver Dam   | 2026 | 34    | Jul 15 / +3           | Jul 22 / +1  | Jul 29 / -2  |
| East Troy    | 2026 | 133   | Jul 22 / -8           | Jul 22 / -4  | Jul 22 / +0  |
| Wausau E     | 2026 | 69    | Jul 29 / +0           | Jul 29 / +4  | Aug 12 / -5  |

### Pheromone traps

Ours − the trap's week end, days (median, 10th–90th percentile; inside the week, −6 to 0; within a week either side, −13 to +7; n):

- 25 %: -3 (-9 to +5; inside 145, within a week 268), n = 286
- 50 %: -3 (-8 to +4; inside 135, within a week 273), n = 286
- 75 %: -2 (-8 to +6; inside 163, within a week 263), n = 286

| Site              | Year | Moths | 25 % week / ours − it | 50 %         | 75 %         |
| ----------------- | ---- | ----- | --------------------- | ------------ | ------------ |
| Abrams            | 2021 | 39    | Jul 28 / +0           | Jul 28 / +4  | Aug 4 / +2   |
| Antigo            | 2021 | 87    | Jul 28 / +8           | Jul 28 / +13 | Aug 4 / +12  |
| Arlington         | 2021 | 172   | Jul 21 / -2           | Jul 21 / +2  | Jul 28 / -1  |
| Arlington N       | 2021 | 68    | Jul 21 / -3           | Jul 28 / -5  | Jul 28 / -1  |
| Atlas             | 2021 | 49    | Jul 28 / +0           | Aug 4 / -2   | Aug 4 / +3   |
| Beaver Dam        | 2021 | 244   | Jul 21 / -1           | Jul 28 / -4  | Jul 28 / +0  |
| Columbus          | 2021 | 55    | Jul 21 / -3           | Jul 21 / +1  | Jul 21 / +5  |
| Crivitz           | 2021 | 80    | Jul 28 / +3           | Aug 4 / +0   | Aug 11 / -2  |
| Fall River        | 2021 | 49    | Jul 21 / -3           | Jul 28 / -5  | Jul 28 / -1  |
| Fort Winnebago    | 2021 | 210   | Jul 21 / -2           | Jul 28 / -5  | Jul 28 / -1  |
| Grantsburg        | 2021 | 30    | Jul 28 / -2           | Jul 28 / +2  | Aug 4 / +0   |
| Greenfield        | 2021 | 170   | Jul 21 / -5           | Jul 28 / -8  | Aug 4 / -10  |
| Hancock           | 2021 | 55    | Jul 28 / -4           | Jul 28 / +0  | Aug 4 / -2   |
| Lake Delton       | 2021 | 221   | Jul 21 / -2           | Jul 28 / -4  | Aug 4 / -7   |
| Lewiston          | 2021 | 458   | Jul 21 / -3           | Jul 28 / -5  | Jul 28 / -1  |
| Lodi              | 2021 | 203   | Jul 21 / -3           | Jul 28 / -6  | Jul 28 / -2  |
| Loganville        | 2021 | 179   | Jul 21 / -1           | Jul 28 / -4  | Aug 4 / -6   |
| Lyndon Station    | 2021 | 173   | Jul 21 / -2           | Jul 28 / -5  | Aug 4 / -8   |
| Manchester        | 2021 | 153   | Jul 21 / -2           | Jul 21 / +2  | Jul 28 / -1  |
| Manitowoc         | 2021 | 39    | Jul 28 / +3           | Aug 4 / +1   | Aug 4 / +6   |
| Markesan          | 2021 | 170   | Jul 21 / -1           | Jul 28 / -4  | Aug 4 / -7   |
| Marshfield        | 2021 | 83    | Jul 21 / +7           | Jul 28 / +5  | Jul 28 / +10 |
| Merrimac          | 2021 | 187   | Jul 21 / -5           | Jul 21 / -1  | Jul 28 / -4  |
| Montello          | 2021 | 87    | Jul 14 / +5           | Jul 21 / +2  | Jul 28 / -1  |
| Newport           | 2021 | 467   | Jul 28 / -8           | Jul 28 / -4  | Aug 4 / -7   |
| Pardeeville N     | 2021 | 106   | Jul 14 / +4           | Jul 21 / +1  | Jul 28 / -2  |
| Pardeeville S     | 2021 | 68    | Jul 14 / +4           | Jul 21 / +1  | Jul 28 / -2  |
| Plain             | 2021 | 74    | Jul 21 / -4           | Jul 28 / -7  | Jul 28 / -3  |
| Prairie du Sac    | 2021 | 150   | Jul 14 / +3           | Jul 14 / +7  | Jul 14 / +12 |
| Princeton         | 2021 | 420   | Jul 21 / -2           | Jul 28 / -5  | Aug 4 / -8   |
| Randolph          | 2021 | 189   | Jul 21 / -1           | Jul 28 / -3  | Jul 28 / +1  |
| Reedsburg S       | 2021 | 45    | Jul 21 / -2           | Jul 28 / -5  | Jul 28 / -1  |
| Ripon             | 2021 | 214   | Jul 21 / -1           | Jul 28 / -4  | Jul 28 / +0  |
| Spring Green      | 2021 | 91    | Jul 21 / -7           | Jul 21 / -2  | Jul 28 / -5  |
| Troy              | 2021 | 132   | Jul 14 / +3           | Jul 21 / +0  | Jul 28 / -3  |
| Waupun            | 2021 | 210   | Jul 21 / -1           | Jul 28 / -4  | Jul 28 / +0  |
| West Baraboo      | 2021 | 36    | Jul 21 / -3           | Jul 28 / -6  | Jul 28 / -2  |
| West Point        | 2021 | 101   | Jul 14 / +3           | Jul 21 / +0  | Jul 28 / -3  |
| Arlington E       | 2022 | 47    | Jul 28 / -4           | Aug 4 / -6   | Aug 4 / -1   |
| Arlington W       | 2022 | 95    | Jul 28 / -4           | Jul 28 / +1  | Aug 4 / -1   |
| Baraboo           | 2022 | 73    | Jul 28 / -3           | Jul 28 / +2  | Aug 4 / -1   |
| Beaver Dam        | 2022 | 45    | Jul 28 / -2           | Aug 4 / -5   | Aug 4 / +0   |
| Crivitz           | 2022 | 320   | Aug 4 / +2            | Aug 18 / -7  | Aug 18 / -1  |
| Durand            | 2022 | 130   | Jul 28 / -5           | Aug 4 / -8   | Aug 11 / -10 |
| East Troy         | 2022 | 231   | Jul 21 / +1           | Jul 28 / -2  | Jul 28 / +3  |
| Fall River        | 2022 | 56    | Jul 28 / -4           | Jul 28 / +0  | Jul 28 / +5  |
| Green Lake        | 2022 | 257   | Jul 28 / +0           | Jul 28 / +5  | Aug 4 / +2   |
| Lake Delton       | 2022 | 265   | Jul 21 / +6           | Jul 28 / +3  | Aug 4 / +1   |
| Lena              | 2022 | 74    | Aug 4 / +2            | Aug 11 / +1  | Aug 18 / -1  |
| Manitowoc         | 2022 | 39    | Aug 4 / +2            | Aug 4 / +6   | Aug 11 / +5  |
| Markesan          | 2022 | 61    | Jul 28 / -1           | Jul 28 / +3  | Aug 4 / +1   |
| Marshfield        | 2022 | 39    | Aug 4 / +1            | Aug 4 / +5   | Aug 4 / +11  |
| Merrimac          | 2022 | 343   | Jul 28 / -5           | Jul 28 / -1  | Aug 4 / -3   |
| Montello E        | 2022 | 168   | Jul 21 / +5           | Jul 28 / +3  | Jul 28 / +7  |
| Montello W        | 2022 | 285   | Jul 21 / +5           | Jul 28 / +3  | Jul 28 / +7  |
| Pardeeville       | 2022 | 88    | Jul 14 / +11          | Jul 21 / +9  | Jul 21 / +13 |
| Plain E           | 2022 | 71    | Jul 28 / -5           | Jul 28 / +0  | Jul 28 / +5  |
| Plain N           | 2022 | 70    | Jul 28 / -5           | Aug 4 / -7   | Aug 4 / -2   |
| Portage N         | 2022 | 437   | Jul 21 / +4           | Jul 28 / +2  | Aug 4 / -1   |
| Portage S         | 2022 | 201   | Jul 28 / -3           | Jul 28 / +2  | Aug 4 / -1   |
| Portage W         | 2022 | 156   | Jul 21 / +5           | Jul 28 / +3  | Aug 4 / +0   |
| Princeton         | 2022 | 365   | Jul 28 / -2           | Jul 28 / +3  | Aug 4 / +0   |
| Randolph          | 2022 | 62    | Jul 28 / -1           | Jul 28 / +3  | Jul 28 / +8  |
| Richland Center   | 2022 | 73    | Aug 4 / -11           | Aug 4 / -6   | Aug 11 / -8  |
| Rio E             | 2022 | 114   | Jul 21 / +3           | Jul 28 / +1  | Jul 28 / +5  |
| Rio W             | 2022 | 168   | Jul 28 / -4           | Jul 28 / +1  | Jul 28 / +5  |
| Ripon             | 2022 | 167   | Aug 4 / -8            | Aug 4 / -3   | Aug 4 / +1   |
| Spring Green      | 2022 | 51    | Jul 21 / +0           | Jul 28 / -3  | Jul 28 / +2  |
| Waupun            | 2022 | 186   | Jul 28 / -2           | Jul 28 / +3  | Aug 4 / +0   |
| Abrams            | 2023 | 29    | Aug 10 / -9           | Aug 10 / -5  | Aug 24 / -14 |
| Arlington         | 2023 | 115   | Jul 27 / -5           | Aug 3 / -8   | Aug 3 / -3   |
| Beaver Dam        | 2023 | 80    | Jul 27 / -4           | Jul 27 / +0  | Aug 3 / -2   |
| Bryant            | 2023 | 52    | Sep 14 / -37          | Sep 14 / -32 | Sep 14 / -26 |
| Buffalo           | 2023 | 320   | Jul 20 / +3           | Aug 3 / -7   | Aug 3 / -3   |
| Cambria           | 2023 | 362   | Jul 27 / -2           | Aug 3 / -6   | Aug 3 / -1   |
| Cameron           | 2023 | 87    | Jul 27 / +0           | Aug 3 / -2   | Aug 10 / -5  |
| Cecil             | 2023 | 57    | Aug 10 / -7           | Aug 10 / -3  | Aug 24 / -12 |
| Columbus          | 2023 | 271   | Jul 20 / +1           | Jul 27 / -2  | Jul 27 / +2  |
| Crivitz           | 2023 | 139   | Aug 10 / -8           | Aug 10 / -3  | Aug 24 / -13 |
| Dorchester        | 2023 | 49    | Jul 27 / +9           | Aug 10 / +0  | Aug 10 / +6  |
| Dunn              | 2023 | 74    | Jul 27 / -7           | Aug 17 / -23 | Aug 17 / -19 |
| Durand            | 2023 | 97    | Jul 20 / +1           | Jul 27 / -2  | Aug 3 / -5   |
| East Troy         | 2023 | 80    | Jul 27 / -6           | Jul 27 / -2  | Aug 3 / -5   |
| Fox Lake N        | 2023 | 260   | Jul 27 / -4           | Aug 3 / -7   | Aug 3 / -2   |
| Fox Lake NE       | 2023 | 51    | Jul 27 / -4           | Aug 3 / -7   | Aug 3 / -2   |
| Grand Marsh       | 2023 | 88    | Jul 20 / +6           | Jul 27 / +3  | Jul 27 / +8  |
| Green Lake        | 2023 | 721   | Jul 27 / -1           | Jul 27 / +2  | Aug 3 / +0   |
| Hancock           | 2023 | 89    | Jul 20 / +8           | Jul 20 / +12 | Aug 3 / +2   |
| Leeds             | 2023 | 74    | Jul 27 / -5           | Jul 27 / -1  | Aug 3 / -3   |
| Lodi              | 2023 | 702   | Jul 20 / +1           | Jul 27 / -2  | Aug 3 / -5   |
| Loganville        | 2023 | 227   | Jul 27 / -4           | Aug 3 / -7   | Aug 3 / -3   |
| Loyal             | 2023 | 82    | Aug 3 / -2            | Aug 10 / -5  | Aug 10 / +0  |
| Manitowoc         | 2023 | 119   | Jul 27 / +6           | Aug 3 / +3   | Aug 3 / +8   |
| Markesan          | 2023 | 715   | Jul 27 / -2           | Aug 3 / -5   | Aug 3 / -1   |
| Marshfield        | 2023 | 46    | Jul 27 / +5           | Jul 27 / +9  | Aug 10 / +0  |
| Montello          | 2023 | 514   | Jul 20 / +3           | Jul 27 / +0  | Aug 3 / -2   |
| Pardeeville       | 2023 | 256   | Jul 20 / +2           | Jul 27 / -1  | Aug 3 / -4   |
| Plain             | 2023 | 236   | Jul 27 / -7           | Aug 3 / -10  | Aug 3 / -6   |
| Portage N         | 2023 | 807   | Jul 27 / -6           | Jul 27 / -2  | Aug 3 / -5   |
| Portage S         | 2023 | 353   | Jul 27 / -6           | Jul 27 / -2  | Aug 3 / -5   |
| Princeton         | 2023 | 850   | Jul 27 / -3           | Jul 27 / +1  | Aug 10 / -9  |
| Randolph          | 2023 | 264   | Jul 27 / -3           | Jul 27 / +1  | Aug 3 / -1   |
| Ripon             | 2023 | 220   | Jul 27 / -2           | Jul 27 / +1  | Aug 3 / -1   |
| Sauk City N       | 2023 | 153   | Jul 20 / +0           | Jul 27 / -3  | Aug 3 / -6   |
| Sauk City NE      | 2023 | 107   | Jul 20 / +0           | Jul 27 / -3  | Aug 3 / -6   |
| Sauk City NW      | 2023 | 48    | Jul 27 / -7           | Aug 3 / -10  | Aug 3 / -6   |
| Spring Green      | 2023 | 91    | Jul 20 / -3           | Jul 20 / +2  | Jul 27 / -1  |
| Waupun            | 2023 | 377   | Jul 27 / -4           | Jul 27 / +0  | Aug 3 / -2   |
| Wausau N          | 2023 | 48    | Aug 3 / +2            | Aug 10 / +0  | Aug 10 / +6  |
| Almond            | 2024 | 228   | Jul 25 / +0           | Aug 1 / -2   | Aug 8 / -5   |
| Argyle            | 2024 | 551   | Jul 18 / -7           | Jul 25 / -10 | Jul 25 / -6  |
| Arlington         | 2024 | 110   | Jul 25 / -9           | Jul 25 / -4  | Aug 1 / -6   |
| Beaver Dam        | 2024 | 89    | Jul 25 / -7           | Jul 25 / -3  | Aug 1 / -5   |
| Cameron           | 2024 | 243   | Aug 1 / -5            | Aug 1 / -1   | Aug 1 / +3   |
| Chase             | 2024 | 606   | Aug 1 / -5            | Aug 1 / -1   | Aug 8 / -4   |
| Cobb              | 2024 | 50    | Jul 18 / -2           | Jul 25 / -4  | Jul 25 / +1  |
| Cottage Grove     | 2024 | 51    | Jul 18 / -4           | Jul 18 / +0  | Jul 18 / +5  |
| Dodgeville        | 2024 | 103   | Jul 25 / -8           | Aug 1 / -10  | Aug 1 / -5   |
| Durand            | 2024 | 529   | Jul 25 / -6           | Aug 1 / -8   | Aug 8 / -11  |
| East Troy         | 2024 | 107   | Jul 18 / -4           | Jul 18 / +0  | Jul 18 / +5  |
| Eau Claire        | 2024 | 392   | Aug 1 / -12           | Aug 1 / -8   | Aug 1 / -4   |
| Ettrick           | 2024 | 190   | Aug 1 / -12           | Aug 1 / -7   | Aug 8 / -10  |
| Evansville        | 2024 | 111   | Jul 18 / -6           | Jul 18 / -2  | Jul 25 / -4  |
| Fall City Prairie | 2024 | 612   | Jul 25 / -2           | Jul 25 / +2  | Jul 25 / +6  |
| Grand Marsh N     | 2024 | 75    | Jul 25 / -3           | Aug 1 / -5   | Aug 8 / -8   |
| Grand Marsh S     | 2024 | 665   | Jul 18 / +2           | Jul 18 / +7  | Jul 25 / +5  |
| Hancock           | 2024 | 236   | Jul 18 / +7           | Jul 25 / +5  | Aug 1 / +2   |
| Hollandale        | 2024 | 58    | Jul 25 / -13          | Jul 25 / -9  | Jul 25 / -4  |
| Janesville C      | 2024 | 59    | Jul 18 / -8           | Jul 18 / -4  | Jul 18 / +1  |
| Janesville R      | 2024 | 61    | Jul 18 / -8           | Jul 25 / -11 | Jul 25 / -6  |
| Little River      | 2024 | 811   | Aug 1 / -1            | Aug 1 / +3   | Aug 1 / +9   |
| Lodi H            | 2024 | 89    | Jul 18 / -5           | Jul 25 / -8  | Aug 1 / -10  |
| Lodi O            | 2024 | 40    | Jul 18 / -5           | Jul 25 / -8  | Aug 1 / -10  |
| Lodi R            | 2024 | 132   | Jul 18 / -5           | Jul 25 / -8  | Jul 25 / -3  |
| Loganville        | 2024 | 265   | Jul 25 / -9           | Jul 25 / -4  | Aug 1 / -6   |
| Lone Rock         | 2024 | 61    | Jul 18 / -5           | Jul 25 / -8  | Jul 25 / -3  |
| Lowell            | 2024 | 87    | Jul 25 / -10          | Jul 25 / -5  | Aug 8 / -15  |
| Lyndon Station    | 2024 | 406   | Jul 25 / -8           | Jul 25 / -3  | Aug 1 / -6   |
| Marshfield        | 2024 | 163   | Jul 25 / +5           | Aug 1 / +2   | Aug 1 / +7   |
| Mountain          | 2024 | 555   | Jul 25 / +6           | Aug 1 / +3   | Aug 8 / +1   |
| New Glarus E      | 2024 | 414   | Jul 11 / +2           | Jul 18 / -1  | Jul 18 / +4  |
| New Glarus W      | 2024 | 591   | Jul 18 / -5           | Jul 25 / -8  | Jul 25 / -3  |
| Oakfield          | 2024 | 26    | Jul 4 / +14           | Jul 25 / -3  | Aug 1 / -5   |
| Oregon            | 2024 | 361   | Jul 18 / -5           | Jul 25 / -8  | Jul 25 / -3  |
| Pardeeville       | 2024 | 287   | Jul 18 / -2           | Jul 25 / -4  | Aug 1 / -7   |
| Ripon             | 2024 | 205   | Aug 1 / -13           | Aug 1 / -9   | Aug 1 / -4   |
| Rochester         | 2024 | 86    | Jul 11 / +2           | Jul 18 / -1  | Jul 25 / -3  |
| Rusk              | 2024 | 269   | Aug 1 / -9            | Aug 1 / -5   | Aug 1 / -1   |
| Sextonville       | 2024 | 129   | Jul 18 / -5           | Jul 25 / -8  | Aug 1 / -10  |
| Sheboygan         | 2024 | 266   | Jul 18 / +9           | Jul 25 / +6  | Aug 1 / +3   |
| Shullsburg        | 2024 | 31    | Jul 4 / +8            | Jul 18 / -2  | Jul 18 / +3  |
| Springville       | 2024 | 392   | Jul 18 / +1           | Jul 18 / +6  | Jul 25 / +4  |
| Stephenson        | 2024 | 1,839 | Aug 1 / -1            | Aug 8 / -4   | Aug 8 / +2   |
| Stockton          | 2024 | 345   | Aug 8 / -13           | Aug 8 / -9   | Aug 8 / -5   |
| Suring            | 2024 | 338   | Jul 25 / +5           | Aug 1 / +2   | Aug 8 / +0   |
| Taylor            | 2024 | 1,065 | Jul 25 / -2           | Jul 25 / +2  | Aug 1 / -1   |
| Verona            | 2024 | 169   | Jul 18 / -4           | Jul 18 / +0  | Jul 25 / -2  |
| Waupun            | 2024 | 134   | Jul 25 / -7           | Jul 25 / -3  | Aug 1 / -5   |
| Wausau E          | 2024 | 148   | Aug 1 / -1            | Aug 1 / +3   | Aug 8 / +2   |
| Wausau N          | 2024 | 123   | Aug 1 / +1            | Aug 1 / +5   | Aug 1 / +11  |
| Wisconsin Dells   | 2024 | 448   | Jul 18 / -1           | Aug 1 / -10  | Aug 1 / -5   |
| Wonewoc           | 2024 | 265   | Jul 25 / -6           | Aug 1 / -8   | Aug 1 / -4   |
| Arlington         | 2025 | 58    | Jul 31 / -11          | Jul 31 / -7  | Aug 7 / -10  |
| Baraboo           | 2025 | 26    | Jul 31 / -13          | Jul 31 / -9  | Jul 31 / -5  |
| Brodhead          | 2025 | 41    | Jul 17 / -3           | Jul 17 / +2  | Jul 24 / -1  |
| Bryant            | 2025 | 98    | Aug 7 / +4            | Aug 14 / +1  | Aug 14 / +7  |
| Cambria           | 2025 | 112   | Jul 24 / -1           | Jul 31 / -4  | Jul 31 / +0  |
| Cameron           | 2025 | 866   | Aug 7 / -11           | Aug 7 / -7   | Aug 14 / -8  |
| Chetek            | 2025 | 340   | Jul 31 / -3           | Aug 7 / -6   | Aug 7 / -1   |
| Clinton N         | 2025 | 96    | Jul 24 / -7           | Jul 31 / -9  | Jul 31 / -5  |
| Crivitz           | 2025 | 93    | Aug 7 / -2            | Aug 21 / -12 | Aug 21 / -7  |
| Delavan           | 2025 | 25    | Jul 10 / +9           | Jul 24 / -1  | Aug 7 / -11  |
| Durand            | 2025 | 212   | Jul 31 / -10          | Jul 31 / -6  | Jul 31 / -2  |
| Eagle Point       | 2025 | 343   | Jul 31 / -5           | Jul 31 / -2  | Aug 7 / -3   |
| Ettrick           | 2025 | 48    | Jul 31 / -11          | Jul 31 / -7  | Aug 7 / -10  |
| Fredonia          | 2025 | 77    | Jul 31 / -3           | Aug 7 / -5   | Aug 7 / +0   |
| Grand Chute       | 2025 | 37    | Jul 31 / -6           | Aug 7 / -9   | Aug 7 / -4   |
| Grand Marsh       | 2025 | 95    | Jul 31 / -8           | Jul 31 / -4  | Aug 7 / -6   |
| Greenleaf         | 2025 | 58    | Aug 7 / -10           | Aug 7 / -5   | Aug 7 / +0   |
| Gresham           | 2025 | 144   | Jul 31 / +0           | Aug 7 / -1   | Aug 14 / -4  |
| Hancock           | 2025 | 80    | Jul 31 / -4           | Jul 31 / +0  | Aug 7 / -1   |
| Hillsboro         | 2025 | 29    | Aug 7 / -16           | Aug 7 / -12  | Aug 7 / -8   |
| Hustler           | 2025 | 33    | Jul 31 / -9           | Jul 31 / -5  | Jul 31 / -1  |
| Janesville N      | 2025 | 37    | Jul 24 / -7           | Jul 24 / -2  | Jul 31 / -5  |
| Janesville S      | 2025 | 106   | Jul 24 / -7           | Jul 24 / -2  | Jul 31 / -5  |
| Lake Mills        | 2025 | 425   | Jul 24 / -6           | Jul 24 / -2  | Jul 31 / -5  |
| Lancaster 1       | 2025 | 88    | Jul 17 / -3           | Jul 24 / -5  | Jul 31 / -8  |
| Lancaster 2       | 2025 | 45    | Jul 3 / +11           | Jul 24 / -5  | Aug 7 / -15  |
| Lemonweir         | 2025 | 156   | Jul 31 / -11          | Jul 31 / -7  | Jul 31 / -3  |
| Leroy             | 2025 | 151   | Jul 31 / -5           | Aug 7 / -8   | Aug 7 / -3   |
| Lodi L            | 2025 | 44    | Jul 24 / -8           | Jul 31 / -10 | Jul 31 / -6  |
| Lodi M            | 2025 | 42    | Jul 31 / -15          | Jul 31 / -10 | Jul 31 / -6  |
| Lone Rock         | 2025 | 27    | Jul 24 / -9           | Jul 31 / -12 | Jul 31 / -7  |
| Lyndon Station    | 2025 | 55    | Jul 31 / -12          | Jul 31 / -8  | Jul 31 / -4  |
| Marshfield        | 2025 | 48    | Jul 24 / +6           | Jul 31 / +4  | Jul 31 / +9  |
| Mauston           | 2025 | 67    | Jul 31 / -10          | Jul 31 / -7  | Aug 7 / -10  |
| Monroe            | 2025 | 53    | Jul 24 / -10          | Jul 24 / -5  | Jul 31 / -8  |
| Mountain          | 2025 | 299   | Aug 7 / -4            | Aug 7 / +1   | Aug 14 / -2  |
| Muscoda           | 2025 | 74    | Jul 24 / -10          | Jul 24 / -5  | Jul 24 / -1  |
| New Auburn NE     | 2025 | 209   | Jul 31 / -4           | Aug 7 / -7   | Aug 7 / -2   |
| Oconto            | 2025 | 65    | Jul 31 / +5           | Aug 7 / +2   | Aug 7 / +6   |
| Oostburg          | 2025 | 95    | Jul 31 / +1           | Aug 7 / -1   | Aug 14 / -4  |
| Pardeeville       | 2025 | 168   | Jul 24 / -4           | Jul 31 / -7  | Jul 31 / -3  |
| Portage W         | 2025 | 167   | Jul 24 / -5           | Jul 31 / -8  | Jul 31 / -4  |
| Pulaski           | 2025 | 159   | Jul 31 / +0           | Jul 31 / +5  | Aug 7 / +2   |
| Reedsburg         | 2025 | 213   | Jul 24 / -5           | Jul 31 / -8  | Aug 7 / -11  |
| Reedsburg N       | 2025 | 31    | Jul 31 / -12          | Jul 31 / -8  | Jul 31 / -4  |
| Rochester         | 2025 | 87    | Jul 24 / -4           | Jul 24 / +0  | Jul 24 / +4  |
| Sharon            | 2025 | 128   | Jul 24 / -6           | Jul 31 / -9  | Jul 31 / -5  |
| Sheboygan         | 2025 | 159   | Jul 31 / +4           | Aug 7 / +1   | Aug 14 / -2  |
| Sherwood          | 2025 | 77    | Aug 7 / -12           | Aug 14 / -15 | Aug 21 / -17 |
| Spring Green      | 2025 | 121   | Jul 17 / -2           | Jul 24 / -5  | Jul 31 / -8  |
| St Nazianz        | 2025 | 85    | Jul 31 / +0           | Aug 14 / -9  | Aug 21 / -12 |
| Stevens Point     | 2025 | 43    | Jun 26 / +31          | Jul 10 / +21 | Jul 31 / +5  |
| Strickland        | 2025 | 100   | Aug 7 / -10           | Aug 7 / -5   | Aug 14 / -7  |
| Sturgeon Bay      | 2025 | 327   | Jul 31 / +6           | Aug 7 / +3   | Aug 14 / +0  |
| Sumner            | 2025 | 134   | Aug 7 / -8            | Aug 7 / -2   | Aug 7 / +2   |
| Sun Prairie E     | 2025 | 70    | Jul 24 / -5           | Jul 31 / -8  | Aug 7 / -11  |
| Sun Prairie N     | 2025 | 61    | Jul 24 / -5           | Jul 31 / -8  | Jul 31 / -4  |
| Suring            | 2025 | 32    | Jul 31 / +2           | Jul 31 / +7  | Aug 21 / -10 |
| Watertown W       | 2025 | 134   | Jul 24 / -5           | Jul 31 / -8  | Jul 31 / -4  |
| Waupun            | 2025 | 147   | Jul 31 / -8           | Jul 31 / -4  | Aug 7 / -6   |
| Wausau            | 2025 | 139   | Jul 31 / +0           | Jul 31 / +5  | Aug 7 / +2   |
| Wausau E          | 2025 | 38    | Jul 31 / +3           | Aug 7 / +1   | Aug 14 / -2  |
| West Bloomfield   | 2025 | 73    | Jul 31 / -7           | Jul 31 / -3  | Aug 7 / -5   |
| Almond            | 2026 | 95    | Jul 15 / +8           | Jul 22 / +6  | Jul 22 / +10 |
| Amherst           | 2026 | 56    | Jul 29 / -4           | Jul 29 / +0  | Aug 12 / -9  |
| Arlington         | 2026 | 28    | Jul 22 / -5           | Jul 29 / -8  | Jul 29 / -3  |
| Beaver Dam        | 2026 | 35    | Jul 22 / -4           | Jul 29 / -6  | Jul 29 / -2  |
| Beloit W          | 2026 | 39    | Jul 22 / -11          | Jul 22 / -7  | Jul 22 / -3  |
| Boltonville       | 2026 | 446   | Jul 22 / -2           | Jul 29 / -4  | Jul 29 / +1  |
| Brodhead          | 2026 | 72    | Jul 8 / +3            | Jul 15 / +0  | Jul 22 / -3  |
| Calumetville      | 2026 | 54    | Jul 29 / -7           | Aug 5 / -10  | Aug 12 / -12 |
| Cambria           | 2026 | 281   | Jul 22 / -2           | Jul 29 / -4  | Jul 29 / +0  |
| Cameron           | 2026 | 188   | Jul 29 / -5           | Jul 29 / -1  | Aug 5 / -4   |
| Cashton           | 2026 | 131   | Jul 15 / +3           | Jul 29 / -7  | Jul 29 / -2  |
| Chetek            | 2026 | 468   | Jul 22 / +3           | Jul 29 / +0  | Aug 5 / -3   |
| Clinton E         | 2026 | 169   | Jul 15 / -3           | Jul 22 / -6  | Jul 22 / -2  |
| Coloma            | 2026 | 82    | Jul 15 / +6           | Jul 22 / +4  | Jul 22 / +8  |
| Crivitz           | 2026 | 216   | Aug 5 / -5            | Aug 5 / +0   | Aug 19 / -9  |
| Darien S          | 2026 | 91    | Jul 15 / -3           | Jul 22 / -6  | Jul 22 / -1  |
| Delavan           | 2026 | 60    | Jul 22 / -9           | Jul 22 / -5  | Jul 29 / -7  |
| Durand            | 2026 | 172   | Jul 29 / -13          | Jul 29 / -10 | Jul 29 / -5  |
| East Troy         | 2026 | 94    | Jul 22 / -8           | Jul 22 / -4  | Jul 22 / +0  |
| Fort Atkinson     | 2026 | 206   | Jul 15 / -1           | Jul 22 / -4  | Jul 22 / +0  |
| Fredonia          | 2026 | 64    | Jul 29 / -7           | Jul 29 / -2  | Aug 5 / -5   |
| Gillett           | 2026 | 150   | Jul 29 / -1           | Jul 29 / +4  | Jul 29 / +9  |
| Gotham            | 2026 | 29    | Jul 15 / -2           | Jul 22 / -5  | Jul 22 / -1  |
| Grand Marsh N     | 2026 | 78    | Jul 22 / -2           | Jul 22 / +4  | Aug 5 / -6   |
| Grand Marsh S     | 2026 | 138   | Jul 15 / +3           | Jul 22 / +1  | Jul 22 / +6  |
| Greenleaf         | 2026 | 165   | Jul 22 / +3           | Jul 29 / +0  | Aug 5 / -2   |
| Gresham           | 2026 | 78    | Jul 29 / -2           | Aug 12 / -12 | Aug 12 / -7  |
| Hancock           | 2026 | 70    | Jul 15 / +8           | Jul 22 / +5  | Jul 22 / +10 |
| Janesville N      | 2026 | 68    | Jul 15 / -2           | Jul 15 / +2  | Jul 22 / -1  |
| Janesville S      | 2026 | 55    | Jul 15 / -3           | Jul 15 / +1  | Jul 22 / -2  |
| Keyeser           | 2026 | 173   | Jul 22 / -5           | Jul 22 / -1  | Jul 29 / -3  |
| Lake Mills        | 2026 | 635   | Jul 15 / -1           | Jul 22 / -4  | Jul 29 / -7  |
| Lancaster N       | 2026 | 166   | Jul 15 / -5           | Jul 15 / -1  | Jul 22 / -4  |
| Lancaster S       | 2026 | 69    | Jul 8 / +2            | Jul 15 / -1  | Jul 22 / -4  |
| Lena              | 2026 | 113   | Jul 29 / +3           | Aug 5 / +0   | Aug 12 / -2  |
| Leroy             | 2026 | 62    | Jul 29 / -9           | Jul 29 / -4  | Aug 5 / -7   |
| Lodi              | 2026 | 58    | Jul 22 / -6           | Jul 22 / -3  | Jul 29 / -4  |
| Marshall          | 2026 | 37    | Jul 29 / -14          | Jul 29 / -10 | Jul 29 / -5  |
| Monroe            | 2026 | 32    | Jul 22 / -12          | Jul 22 / -8  | Jul 22 / -4  |
| Mosinee           | 2026 | 99    | Jul 29 / -3           | Jul 29 / +1  | Aug 12 / -8  |
| Mountain          | 2026 | 632   | Jul 22 / +7           | Jul 29 / +5  | Aug 5 / +3   |
| Mt. Horeb S       | 2026 | 84    | Jul 22 / -8           | Jul 22 / -4  | Jul 22 / +0  |
| Omro              | 2026 | 36    | Jul 22 / -2           | Jul 22 / +3  | Jul 22 / +7  |
| Oostburg          | 2026 | 248   | Jul 8 / +19           | Jul 15 / +17 | Jul 22 / +15 |
| Pardeeville       | 2026 | 163   | Jul 22 / -5           | Jul 22 / -1  | Jul 29 / -3  |
| Patch Grove       | 2026 | 29    | Jul 15 / -4           | Jul 29 / -14 | Jul 29 / -10 |
| Portage W         | 2026 | 110   | Jul 15 / +1           | Jul 22 / -2  | Jul 22 / +4  |
| Reedsburg         | 2026 | 44    | Jul 15 / +1           | Jul 22 / -2  | Jul 29 / -4  |
| Seymour           | 2026 | 30    | Jul 29 / -5           | Aug 12 / -15 | Aug 12 / -10 |
| Sheboygan         | 2026 | 66    | Jul 8 / +22           | Jul 8 / +27  | Jul 15 / +24 |
| Spring Green      | 2026 | 116   | Jul 15 / -3           | Jul 15 / +1  | Jul 22 / -2  |
| St. Nazianz       | 2026 | 31    | Jul 22 / +4           | Jul 22 / +8  | Jul 29 / +6  |
| Sturgeon Bay      | 2026 | 310   | Jul 29 / +5           | Aug 5 / +2   | Aug 5 / +7   |
| Sun Prairie N     | 2026 | 52    | Jul 22 / -6           | Jul 29 / -9  | Jul 29 / -4  |
| Suring            | 2026 | 149   | Jul 29 / -1           | Jul 29 / +4  | Aug 5 / +2   |
| Viroqua           | 2026 | 66    | Jul 15 / +2           | Jul 22 / +0  | Jul 29 / -2  |
| Watertown         | 2026 | 251   | Jul 22 / -8           | Jul 22 / -4  | Jul 29 / -7  |
| Wausau E          | 2026 | 68    | Jul 29 / +0           | Aug 5 / -3   | Aug 5 / +2   |
| Wausau N          | 2026 | 96    | Jul 29 / +1           | Aug 5 / -2   | Aug 5 / +3   |
| Weston            | 2026 | 284   | Jul 22 / -5           | Jul 29 / -8  | Jul 29 / -3  |
| Westpoint         | 2026 | 47    | Jul 22 / -7           | Jul 22 / -3  | Jul 29 / -5  |
