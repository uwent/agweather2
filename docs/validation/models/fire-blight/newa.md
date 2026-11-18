# Fire blight: ours against NEWA's on Wisconsin's orchard stations

Written by `scripts/check_fire_blight.py`. NEWA: its rules on the station's hours (`scripts/newa_reference.py`). Ours: the station's own hours, and the archive's at the station's cell. NEWA's bloom days only. Cougarblight: the four-day total's median difference (ours − NEWA's) and the share of days on the same level (blight nearby last year). EIP: the median absolute difference. Infection: MaryBlyt's Infection days, NEWA's / ours matched within a day / ours not in NEWA's.

| Station | Year | First blossom NEWA / station / grid | CB diff, same level (station; grid) | EIP abs diff (station; grid) | Infections (station; grid) |
| --- | --- | --- | --- | --- | --- |
| Baileys Harbor | 2024 | May 8 / May 8 / May 9 | +13, 100%; +9, 100% | 0; 1 | 0 / 0 / 0; 0 / 0 |
| Baileys Harbor | 2025 | May 16 / May 16 / May 17 | +10, 100%; +9, 100% | 0; 2 | 0 / 0 / 0; 0 / 0 |
| Belgium | 2024 | Apr 26 / Apr 26 / Apr 23 | +9, 100%; +24, 85% | 0; 7 | 0 / 0 / 0; 0 / 0 |
| Belgium | 2025 | May 6 / May 6 / May 6 | +13, 100%; +21, 87% | 0; 2 | 3 / 3 / 0; 3 / 0 |
| Belmont | 2024 | Apr 13 / Apr 13 / Apr 14 | +10, 100%; -7, 77% | 0; 8 | 2 / 1 / 0; 0 / 0 |
| Belmont | 2025 | Apr 19 / Apr 19 / Apr 22 | +8, 100%; -28, 82% | 0; 19 | 1 / 0 / 0; 0 / 0 |
| Brighton | 2024 | Apr 13 / Apr 13 / Apr 14 | +8, 90%; +17, 93% | 0; 5 | 0 / 0 / 0; 0 / 1 |
| Brighton | 2025 | Apr 22 / Apr 22 / Apr 22 | +9, 96%; +9, 92% | 0; 1 | 4 / 4 / 0; 4 / 0 |
| Brooklyn | 2024 | Apr 14 / Apr 14 / Apr 14 | +10, 71%; +11, 71% | 0; 3 | 0 / 0 / 0; 0 / 0 |
| Brooklyn | 2025 | Apr 22 / Apr 22 / Apr 22 | +7, 96%; +12, 92% | 0; 5 | 3 / 3 / 0; 3 / 0 |
| Brodhead | 2024 | Apr 13 / Apr 13 / Apr 13 | +9, 92%; +3, 96% | 0; 3 | 0 / 0 / 2; 0 / 1 |
| Brodhead | 2025 | Apr 19 / Apr 19 / Apr 19 | +9, 96%; +7, 96% | 0; 0 | 1 / 1 / 0; 1 / 0 |
| Burlington (Munster) | 2024 | Apr 14 / Apr 14 / Apr 14 | +8, 79%; +9, 64% | 0; 12 | 3 / 2 / 0; 1 / 0 |
| Burlington (Munster) | 2025 | Apr 23 / Apr 23 / Apr 22 | +8, 96%; -10, 96% | 0; 10 | 5 / 5 / 0; 5 / 0 |
| Chippewa Falls | 2024 | Apr 22 / Apr 22 / Apr 23 | +9, 100%; +23, 88% | 0; 7 | 2 / 1 / 0; 2 / 0 |
| Chippewa Falls | 2025 | Apr 28 / Apr 28 / Apr 28 | +7, 100%; +32, 96% | 0; 7 | 5 / 3 / 0; 3 / 0 |
| Colgate | 2024 | Apr 21 / Apr 22 / Apr 22 | +8, 96%; +4, 96% | 0; 4 | 1 / 1 / 0; 1 / 0 |
| Colgate | 2025 | Apr 28 / Apr 28 / Apr 28 | +10, 88%; +19, 84% | 0; 3 | 3 / 3 / 0; 3 / 0 |
| Eau Claire | 2024 | Apr 23 / Apr 24 / Apr 21 | +8, 93%; +18, 88% | 0; 6 | 2 / 2 / 0; 1 / 2 |
| Eau Claire | 2025 | Apr 28 / Apr 28 / Apr 27 | +5, 100%; +32, 95% | 0; 12 | 3 / 3 / 0; 2 / 0 |
| Eau Clair (Ferguson's Orchards) | 2024 | Apr 21 / Apr 21 / Apr 22 | +8, 96%; +17, 85% | 0; 6 | 3 / 2 / 0; 3 / 0 |
| Eau Clair (Ferguson's Orchards) | 2025 | Apr 28 / Apr 28 / Apr 28 | +7, 100%; +52, 88% | 0; 14 | 3 / 2 / 0; 2 / 0 |
| Edgar | 2024 | May 3 / May 3 / May 3 | +9, 100%; +8, 100% | 0; 0 | 1 / 1 / 0; 1 / 0 |
| Edgar | 2025 | May 8 / May 9 / May 9 | +9, 93%; +8, 93% | 0; 0 | 4 / 4 / 0; 4 / 0 |
| Fort Atkinson (Warm Belly Farm) (gauge) | 2024 | Apr 14 / Apr 14 / Apr 14 | +9, 82%; +8, 82% | 0; 0 | 2 / 1 / 0; 1 / 0 |
| Fort Atkinson (Warm Belly Farm) | 2025 | Apr 22 / Apr 22 / Apr 22 | +6, 100%; +4, 100% | 2; 4 | 0 / 0 / 0; 0 / 3 |
| Galesville (Ferguson) | 2025 | Apr 23 / Apr 23 / Apr 24 | +8, 100%; -1, 91% | 0; 6 | 3 / 3 / 0; 3 / 0 |
| Galesville | 2024 | Apr 14 / Apr 15 / Apr 14 | +9, 87%; +11, 84% | 0; 2 | 2 / 1 / 0; 2 / 0 |
| Galesville | 2025 | Apr 23 / Apr 23 / Apr 23 | +7, 100%; +55, 95% | 0; 8 | 4 / 3 / 0; 3 / 0 |
| Gays Mills (gauge) | 2024 | Apr 14 / Apr 14 / Apr 13 | +10, 87%; +60, 69% | 0; 20 | 0 / 0 / 0; 0 / 2 |
| Gays Mills (gauge) | 2025 | Apr 22 / Apr 22 / Apr 18 | +9, 100%; +86, 87% | 0; 26 | 3 / 3 / 0; 3 / 1 |
| Genoa City | 2024 | Apr 14 / Apr 14 / Apr 14 | +8, 85%; +3, 74% | 0; 4 | 2 / 2 / 0; 2 / 0 |
| Genoa City (gauge) | 2025 | Apr 22 / Apr 23 / Apr 22 | +8, 100%; +14, 100% | 0; 3 | 3 / 3 / 0; 3 / 0 |
| Gays Mills (Sandcreek) | 2024 | Apr 14 / Apr 14 / Apr 14 | +10, 87%; +39, 80% | 0; 15 | 1 / 0 / 0; 1 / 1 |
| Gays Mills (Sandcreek) | 2025 | Apr 21 / Apr 22 / Apr 21 | +7, 100%; +18, 100% | 0; 7 | 2 / 2 / 0; 2 / 0 |
| Malone | 2024 | Apr 22 / Apr 22 / Apr 23 | +10, 100%; +2, 100% | 0; 4 | 0 / 0 / 0; 0 / 0 |
| Malone | 2025 | Apr 30 / May 2 / May 5 | +9, 100%; -21, 92% | 0; 7 | 4 / 4 / 0; 4 / 0 |
| Mauston (Northwoods) | 2024 | Apr 15 / Apr 15 / Apr 16 | +9, 90%; +8, 83% | 0; 0 | 1 / 0 / 0; 0 / 0 |
| Mauston (Northwoods) | 2025 | Apr 24 / Apr 24 / Apr 26 | +6, 96%; +5, 91% | 0; 2 | 4 / 4 / 0; 4 / 0 |
| Mequon (Barthel) | 2024 | Apr 19 / Apr 21 / Apr 17 | +6, 100%; +20, 100% | 0; 5 | 1 / 1 / 0; 0 / 0 |
| Mequon (Barthel) | 2025 | May 1 / May 1 / Apr 28 | +10, 97%; +16, 93% | 0; 2 | 3 / 3 / 0; 2 / 0 |
| Merrill (Helenes) | 2024 | May 3 / May 3 / May 3 | +8, 100%; -11, 96% | 1; 11 | 1 / 1 / 0; 1 / 1 |
| Merrill (Helenes) | 2025 | May 9 / May 9 / May 9 | +8, 96%; +20, 93% | 0; 2 | 6 / 6 / 0; 6 / 0 |
| Mount Horeb (Atoms to Apples) | 2024 | Apr 14 / Apr 14 / Apr 14 | +9, 80%; +33, 64% | 0; 8 | 1 / 1 / 0; 0 / 1 |
| Mount Horeb (Atoms to Apples) | 2025 | Apr 19 / Apr 19 / Apr 22 | +7, 96%; +30, 96% | 0; 7 | 4 / 3 / 0; 3 / 0 |
| Mt Horeb | 2024 | Apr 14 / Apr 15 / Apr 14 | +9, 86%; +21, 71% | 0; 7 | 1 / 0 / 1; 0 / 1 |
| Mt Horeb | 2025 | Apr 23 / Apr 23 / Apr 21 | +8, 100%; +46, 82% | 0; 18 | 3 / 3 / 0; 3 / 0 |
| Niagara | 2024 | May 3 / May 3 / May 4 | +9, 96%; -10, 84% | 1; 5 | 3 / 2 / 0; 2 / 0 |
| Niagara | 2025 | May 11 / May 11 / May 12 | +8, 96%; -22, 96% | 0; 12 | 8 / 8 / 0; 7 / 0 |
| Plymouth (Log Cabin) | 2024 | Apr 21 / Apr 21 / Apr 26 | +6, 100%; -61, 78% | 0; 32 | 3 / 3 / 0; 1 / 0 |
| Plymouth (Log Cabin) | 2025 | May 2 / May 3 / May 5 | +9, 100%; -28, 96% | 0; 9 | 3 / 3 / 0; 3 / 0 |
| Grafton (Dream Apple) | 2024 | Apr 28 / Apr 28 / Apr 27 | +12, 93%; +21, 92% | 0; 5 | 0 / 0 / 0; 0 / 0 |
| Grafton (Dream Apple) | 2025 | May 11 / May 11 / May 9 | +11, 97%; +24, 96% | 0; 3 | 0 / 0 / 0; 0 / 0 |
| Richland Center (Oakwood) | 2024 | Apr 14 / Apr 14 / Apr 14 | +10, 83%; +39, 66% | 0; 13 | 1 / 0 / 0; 1 / 0 |
| Richland Center (Oakwood) | 2025 | Apr 23 / Apr 23 / Apr 21 | +8, 100%; +51, 91% | 0; 18 | 4 / 4 / 0; 4 / 0 |
| Rochester (Ela) | 2024 | Apr 15 / Apr 15 / Apr 14 | +8, 91%; +28, 79% | 0; 5 | 1 / 1 / 0; 0 / 1 |
| Rochester (Ela) | 2025 | Apr 24 / Apr 24 / Apr 23 | +8, 97%; +26, 93% | 0; 11 | 3 / 3 / 0; 3 / 0 |
| Spring Valley | 2024 | Apr 25 / Apr 25 / Apr 27 | +8, 96%; +6, 88% | 0; 1 | 4 / 4 / 0; 4 / 0 |
| Spring Valley | 2025 | Apr 28 / Apr 28 / Apr 30 | +7, 100%; -12, 91% | 0; 3 | 2 / 2 / 0; 2 / 0 |
| Trempealeau (Ecker) | 2024 | Apr 16 / Apr 16 / Apr 14 | +8, 100%; +13, 97% | 0; 1 | 1 / 1 / 1; 0 / 0 |
| Trempealeau (Ecker) | 2025 | Apr 23 / Apr 23 / Apr 22 | +6, 96%; +51, 91% | 0; 6 | 5 / 5 / 0; 3 / 0 |
| Verona (West Mad Ag Sta) | 2024 | Apr 15 / Apr 15 / Apr 15 | +9, 90%; +30, 72% | 0; 7 | 0 / 0 / 0; 0 / 0 |
| Verona (West Mad Ag Sta) | 2025 | Apr 23 / Apr 24 / Apr 23 | +8, 96%; +32, 83% | 0; 7 | 3 / 3 / 0; 3 / 0 |
| Wabasha | 2024 | Apr 17 / Apr 17 / Apr 17 | +9, 96%; +6, 96% | 0; 0 | 1 / 1 / 0; 0 / 1 |
| Wabasha | 2025 | Apr 24 / Apr 25 / Apr 24 | +10, 100%; +20, 100% | 0; 4 | 2 / 2 / 0; 2 / 0 |
| Waupaca | 2024 | Apr 26 / Apr 26 / Apr 21 | +8, 100%; +32, 83% | 0; 11 | 5 / 5 / 0; 4 / 1 |
| Waupaca | 2025 | May 5 / May 5 / May 1 | +10, 100%; +53, 88% | 0; 11 | 5 / 5 / 0; 4 / 0 |

## Totals (working gauges)

- station hours: Cougarblight on NEWA's level 1625 of 1708 bloom days (95%); EIP median absolute difference 0; NEWA's 146 Infection days, 130 matched within a day, 4 of ours not in NEWA's
- grid hours: Cougarblight on NEWA's level 1448 of 1636 bloom days (89%); EIP median absolute difference 5; NEWA's 146 Infection days, 118 matched within a day, 14 of ours not in NEWA's
