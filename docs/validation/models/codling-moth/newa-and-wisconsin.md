# Codling moth: ours against NEWA's, and across Wisconsin

Written by `scripts/check_codling_moth.py`. Ours: WSU's curves from first catch, degree days 50/86 °F single sine, first catch by Jones et al. 2013's latitude equation unless a trap date is given. NEWA: `scripts/newa_reference.py`'s reading of its page (DD50 without an upper, first catch at 404, first spray 250 after it, second first catch 1501 after it). Station days are NEWA's on the local clock; the archive's are CST.

## 1–2. NEWA's codling moth against ours, on the station's hours and the archive's

Dates. First catch: NEWA's default (404 DD50 from January 1) / ours estimated from latitude on the station's days / ours on the archive at the station's cell. Hatch: NEWA's first spray (250 DD after its first catch) / our window's opening with NEWA's first catch as the trap date / ours estimated (station) / ours estimated (grid). Second hatch: NEWA's (its second first catch, 1501 after the first) / ours with NEWA's first catch / ours estimated (station). Size: the second generation's class on the station's days and the grid's.

| Station | Year | First catch NEWA / station / grid | First hatch NEWA / same catch / station / grid | Second hatch NEWA / same catch / station | Size station / grid |
| --- | --- | --- | --- | --- | --- |
| Baileys Harbor | 2024 | Jun 16 / Jun 7 / Jun 12 | Jul 3 / Jul 4 / Jun 28 / Jun 30 | Sep 14 / Aug 22 / Aug 16 | 2 / 2 |
| Baileys Harbor | 2025 | Jun 24 / Jun 19 / Jun 19 | Jul 8 / Jul 9 / Jul 4 / Jul 4 | Sep 25 / Aug 23 / Aug 18 | 2 / 2 |
| Belgium | 2024 | Jun 3 / May 27 / May 25 | Jun 18 / Jun 18 / Jun 16 / Jun 15 | Aug 21 / Aug 1 / Jul 30 | 3 / 3 |
| Belgium | 2025 | Jun 16 / Jun 10 / Jun 8 | Jun 26 / Jun 27 / Jun 24 / Jun 23 | Aug 28 / Aug 8 / Aug 5 | 3 / 3 |
| Belmont | 2024 | May 17 / May 13 / May 17 | Jun 3 / Jun 4 / Jun 2 / Jun 6 | Jul 30 / Jul 13 / Jul 12 | 5 / 4 |
| Belmont | 2025 | May 23 / May 15 / May 23 | Jun 10 / Jun 10 / Jun 7 / Jun 12 | Jul 29 / Jul 15 / Jul 13 | 5 / 4 |
| Brighton | 2024 | May 19 / May 16 / May 16 | Jun 5 / Jun 5 / Jun 3 / Jun 4 | Jul 31 / Jul 15 / Jul 13 | 5 / 5 |
| Brighton | 2025 | Jun 3 / May 30 / May 29 | Jun 17 / Jun 18 / Jun 16 / Jun 16 | Aug 8 / Jul 23 / Jul 22 | 4 / 4 |
| Brooklyn | 2024 | May 19 / May 16 / May 16 | Jun 5 / Jun 6 / Jun 4 / Jun 4 | Aug 4 / Jul 17 / Jul 15 | 5 / 4 |
| Brooklyn | 2025 | May 29 / May 22 / May 24 | Jun 14 / Jun 15 / Jun 12 / Jun 13 | Aug 5 / Jul 20 / Jul 18 | 4 / 4 |
| Brodhead | 2024 | May 17 / May 13 / May 14 | Jun 2 / Jun 3 / May 31 / Jun 2 | Jul 31 / Jul 13 / Jul 12 | 5 / 5 |
| Brodhead | 2025 | May 26 / May 16 / May 17 | Jun 12 / Jun 13 / Jun 11 / Jun 12 | Aug 4 / Jul 19 / Jul 16 | 4 / 4 |
| Burlington (Munster) | 2024 | May 20 / May 17 / May 16 | Jun 6 / Jun 7 / Jun 4 / Jun 4 | Aug 3 / Jul 17 / Jul 15 | 5 / 5 |
| Burlington (Munster) | 2025 | Jun 1 / May 27 / May 29 | Jun 16 / Jun 17 / Jun 15 / Jun 16 | Aug 7 / Jul 23 / Jul 20 | 4 / 4 |
| Chippewa Falls | 2024 | May 29 / May 21 / May 21 | Jun 15 / Jun 16 / Jun 11 / Jun 11 | Aug 18 / Jul 30 / Jul 27 | 4 / 4 |
| Chippewa Falls | 2025 | Jun 1 / May 24 / May 24 | Jun 18 / Jun 19 / Jun 15 / Jun 16 | Aug 13 / Jul 27 / Jul 24 | 4 / 4 |
| Colgate | 2024 | May 26 / May 21 / May 22 | Jun 14 / Jun 15 / Jun 12 / Jun 12 | Aug 17 / Jul 29 / Jul 26 | 4 / 4 |
| Colgate | 2025 | Jun 8 / Jun 3 / Jun 3 | Jun 22 / Jun 22 / Jun 21 / Jun 19 | Aug 17 / Jul 31 / Jul 28 | 3 / 4 |
| Eau Claire | 2024 | May 30 / May 21 / May 20 | Jun 16 / Jun 17 / Jun 12 / Jun 9 | Aug 24 / Aug 1 / Jul 29 | 3 / 4 |
| Eau Claire | 2025 | Jun 2 / May 25 / May 22 | Jun 19 / Jun 20 / Jun 16 / Jun 14 | Aug 15 / Jul 28 / Jul 26 | 4 / 4 |
| Eau Clair (Ferguson's Orchards) | 2024 | May 28 / May 20 / May 20 | Jun 15 / Jun 16 / Jun 11 / Jun 10 | Aug 19 / Jul 30 / Jul 27 | 4 / 4 |
| Eau Clair (Ferguson's Orchards) | 2025 | Jun 2 / May 25 / May 23 | Jun 19 / Jun 19 / Jun 16 / Jun 15 | Aug 14 / Jul 27 / Jul 24 | 4 / 4 |
| Edgar | 2024 | Jun 7 / Jun 1 / Jun 1 | Jun 24 / Jun 25 / Jun 20 / Jun 20 | Sep 13 / Aug 17 / Aug 13 | 2 / 2 |
| Edgar | 2025 | Jun 12 / Jun 4 / Jun 5 | Jun 27 / Jun 28 / Jun 23 / Jun 23 | Sep 13 / Aug 11 / Aug 8 | 2 / 2 |
| Fort Atkinson (Warm Belly Farm) | 2024 | May 19 / May 16 / May 16 | Jun 5 / Jun 6 / Jun 3 / Jun 4 | Aug 2 / Jul 16 / Jul 14 | 5 / 5 |
| Fort Atkinson (Warm Belly Farm) | 2025 | May 28 / May 18 / May 23 | Jun 14 / Jun 15 / Jun 12 / Jun 13 | Aug 4 / Jul 20 / Jul 17 | 4 / 4 |
| Galesville (Ferguson) | 2025 | May 29 / May 16 / May 16 | Jun 15 / Jun 15 / Jun 11 / Jun 12 | Aug 6 / Jul 21 / Jul 18 | 4 / 4 |
| Galesville | 2024 | May 22 / May 18 / May 17 | Jun 10 / Jun 11 / Jun 6 / Jun 6 | Aug 11 / Jul 25 / Jul 21 | 4 / 4 |
| Galesville | 2025 | May 30 / May 18 / May 15 | Jun 15 / Jun 16 / Jun 12 / Jun 11 | Aug 7 / Jul 22 / Jul 19 | 4 / 4 |
| Gays Mills | 2024 | May 21 / May 18 / May 15 | Jun 9 / Jun 11 / Jun 6 / Jun 4 | Aug 10 / Jul 23 / Jul 21 | 4 / 5 |
| Gays Mills | 2025 | May 30 / May 19 / May 16 | Jun 15 / Jun 15 / Jun 12 / Jun 11 | Aug 8 / Jul 22 / Jul 20 | 4 / 4 |
| Genoa City | 2024 | May 18 / May 15 / May 17 | Jun 3 / Jun 4 / Jun 2 / Jun 4 | Jul 29 / Jul 13 / Jul 11 | 5 / 5 |
| Genoa City | 2025 | Jun 3 / May 29 / May 29 | Jun 17 / Jun 18 / Jun 16 / Jun 16 | Aug 8 / Jul 23 / Jul 22 | 4 / 4 |
| Gays Mills (Sandcreek) | 2024 | May 21 / May 17 / May 17 | Jun 9 / Jun 10 / Jun 5 / Jun 5 | Aug 9 / Jul 23 / Jul 20 | 4 / 4 |
| Gays Mills (Sandcreek) | 2025 | May 30 / May 18 / May 19 | Jun 15 / Jun 15 / Jun 12 / Jun 12 | Aug 8 / Jul 22 / Jul 19 | 4 / 4 |
| Malone | 2024 | May 27 / May 21 / May 22 | Jun 13 / Jun 14 / Jun 10 / Jun 12 | Aug 12 / Jul 26 / Jul 22 | 4 / 4 |
| Malone | 2025 | Jun 6 / Jun 2 / Jun 5 | Jun 21 / Jun 21 / Jun 19 / Jun 21 | Aug 12 / Jul 28 / Jul 25 | 4 / 3 |
| Mauston (Northwoods) | 2024 | May 22 / May 18 / May 19 | Jun 10 / Jun 11 / Jun 5 / Jun 8 | Aug 9 / Jul 23 / Jul 20 | 4 / 4 |
| Mauston (Northwoods) | 2025 | Jun 2 / May 26 / May 28 | Jun 17 / Jun 17 / Jun 14 / Jun 16 | Aug 9 / Jul 23 / Jul 20 | 4 / 4 |
| Mequon (Barthel) | 2024 | May 29 / May 23 / May 21 | Jun 16 / Jun 16 / Jun 13 / Jun 11 | Aug 18 / Jul 31 / Jul 28 | 4 / 4 |
| Mequon (Barthel) | 2025 | Jun 11 / Jun 7 / Jun 5 | Jun 23 / Jun 24 / Jun 22 / Jun 21 | Aug 21 / Aug 5 / Aug 2 | 3 / 3 |
| Merrill (Helenes) | 2024 | Jun 4 / May 30 / May 31 | Jun 21 / Jun 22 / Jun 18 / Jun 19 | Sep 9 / Aug 13 / Aug 7 | 2 / 2 |
| Merrill (Helenes) | 2025 | Jun 15 / Jun 5 / Jun 4 | Jun 28 / Jun 29 / Jun 23 / Jun 23 | Sep 15 / Aug 13 / Aug 9 | 2 / 2 |
| Mount Horeb (Atoms to Apples) | 2024 | May 21 / May 17 / May 15 | Jun 9 / Jun 10 / Jun 6 / Jun 4 | Aug 8 / Jul 22 / Jul 19 | 4 / 5 |
| Mount Horeb (Atoms to Apples) | 2025 | May 30 / May 19 / May 18 | Jun 16 / Jun 16 / Jun 13 / Jun 11 | – / – / – | 1 / 4 |
| Mt Horeb | 2024 | May 20 / May 17 / May 15 | Jun 7 / Jun 8 / Jun 5 / Jun 4 | Aug 7 / Jul 21 / Jul 18 | 4 / 5 |
| Mt Horeb | 2025 | May 30 / May 23 / May 16 | Jun 15 / Jun 16 / Jun 13 / Jun 11 | Aug 9 / Jul 23 / Jul 21 | 4 / 4 |
| Niagara | 2024 | Jun 7 / May 31 / Jun 1 | Jun 25 / Jun 25 / Jun 19 / Jun 21 | Sep 9 / Aug 14 / Aug 8 | 2 / 2 |
| Niagara | 2025 | Jun 15 / Jun 4 / Jun 6 | Jun 27 / Jun 28 / Jun 23 / Jun 24 | Sep 13 / Aug 12 / Aug 8 | 2 / 2 |
| Plymouth (Log Cabin) | 2024 | May 25 / May 19 / May 25 | Jun 13 / Jun 13 / Jun 9 / Jun 14 | Aug 12 / Jul 25 / Jul 23 | 4 / 4 |
| Plymouth (Log Cabin) | 2025 | Jun 7 / Jun 3 / Jun 6 | Jun 21 / Jun 22 / Jun 20 / Jun 22 | Aug 16 / Jul 30 / Jul 28 | 3 / 3 |
| Grafton (Dream Apple) | 2024 | Jun 7 / Jun 3 / May 31 | Jun 22 / Jun 23 / Jun 20 / Jun 18 | Aug 28 / Aug 7 / Aug 5 | 3 / 3 |
| Grafton (Dream Apple) | 2025 | Jun 19 / Jun 16 / Jun 14 | Jun 30 / Jul 1 / Jun 28 / Jun 27 | Sep 4 / Aug 12 / Aug 10 | 2 / 2 |
| Richland Center (Oakwood) | 2024 | May 21 / May 17 / May 16 | Jun 10 / Jun 11 / Jun 7 / Jun 5 | Aug 13 / Jul 24 / Jul 22 | 4 / 4 |
| Richland Center (Oakwood) | 2025 | Jun 1 / May 25 / May 23 | Jun 16 / Jun 17 / Jun 14 / Jun 12 | Aug 10 / Jul 24 / Jul 22 | 4 / 4 |
| Rochester (Ela) | 2024 | May 23 / May 19 / May 17 | Jun 12 / Jun 13 / Jun 9 / Jun 5 | Aug 13 / Jul 25 / Jul 23 | 4 / 5 |
| Rochester (Ela) | 2025 | Jun 6 / Jun 3 / May 30 | Jun 21 / Jun 21 / Jun 20 / Jun 17 | Aug 14 / Jul 28 / Jul 27 | 4 / 4 |
| Spring Valley | 2024 | May 30 / May 22 / May 23 | Jun 16 / Jun 16 / Jun 12 / Jun 13 | Aug 22 / Jul 31 / Jul 28 | 3 / 3 |
| Spring Valley | 2025 | Jun 1 / May 24 / May 27 | Jun 18 / Jun 19 / Jun 15 / Jun 17 | Aug 15 / Jul 28 / Jul 25 | 4 / 3 |
| Trempealeau (Ecker) | 2024 | May 24 / May 18 / May 17 | Jun 13 / Jun 13 / Jun 8 / Jun 5 | Aug 14 / Jul 27 / Jul 24 | 4 / 4 |
| Trempealeau (Ecker) | 2025 | May 30 / May 19 / May 15 | Jun 16 / Jun 16 / Jun 12 / Jun 10 | Aug 7 / Jul 22 / Jul 20 | 4 / 4 |
| Verona (West Mad Ag Sta) | 2024 | May 21 / May 18 / May 18 | Jun 8 / Jun 9 / Jun 5 / Jun 6 | Aug 6 / Jul 20 / Jul 18 | 4 / 4 |
| Verona (West Mad Ag Sta) | 2025 | Jun 1 / May 26 / May 26 | Jun 16 / Jun 17 / Jun 14 / Jun 14 | Aug 8 / Jul 23 / Jul 21 | 4 / 4 |
| Wabasha | 2024 | May 18 / May 16 / May 18 | Jun 4 / Jun 4 / Jun 3 / Jun 6 | Aug 4 / Jul 20 / Jul 18 | 4 / 4 |
| Wabasha | 2025 | May 30 / May 16 / May 15 | Jun 15 / Jun 16 / Jun 10 / Jun 10 | Aug 8 / Jul 23 / Jul 20 | 4 / 4 |
| Waupaca | 2024 | May 31 / May 23 / May 20 | Jun 17 / Jun 17 / Jun 14 / Jun 11 | Aug 24 / Aug 1 / Jul 30 | 3 / 4 |
| Waupaca | 2025 | Jun 7 / Jun 2 / May 30 | Jun 22 / Jun 22 / Jun 20 / Jun 17 | Aug 19 / Aug 1 / Jul 29 | 3 / 4 |

Ours − NEWA's, days (median, 10th–90th percentile, n):

- First catch, ours estimated on the station's days: -6 (-11 to -3), n = 67
- First catch, ours estimated on the grid: -6 (-11 to -2), n = 67
- First hatch window against NEWA's first spray, the same first catch: +1 (+0 to +1), n = 67
- First hatch window, ours estimated (station): -3 (-4 to -1), n = 67
- First hatch window, ours estimated (grid): -3 (-5 to +0), n = 67
- Second hatch, the same first catch: -17 (-24 to -16), n = 66

## 3. Across Wisconsin on the archive, 2016–2025 (estimated first catch)

Mean date of each event (years reaching it, if not all), the second generation's size class in each year, and first catch less the day `apple-stages` reaches bloom (346 DD43), mean (range).

| Site | First catch | Window opens | Half hatched | Window closes | Second flight | Second window opens | Size classes | First catch − bloom, days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gays Mills | May 23 | Jun 9 | Jun 20 | Jul 4 | Jul 14 | Jul 19 | 4, 4, 4, 4, 4, 4, 4, 4, 5, 4 | +18.9 (+13 to +28) |
| Baraboo | May 25 | Jun 11 | Jun 22 | Jul 6 | Jul 16 | Jul 21 | 4, 4, 4, 4, 3, 4, 4, 4, 4, 4 | +17.5 (+11 to +23) |
| Verona (WMARS) | May 26 | Jun 12 | Jun 22 | Jul 6 | Jul 16 | Jul 22 | 4, 4, 4, 4, 4, 4, 4, 4, 4, 4 | +18.9 (+12 to +30) |
| Fort Atkinson | May 25 | Jun 10 | Jun 21 | Jul 5 | Jul 15 | Jul 20 | 4, 4, 4, 4, 4, 5, 4, 4, 5, 4 | +18.6 (+11 to +30) |
| Eau Claire | May 24 | Jun 10 | Jun 21 | Jul 5 | Jul 14 | Jul 20 | 4, 4, 5, 3, 4, 5, 4, 5, 4, 4 | +14.4 (+8 to +19) |
| Sturgeon Bay (PARS) | Jun 9 | Jun 26 | Jul 9 | Jul 25 | Aug 5 | Aug 12 | 2, 2, 3, 2, 2, 2, 2, 2, 2, 2 | +15.1 (+7 to +20) |
| Bayfield | Jun 21 | Jul 9 | Jul 22 | Aug 9 | Aug 21 | Aug 30 | 2, 1, 2, 2, 2, 2, 2, 2, 2, 2 | +15.8 (+10 to +19) |
