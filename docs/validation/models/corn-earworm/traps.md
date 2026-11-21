# Corn earworm: the default biofix against DATCP's pheromone traps, 2021–2026

Written by `scripts/check_corn_earworm.py` from DATCP's corn earworm pheromone tables (`docs/validation/data/datcp-blacklight-traps/cew-pheromone-weekly.csv`) and the archive at each site's cell. Site-years with 50 or more moths. Significant flight: the first week with 35 or more moths (5 a night); main flight: the first such week from July 25. Days off: 0 inside the week (the 7 days ending on its date), else days before (−) or after (+) it. DD: single sine 55/92 °F.

| Year | Site | Moths | Significant week | Main flight's week | DD from Jan 1 (main) | Aug 1 off | Aug 8 off | Aug 15 off | Aug 20 off | DD Aug 15 to Oct 15 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | Arlington | 2469 | Aug 18 | Aug 18 | 1470 | -11 | -4 | 0 | +2 | 717 |
| 2021 | Arlington N | 1958 | Jul 28 | Jul 28 | 1167 | +4 | +11 | +18 | +23 | 721 |
| 2021 | Beaver Dam | 594 | Jul 28 | Jul 28 | 1134 | +4 | +11 | +18 | +23 | 700 |
| 2021 | Bristol | 72 | Aug 25 | Aug 25 | 1649 | -18 | -11 | -4 | 0 | 753 |
| 2021 | Coon Valley | 160 | Aug 25 | Aug 25 | 1657 | -18 | -11 | -4 | 0 | 676 |
| 2021 | Cottage Grove | 273 | Aug 25 | Aug 25 | 1699 | -18 | -11 | -4 | 0 | 776 |
| 2021 | Hancock | 126 | Sep 1 | Sep 1 | 1580 | -25 | -18 | -11 | -6 | 610 |
| 2021 | Manitowoc | 318 | Aug 25 | Aug 25 | 1281 | -18 | -11 | -4 | 0 | 638 |
| 2021 | Mayville | 2156 | Aug 18 | Aug 18 | 1440 | -11 | -4 | 0 | +2 | 688 |
| 2021 | Ripon | 3098 | Aug 18 | Aug 18 | 1482 | -11 | -4 | 0 | +2 | 692 |
| 2021 | Sun Prairie East | 84 | Sep 1 | Sep 1 | 1823 | -25 | -18 | -11 | -6 | 762 |
| 2021 | Sun Prairie North | 196 | Sep 1 | Sep 1 | 1823 | -25 | -18 | -11 | -6 | 762 |
| 2021 | Watertown | 274 | Aug 18 | Aug 18 | 1560 | -11 | -4 | 0 | +2 | 770 |
| 2022 | Beaver Dam | 349 | Sep 1 | Sep 1 | 1563 | -25 | -18 | -11 | -6 | 514 |
| 2022 | Hancock | 211 | Sep 8 | Sep 8 | 1515 | -32 | -25 | -18 | -13 | 484 |
| 2022 | Manitowoc | 67 | – | – | – | – | – | – | – | 523 |
| 2022 | Mayville | 1209 | Jul 28 | Jul 28 | 1059 | +4 | +11 | +18 | +23 | 506 |
| 2022 | Ripon | 1395 | Aug 25 | Aug 25 | 1420 | -18 | -11 | -4 | 0 | 507 |
| 2022 | Sun Prairie North | 298 | Sep 8 | Sep 8 | 1745 | -32 | -25 | -18 | -13 | 534 |
| 2022 | Sun Prairie Northwest | 233 | Sep 1 | Sep 1 | 1654 | -25 | -18 | -11 | -6 | 534 |
| 2022 | Sun Prairie South | 270 | Sep 1 | Sep 1 | 1654 | -25 | -18 | -11 | -6 | 534 |
| 2022 | Watertown | 62 | – | – | – | – | – | – | – | 556 |
| 2023 | Beaver Dam | 4545 | Aug 24 | Aug 24 | 1513 | -17 | -10 | -3 | 0 | 622 |
| 2023 | East Bristol | 1230 | Aug 24 | Aug 24 | 1589 | -17 | -10 | -3 | 0 | 672 |
| 2023 | Hancock | 160 | Sep 7 | Sep 7 | 1637 | -31 | -24 | -17 | -12 | 594 |
| 2023 | Manitowoc | 281 | Aug 31 | Aug 31 | 1320 | -24 | -17 | -10 | -5 | 535 |
| 2023 | Mayville | 3218 | Aug 24 | Aug 24 | 1470 | -17 | -10 | -3 | 0 | 604 |
| 2023 | Pardeeville | 2267 | Aug 24 | Aug 24 | 1599 | -17 | -10 | -3 | 0 | 673 |
| 2023 | Ripon | 1459 | Aug 24 | Aug 24 | 1499 | -17 | -10 | -3 | 0 | 623 |
| 2023 | Sun Prairie | 547 | Aug 24 | Aug 24 | 1613 | -17 | -10 | -3 | 0 | 676 |
| 2023 | Watertown | 224 | Aug 31 | Aug 31 | 1734 | -24 | -17 | -10 | -5 | 659 |
| 2024 | Beaver Dam | 2204 | Aug 15 | Aug 15 | 1359 | -8 | -1 | 0 | +5 | 648 |
| 2024 | Burlington | 650 | Aug 22 | Aug 22 | 1602 | -15 | -8 | -1 | 0 | 694 |
| 2024 | Cottage Grove | 693 | Aug 22 | Aug 22 | 1560 | -15 | -8 | -1 | 0 | 671 |
| 2024 | Fitchburg | 562 | Jul 11 | Aug 15 | 1431 | -8 | -1 | 0 | +5 | 681 |
| 2024 | Hancock | 120 | Sep 5 | Sep 5 | 1452 | -29 | -22 | -15 | -10 | 587 |
| 2024 | Mayville | 1909 | Aug 22 | Aug 22 | 1415 | -15 | -8 | -1 | 0 | 628 |
| 2024 | Pardeeville | 370 | Aug 29 | Aug 29 | 1608 | -22 | -15 | -8 | -3 | 674 |
| 2024 | Ripon | 1399 | Aug 29 | Aug 29 | 1525 | -22 | -15 | -8 | -3 | 638 |
| 2024 | Sun Prairie N | 843 | Aug 22 | Aug 22 | 1539 | -15 | -8 | -1 | 0 | 659 |
| 2025 | Beaver Dam | 2200 | Aug 14 | Aug 14 | 1373 | -7 | 0 | +1 | +6 | 600 |
| 2025 | Burlington | 2417 | Aug 14 | Aug 14 | 1471 | -7 | 0 | +1 | +6 | 651 |
| 2025 | Clinton | 2116 | Jul 3 | Aug 14 | 1500 | -7 | 0 | +1 | +6 | 661 |
| 2025 | Coon Valley | 831 | Aug 14 | Aug 14 | 1493 | -7 | 0 | +1 | +6 | 654 |
| 2025 | Hancock | 178 | Aug 14 | Aug 14 | 1277 | -7 | 0 | +1 | +6 | 534 |
| 2025 | Mayville | 1065 | Jul 17 | Aug 14 | 1354 | -7 | 0 | +1 | +6 | 601 |
| 2025 | Pardeeville | 321 | Aug 14 | Aug 14 | 1453 | -7 | 0 | +1 | +6 | 616 |
| 2025 | Sun Prairie E | 1166 | Jul 10 | Aug 14 | 1460 | -7 | 0 | +1 | +6 | 629 |
| 2025 | Sun Prairie N | 1286 | Jul 10 | Aug 14 | 1460 | -7 | 0 | +1 | +6 | 624 |
| 2025 | Watertown E | 841 | Jul 10 | Aug 14 | 1489 | -7 | 0 | +1 | +6 | 657 |
| 2026 | Beaver Dam | 1761 | Jul 29 | Jul 29 | 1179 | +3 | +10 | +17 | +22 | 631 |
| 2026 | Burlington | 1172 | Jul 8 | Aug 12 | 1487 | -5 | 0 | +3 | +8 | 701 |
| 2026 | Coon Valley | 401 | Aug 19 | Aug 19 | 1646 | -12 | -5 | 0 | +1 | 683 |
| 2026 | Fitchburg | 1853 | Aug 12 | Aug 12 | 1499 | -5 | 0 | +3 | +8 | 679 |
| 2026 | Green Lake | 1001 | Sep 9 | Sep 9 | 1753 | -33 | -26 | -19 | -14 | 652 |
| 2026 | Hancock | 876 | Sep 9 | Sep 9 | 1742 | -33 | -26 | -19 | -14 | 570 |
| 2026 | Janesville | 2452 | Aug 12 | Aug 12 | 1558 | -5 | 0 | +3 | +8 | 694 |
| 2026 | Keyeser | 789 | Aug 19 | Aug 19 | 1568 | -12 | -5 | 0 | +1 | 659 |
| 2026 | Leroy | 1136 | Aug 26 | Aug 26 | 1546 | -19 | -12 | -5 | 0 | 606 |
| 2026 | Lodi | 4260 | Jul 22 | Jul 29 | 1236 | +3 | +10 | +17 | +22 | 652 |
| 2026 | Pardeeville | 1001 | Aug 26 | Aug 26 | 1636 | -19 | -12 | -5 | 0 | 629 |
| 2026 | Sun Prairie N | 1382 | Jul 22 | Aug 12 | 1472 | -5 | 0 | +3 | +8 | 675 |
| 2026 | Sun Prairie S | 539 | Aug 12 | Aug 12 | 1483 | -5 | 0 | +3 | +8 | 668 |
| 2026 | Watertown W | 810 | Aug 19 | Aug 19 | 1641 | -12 | -5 | 0 | +1 | 688 |
| 2026 | Williams Bay | 2584 | Aug 12 | Aug 12 | 1487 | -5 | 0 | +3 | +8 | 701 |

## Summary: fixed dates against the observed weeks

| Against | Date | n | Inside the week | Within a week | Median, days | Mean absolute, days |
| --- | --- | --- | --- | --- | --- | --- |
| main | August 1 | 63 | 0 | 21 | -15 | 14.9 |
| main | August 8 | 63 | 16 | 25 | -8 | 9.2 |
| main | August 15 | 63 | 9 | 42 | -1 | 6.0 |
| main | August 20 | 63 | 17 | 46 | +0 | 5.9 |
| significant | August 1 | 63 | 0 | 13 | -15 | 16.7 |
| significant | August 8 | 63 | 9 | 17 | -8 | 12.8 |
| significant | August 15 | 63 | 8 | 34 | -1 | 10.3 |
| significant | August 20 | 63 | 17 | 40 | +0 | 10.2 |

## Date or degree days

The main flight's week (its middle), 63 site-years: day of year median 232 (August 20), SD 10.7 days; degree days from January 1 median 1500, SD 159, which at late August's ~15 degree days a day is 10.6 days. A date places it no worse than degree days.

## The flight after the main flight's week

Degree days (55/92 °F) from the first day of the main flight's week to each later week's middle, each site-year's catch from then on counting alike (63 site-years): 5 % at 44, 10 % at 61, 25 % at 81, 50 % at 141, 75 % at 266, 90 % at 505, 95 % at 623. Traps come down in mid to late September, so the tail is cut short.

Degree days from August 15 to October 15 at these sites: median 652, range 484–776 (65 site-years).
