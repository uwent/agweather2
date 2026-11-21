# Alfalfa weevil: Harcourt's dated peaks, NEWA on the same weather, and typical dates in Wisconsin

Written by `scripts/check_alfalfa_weevil.py`. Ours: simple average degree days above 48 °F from January 1, egg hatch half done at 280, larvae cocooning half done at 600, adults half out at 815 (NEWA's table). Station days are NEWA's on the local clock; the archive's are CST.

## 1. Harcourt 1981's dated peaks, on Open-Meteo's historical weather

Days from the observed peak (Table II, Bay of Quinte; Table I, Guelph's peak hatch) to the day each method's total reaches the stage's peak: Harcourt's own (single sine above 9 °C from April 1, his °C·d), and NEWA's (simple average above 48 °F from January 1, NEWA's table; ours is the same rule, and our curves pass half of egg hatch, cocooning and adult emergence at NEWA's totals). Weather: Open-Meteo's historical daily max and min (ERA5) at the Smithfield farm and Guelph, not the stations Harcourt used. Harcourt's own predicted dates, on his stations, are in his Table II, within 2 days of the observed.

| Year | Stage           | Observed | Harcourt's method | NEWA's |
| ---- | --------------- | -------- | ----------------- | ------ |
| 1977 | Hatch           | May 23   | +1                | +3     |
| 1977 | Instar 1        | May 25   | +1                | +3     |
| 1977 | Instar 2        | May 29   | +2                | +4     |
| 1977 | Instar 3        | Jun 5    | +1                | +5     |
| 1977 | Instar 4        | Jun 11   | +2                | +3     |
| 1977 | Cocooning       | Jun 14   | +2                | +3     |
| 1977 | Pupa            | Jun 21   | +2                | +3     |
| 1977 | Adult emergence | Jun 27   | +0                | +1     |
| 1978 | Hatch           | May 30   | +1                | +3     |
| 1978 | Instar 1        | Jun 1    | +2                | +3     |
| 1978 | Instar 2        | Jun 6    | +3                | +5     |
| 1978 | Instar 3        | Jun 12   | +3                | +5     |
| 1978 | Instar 4        | Jun 18   | +2                | +2     |
| 1978 | Cocooning       | Jun 21   | +2                | +2     |
| 1978 | Pupa            | Jun 27   | +2                | +2     |
| 1978 | Adult emergence | Jul 3    | +0                | +1     |
| 1979 | Hatch           | May 29   | +3                | +4     |
| 1979 | Instar 1        | Jun 1    | +3                | +3     |
| 1979 | Instar 2        | Jun 7    | +1                | +2     |
| 1979 | Instar 3        | Jun 11   | +2                | +3     |
| 1979 | Instar 4        | Jun 16   | +1                | +2     |
| 1979 | Cocooning       | Jun 19   | +1                | +2     |
| 1979 | Pupa            | Jun 28   | +0                | +1     |
| 1979 | Adult emergence | Jul 5    | -2                | -2     |
| 1980 | Hatch           | May 27   | +3                | +4     |
| 1980 | Instar 1        | May 30   | +2                | +4     |
| 1980 | Instar 2        | Jun 5    | +2                | +8     |
| 1980 | Instar 3        | Jun 12   | +4                | +7     |
| 1980 | Instar 4        | Jun 20   | +2                | +4     |
| 1980 | Cocooning       | Jun 23   | +2                | +3     |
| 1980 | Pupa            | Jun 30   | +1                | +2     |
| 1980 | Adult emergence | Jul 5    | +0                | +2     |
| 1977 | Hatch (Guelph)  | May 18   | +1                | +3     |
| 1978 | Hatch (Guelph)  | May 31   | -1                | +0     |
| 1979 | Hatch (Guelph)  | Jun 2    | -4                | +0     |
| 1980 | Hatch (Guelph)  | May 27   | -1                | +3     |

Days late (+) or early (−), all 36 dated peaks:

- Harcourt's method: median +2, mean +1.3, mean absolute 1.7, from -4 to +4
- NEWA's rule (ours): median +3, mean +2.9, mean absolute 3.0, from -2 to +8

## 2. NEWA's model against ours, on the station's hours and the archive's

Days each total reaches NEWA's egg hatch (280), cocooning (600) and adult emergence (815): NEWA's (its days and degree days) / ours on the same station days / ours on the archive at the station's cell; and the Crop Risk Tool's old table (single sine 48.2/86 °F: egg hatch 300, pupae 595, adults 815) on the station days. Our curves pass half of hatch, of larvae cocooned and of adults emerged at NEWA's totals.

| Station                         | Year | Egg hatch NEWA / station / grid / old | Cocooning NEWA / station / grid / old | Adults NEWA / station / grid / old |
| ------------------------------- | ---- | ------------------------------------- | ------------------------------------- | ---------------------------------- |
| Baileys Harbor                  | 2024 | Jun 5 / Jun 5 / Jun 5 / Jun 1         | Jun 27 / Jun 27 / Jun 27 / Jun 22     | Jul 10 / Jul 10 / Jul 10 / Jul 6   |
| Baileys Harbor                  | 2025 | Jun 17 / Jun 17 / Jun 15 / Jun 11     | Jul 3 / Jul 3 / Jul 2 / Jun 30        | Jul 14 / Jul 14 / Jul 14 / Jul 12  |
| Belgium                         | 2024 | May 20 / May 20 / May 19 / May 18     | Jun 13 / Jun 13 / Jun 12 / Jun 9      | Jun 22 / Jun 22 / Jun 22 / Jun 20  |
| Belgium                         | 2025 | Jun 6 / Jun 6 / Jun 5 / Jun 3         | Jun 23 / Jun 23 / Jun 22 / Jun 20     | Jul 2 / Jul 2 / Jun 30 / Jun 29    |
| Belmont                         | 2024 | May 9 / May 9 / May 12 / May 4        | May 30 / May 30 / Jun 3 / May 23      | Jun 11 / Jun 11 / Jun 14 / Jun 6   |
| Belmont                         | 2025 | May 13 / May 13 / May 15 / May 10     | Jun 6 / Jun 6 / Jun 10 / Jun 2        | Jun 16 / Jun 16 / Jun 20 / Jun 13  |
| Brighton                        | 2024 | May 8 / May 8 / May 8 / May 5         | May 30 / May 30 / May 31 / May 25     | Jun 12 / Jun 12 / Jun 12 / Jun 8   |
| Brighton                        | 2025 | May 17 / May 17 / May 17 / May 14     | Jun 14 / Jun 14 / Jun 14 / Jun 10     | Jun 22 / Jun 22 / Jun 22 / Jun 20  |
| Brooklyn                        | 2024 | May 9 / May 9 / May 10 / May 6        | May 31 / May 31 / Jun 1 / May 26      | Jun 12 / Jun 12 / Jun 13 / Jun 9   |
| Brooklyn                        | 2025 | May 14 / May 14 / May 15 / May 12     | Jun 10 / Jun 10 / Jun 11 / Jun 5      | Jun 19 / Jun 19 / Jun 20 / Jun 17  |
| Brodhead                        | 2024 | May 7 / May 7 / May 8 / May 3         | May 27 / May 27 / May 29 / May 23     | Jun 9 / Jun 9 / Jun 10 / Jun 5     |
| Brodhead                        | 2025 | May 14 / May 14 / May 14 / May 10     | Jun 8 / Jun 8 / Jun 10 / Jun 3        | Jun 18 / Jun 18 / Jun 19 / Jun 15  |
| Burlington (Munster)            | 2024 | May 11 / May 11 / May 8 / May 6       | Jun 2 / Jun 2 / May 31 / May 27       | Jun 13 / Jun 13 / Jun 12 / Jun 10  |
| Burlington (Munster)            | 2025 | May 17 / May 17 / May 17 / May 14     | Jun 14 / Jun 14 / Jun 14 / Jun 8      | Jun 22 / Jun 22 / Jun 22 / Jun 19  |
| Chippewa Falls                  | 2024 | May 18 / May 18 / May 20 / May 15     | Jun 10 / Jun 10 / Jun 11 / Jun 5      | Jun 21 / Jun 21 / Jun 22 / Jun 18  |
| Chippewa Falls                  | 2025 | May 15 / May 15 / May 15 / May 13     | Jun 15 / Jun 15 / Jun 15 / Jun 8      | Jun 23 / Jun 23 / Jun 23 / Jun 21  |
| Colgate                         | 2024 | May 16 / May 16 / May 17 / May 13     | Jun 7 / Jun 7 / Jun 8 / Jun 4         | Jun 18 / Jun 18 / Jun 18 / Jun 17  |
| Colgate                         | 2025 | May 31 / May 31 / May 30 / May 18     | Jun 20 / Jun 20 / Jun 18 / Jun 16     | Jun 28 / Jun 28 / Jun 26 / Jun 24  |
| Eau Claire                      | 2024 | May 21 / May 21 / May 18 / May 16     | Jun 13 / Jun 13 / Jun 10 / Jun 5      | Jun 24 / Jun 24 / Jun 21 / Jun 19  |
| Eau Claire                      | 2025 | May 16 / May 16 / May 15 / May 14     | Jun 17 / Jun 17 / Jun 13 / Jun 10     | Jun 24 / Jun 24 / Jun 22 / Jun 22  |
| Eau Clair (Ferguson's Orchards) | 2024 | May 19 / May 19 / May 19 / May 15     | Jun 11 / Jun 11 / Jun 10 / Jun 4      | Jun 21 / Jun 21 / Jun 21 / Jun 17  |
| Eau Clair (Ferguson's Orchards) | 2025 | May 15 / May 15 / May 15 / May 14     | Jun 15 / Jun 15 / Jun 14 / Jun 9      | Jun 23 / Jun 23 / Jun 22 / Jun 21  |
| Edgar                           | 2024 | May 30 / May 30 / May 30 / May 23     | Jun 20 / Jun 20 / Jun 21 / Jun 16     | Jul 4 / Jul 4 / Jul 4 / Jun 28     |
| Edgar                           | 2025 | Jun 4 / Jun 4 / Jun 4 / May 29        | Jun 23 / Jun 23 / Jun 24 / Jun 20     | Jul 4 / Jul 4 / Jul 4 / Jun 30     |
| Fort Atkinson (Warm Belly Farm) | 2024 | May 10 / May 10 / May 10 / May 5      | May 31 / May 31 / Jun 1 / May 26      | Jun 12 / Jun 12 / Jun 13 / Jun 9   |
| Fort Atkinson (Warm Belly Farm) | 2025 | May 15 / May 15 / May 15 / May 12     | Jun 11 / Jun 11 / Jun 11 / Jun 5      | Jun 20 / Jun 20 / Jun 21 / Jun 17  |
| Galesville (Ferguson)           | 2025 | May 14 / May 14 / May 14 / May 11     | Jun 10 / Jun 10 / Jun 11 / Jun 5      | Jun 20 / Jun 20 / Jun 21 / Jun 17  |
| Galesville                      | 2024 | May 17 / May 17 / May 16 / May 11     | Jun 7 / Jun 7 / Jun 6 / Jun 1         | Jun 18 / Jun 18 / Jun 18 / Jun 14  |
| Galesville                      | 2025 | May 15 / May 15 / May 13 / May 12     | Jun 12 / Jun 12 / Jun 10 / Jun 6      | Jun 21 / Jun 21 / Jun 20 / Jun 18  |
| Gays Mills                      | 2024 | May 13 / May 13 / May 13 / May 9      | Jun 4 / Jun 4 / Jun 3 / May 31        | Jun 16 / Jun 16 / Jun 15 / Jun 13  |
| Gays Mills                      | 2025 | May 14 / May 14 / May 14 / May 12     | Jun 10 / Jun 10 / Jun 10 / Jun 6      | Jun 20 / Jun 20 / Jun 20 / Jun 18  |
| Genoa City                      | 2024 | May 7 / May 7 / May 8 / May 4         | May 27 / May 27 / Jun 1 / May 24      | Jun 9 / Jun 9 / Jun 12 / Jun 6     |
| Genoa City                      | 2025 | May 16 / May 16 / May 16 / May 14     | Jun 14 / Jun 14 / Jun 14 / Jun 9      | Jun 22 / Jun 22 / Jun 22 / Jun 20  |
| Gays Mills (Sandcreek)          | 2024 | May 12 / May 12 / May 14 / May 8      | Jun 3 / Jun 3 / Jun 4 / May 30        | Jun 15 / Jun 15 / Jun 16 / Jun 12  |
| Gays Mills (Sandcreek)          | 2025 | May 13 / May 13 / May 15 / May 11     | Jun 10 / Jun 10 / Jun 11 / Jun 5      | Jun 20 / Jun 20 / Jun 21 / Jun 17  |
| Malone                          | 2024 | May 17 / May 17 / May 17 / May 14     | Jun 6 / Jun 6 / Jun 7 / Jun 4         | Jun 17 / Jun 17 / Jun 18 / Jun 16  |
| Malone                          | 2025 | May 29 / May 29 / Jun 2 / May 25      | Jun 18 / Jun 18 / Jun 20 / Jun 14     | Jun 26 / Jun 26 / Jun 29 / Jun 23  |
| Mauston (Northwoods)            | 2024 | May 15 / May 15 / May 17 / May 10     | Jun 5 / Jun 5 / Jun 8 / May 31        | Jun 16 / Jun 16 / Jun 18 / Jun 13  |
| Mauston (Northwoods)            | 2025 | May 16 / May 16 / May 23 / May 13     | Jun 13 / Jun 13 / Jun 15 / Jun 8      | Jun 22 / Jun 22 / Jun 23 / Jun 19  |
| Mequon (Barthel)                | 2024 | May 18 / May 18 / May 16 / May 14     | Jun 10 / Jun 10 / Jun 7 / Jun 6       | Jun 19 / Jun 19 / Jun 18 / Jun 18  |
| Mequon (Barthel)                | 2025 | Jun 4 / Jun 4 / Jun 2 / May 29        | Jun 22 / Jun 22 / Jun 20 / Jun 18     | Jun 30 / Jun 30 / Jun 27 / Jun 27  |
| Merrill (Helenes)               | 2024 | May 30 / May 30 / May 30 / May 21     | Jun 19 / Jun 19 / Jun 20 / Jun 14     | Jul 3 / Jul 3 / Jul 4 / Jun 25     |
| Merrill (Helenes)               | 2025 | Jun 4 / Jun 4 / Jun 4 / May 30        | Jun 24 / Jun 24 / Jun 24 / Jun 21     | Jul 5 / Jul 5 / Jul 4 / Jul 1      |
| Mount Horeb (Atoms to Apples)   | 2024 | May 12 / May 12 / May 9 / May 7       | Jun 3 / Jun 3 / Jun 1 / May 30        | Jun 16 / Jun 16 / Jun 13 / Jun 13  |
| Mount Horeb (Atoms to Apples)   | 2025 | May 15 / May 15 / May 14 / May 11     | Jun 12 / Jun 12 / Jun 10 / Jun 6      | – / – / Jun 20 / Jun 19            |
| Mt Horeb                        | 2024 | May 12 / May 12 / May 9 / May 7       | Jun 3 / Jun 3 / Jun 1 / May 29        | Jun 15 / Jun 15 / Jun 13 / Jun 12  |
| Mt Horeb                        | 2025 | May 15 / May 15 / May 14 / May 12     | Jun 12 / Jun 12 / Jun 9 / Jun 6       | Jun 21 / Jun 21 / Jun 19 / Jun 18  |
| Niagara                         | 2024 | Jun 1 / Jun 1 / Jun 2 / May 23        | Jun 22 / Jun 22 / Jun 24 / Jun 16     | Jul 6 / Jul 6 / Jul 7 / Jun 29     |
| Niagara                         | 2025 | Jun 6 / Jun 6 / Jun 7 / May 31        | Jun 25 / Jun 25 / Jun 27 / Jun 21     | Jul 5 / Jul 5 / Jul 7 / Jul 1      |
| Plymouth (Log Cabin)            | 2024 | May 17 / May 17 / May 19 / May 12     | Jun 8 / Jun 8 / Jun 12 / Jun 4        | Jun 19 / Jun 19 / Jun 21 / Jun 16  |
| Plymouth (Log Cabin)            | 2025 | Jun 2 / Jun 2 / Jun 3 / May 26        | Jun 20 / Jun 20 / Jun 21 / Jun 15     | Jun 28 / Jun 28 / Jun 29 / Jun 24  |
| Grafton (Dream Apple)           | 2024 | May 23 / May 23 / May 21 / May 22     | Jun 17 / Jun 17 / Jun 14 / Jun 15     | Jun 27 / Jun 27 / Jun 24 / Jun 25  |
| Grafton (Dream Apple)           | 2025 | Jun 9 / Jun 9 / Jun 8 / Jun 7         | Jun 25 / Jun 25 / Jun 24 / Jun 23     | Jul 5 / Jul 5 / Jul 3 / Jul 3      |
| Richland Center (Oakwood)       | 2024 | May 12 / May 12 / May 13 / May 8      | Jun 4 / Jun 4 / Jun 4 / May 31        | Jun 16 / Jun 16 / Jun 16 / Jun 13  |
| Richland Center (Oakwood)       | 2025 | May 15 / May 15 / May 15 / May 13     | Jun 12 / Jun 12 / Jun 11 / Jun 7      | Jun 22 / Jun 22 / Jun 21 / Jun 19  |
| Rochester (Ela)                 | 2024 | May 15 / May 15 / May 10 / May 10     | Jun 7 / Jun 7 / Jun 2 / Jun 2         | Jun 18 / Jun 18 / Jun 13 / Jun 15  |
| Rochester (Ela)                 | 2025 | May 31 / May 31 / May 24 / May 16     | Jun 19 / Jun 19 / Jun 15 / Jun 14     | Jun 26 / Jun 26 / Jun 23 / Jun 23  |
| Spring Valley                   | 2024 | May 20 / May 20 / May 21 / May 17     | Jun 11 / Jun 11 / Jun 13 / Jun 6      | Jun 23 / Jun 23 / Jun 24 / Jun 19  |
| Spring Valley                   | 2025 | May 15 / May 15 / May 16 / May 13     | Jun 14 / Jun 14 / Jun 16 / Jun 8      | Jun 23 / Jun 23 / Jun 24 / Jun 21  |
| Trempealeau (Ecker)             | 2024 | May 18 / May 18 / May 16 / May 12     | Jun 10 / Jun 10 / Jun 5 / Jun 3       | Jun 20 / Jun 20 / Jun 17 / Jun 16  |
| Trempealeau (Ecker)             | 2025 | May 15 / May 15 / May 13 / May 12     | Jun 12 / Jun 12 / Jun 9 / Jun 7       | Jun 21 / Jun 21 / Jun 19 / Jun 18  |
| Verona (West Mad Ag Sta)        | 2024 | May 12 / May 12 / May 12 / May 8      | Jun 2 / Jun 2 / Jun 4 / May 30        | Jun 14 / Jun 14 / Jun 16 / Jun 12  |
| Verona (West Mad Ag Sta)        | 2025 | May 15 / May 15 / May 16 / May 13     | Jun 11 / Jun 11 / Jun 13 / Jun 7      | Jun 21 / Jun 21 / Jun 22 / Jun 19  |
| Wabasha                         | 2024 | May 10 / May 10 / May 16 / May 9      | May 31 / May 31 / Jun 4 / May 29      | Jun 12 / Jun 12 / Jun 16 / Jun 11  |
| Wabasha                         | 2025 | May 13 / May 13 / May 13 / May 12     | Jun 8 / Jun 8 / Jun 8 / Jun 5         | Jun 20 / Jun 20 / Jun 20 / Jun 18  |
| Waupaca                         | 2024 | May 21 / May 21 / May 18 / May 17     | Jun 13 / Jun 13 / Jun 10 / Jun 7      | Jun 23 / Jun 23 / Jun 20 / Jun 19  |
| Waupaca                         | 2025 | May 31 / May 31 / May 29 / May 25     | Jun 20 / Jun 20 / Jun 18 / Jun 16     | Jun 29 / Jun 29 / Jun 26 / Jun 25  |

Ours − NEWA's, days (median, 10th–90th percentile, range, n):

- Egg hatch, ours on the station's days: +0 (+0 to +0; +0 to +0), n = 67
- Egg hatch, ours on the archive: +0 (-2 to +2; -7 to +7), n = 67
- Egg hatch, the Crop Risk Tool's old table: -4 (-6 to -2; -15 to -1), n = 67
- Cocooning, ours on the station's days: +0 (+0 to +0; +0 to +0), n = 67
- Cocooning, ours on the archive: +0 (-3 to +2; -5 to +5), n = 67
- Cocooning, the Crop Risk Tool's old table: -5 (-6 to -3; -8 to -2), n = 67
- Adults, ours on the station's days: +0 (+0 to +0; +0 to +0), n = 66
- Adults, ours on the archive: +0 (-3 to +2; -5 to +4), n = 66
- Adults, the Crop Risk Tool's old table: -3 (-4 to -2; -8 to -1), n = 66

## 3. Typical dates on the 1996–2025 normals

The day the normal running total (each year's own total from January 1, averaged over the 30 years, as `/api/v2/climate/normals` computes it) reaches each event, at the archive's cell. Ours: simple average 48 °F. Old: the Crop Risk Tool's table on single sine 48.2/86 °F.

| Event                                                           | Degree days | Arlington | Hancock | Rhinelander |
| --------------------------------------------------------------- | ----------- | --------- | ------- | ----------- |
| 10 % of eggs hatched                                            | 138         | May 6     | May 11  | May 19      |
| Half the eggs hatched, and the scouting window opens (NEWA 280) | 280         | May 22    | May 26  | Jun 2       |
| Most larvae feeding (the risk's peak)                           | 439         | Jun 2     | Jun 6   | Jun 14      |
| Scouting window closes                                          | 532         | Jun 8     | Jun 12  | Jun 20      |
| Half the larvae cocooned (NEWA 600)                             | 600         | Jun 11    | Jun 16  | Jun 24      |
| Half the adults out (NEWA 815)                                  | 815         | Jun 22    | Jun 26  | Jul 5       |
| UW–Madison's heaviest feeding begins                            | 600         | Jun 11    | Jun 16  | Jun 24      |
| UW–Madison's heaviest feeding ends                              | 800         | Jun 21    | Jun 25  | Jul 4       |
| Old: egg hatch                                                  | 300 (sine)  | May 18    | May 22  | May 29      |
| Old: pupae                                                      | 595 (sine)  | Jun 8     | Jun 11  | Jun 19      |
| Old: adults                                                     | 815 (sine)  | Jun 19    | Jun 23  | Jul 1       |
