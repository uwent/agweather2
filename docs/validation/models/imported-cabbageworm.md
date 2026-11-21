# Imported cabbageworm (`imported-cabbageworm`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H3). The model: `packages/agmodels/src/agmodels/insects/imported_cabbageworm.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `imported_cabbageworm.md` beside it. Version 0.1 was VDIFN's two windows (single sine 50 °F, no upper, from January 1: (150, 240, 630) and (830, 1030, 2000), the last three with "?" in VDIFN's own sheet); this version replaces them.

**In short:** UW–Madison's degree-day table (Delahaut's XHT1087: "adult butterflies at 150–240 DD50", modified average 50/86 °F from January 1) as the spring flight's 10 and 50 %, eggs and caterpillars timed from it (Tatchell 1981's 349 degree days for the larva), and later flights every 840 degree days to the season's end, with risk on the caterpillars. Wisconsin's iNaturalist records of cabbage white butterflies (2016–2026) put the middle of the spring flight within 5 degree days of the model's; the generation time was set within the range development times allow to match their later flights, so those agree by construction. No counts of caterpillars were compared.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, XHT1087, Degree Days for Common Fruit & Vegetable Insect Pests (UW–Madison Extension, rev. 2012; hort.extension.wisc.edu, read 2026-11-21) and XHT1086 (the method) | Imported cabbageworm: "Adult butterflies at 150-240 DD50" (base 50 °F); phenology: serviceberry full bloom, redbud early to full bloom. Method: modified average, low raised to the base, high capped at 86 °F, from January 1 | The method and the spring flight (its 10 and 50 %). The table gives no years or observations behind its numbers |
| Tatchell 1981 ([doi:10.1007/BF02371879](https://doi.org/10.1007/BF02371879); as UC IPM's model database gives it, the paper not read) | Laboratory, England: lower threshold 9.4 °C (48.9 °F); larvae on cabbage 193.9 °C·d (349 °F·d); method not stated | The larval stage's duration |
| Nealis, Jones and Wellington 1984 ([doi:10.1007/BF00396765](https://doi.org/10.1007/BF00396765)) | Thresholds and degree days for every immature stage, Vancouver and Canberra | Not read (paywalled): would replace the egg and pupa judgments below |
| UW Vegetable Entomology's and UW–Madison Horticulture's imported cabbageworm pages (Liesch and Groves, rev. 2026) | Butterflies emerge in early May; eggs hatch in about 5 days (Veg Ento) or about a week (Hort); larvae feed 11–20 days; adults 6–11 days after pupating; second-generation butterflies from mid-July do the most damage; usually three generations (Hort), three to six (Veg Ento) | Egg and pupa durations (in days, converted), the calendar checks |
| iNaturalist research-grade records of _Pieris rapae_ in Wisconsin, 2016–2026 (the check of 2026-11-19, `tmp/inat-check/report.md`) | 2,666 dated, located records (965 observers), mostly adults | The generation time's choice within the development range; the spring check |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows: 150 and 240 match XHT1087; 630, 830, 1,030 and 2,000 unsourced | Replaced |

## Choices and differences

- **Degree days:** the modified average, 50/86 °F, from January 1 (XHT1086/XHT1087; the stored total `dd_modified_50_86`). VDIFN ran XHT1087's numbers on a single sine above 50 °F without an upper threshold; in spring the modified average gives more degree days than that sine (it raises the minimum to 50 °F), so the same numbers come a few days earlier on the modified average. NEWA runs no cabbageworm model (D95 doesn't apply).
- **Spring flight:** PERT (100, 210, 550) DD50 for butterflies emerging from overwintering chrysalises: its 10 % at 149 and 50 % at 239 are XHT1087's 150 and 240 (reading the table's span as the flight's first tenth to its middle; the table doesn't say which shares it means). Peak 210; 95 % by 394; the end, 550, is a judgment that fits the records' fall-off by about 550 (below). Weight 0: butterflies don't feed on the crop.
- **Eggs** (a `DerivedStage`, weight 0): from 105 after each butterfly emerges (egg laying centered about 5 days after emergence, a judgment) for 105 (about 5 days, UW Veg Ento). Degree days from days at about 21 DD50 a day, the normal daily total in July at Arlington.
- **Larval feeding** (a `DerivedStage`, the risk): from hatch for 349 degree days (Tatchell 1981's 349 above 48.9 °F, taken as DD50; the 1 °F difference is about 15 degree days over the stage). Its first peak comes at 662. Risk follows the caterpillars only (weight 1), as the plan set (D36): the butterflies are the signal, the caterpillars the damage.
- **Generations:** every 840 degree days, flight to flight, until fall freezes end the season; no cap. Development times give egg laying 105 + egg 105 + larva 349 + pupa 180 (8.5 days) = 739 with the shorter readings of UW's days, and about 820 with UW Hort's week-long egg and egg laying centered a week after emergence; UW's ranges in days allow about 600 to 1,000. Within that range, 840 follows the spacing of Wisconsin's records (832 and 861, below). The generations spread by the default (the spring flight's SD, 80).
- **Action window:** "Scout for eggs and young caterpillars", from 10 to 90 % of each generation's eggs hatched: 359–570 in spring. Weekly scouting all season stays the advice (A3422); the window marks when sprays aimed at small caterpillars work best.
- **Equal generations (D37):** UW–Madison says the second generation, from mid-July, does the most damage, since nearly all of its caterpillars grow up on planted cole crops; every generation counts alike in the risk, and the page says so.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_cole_crop_pests.py`, run in CI:

- XHT1087's butterflies at 150 to 240 degree days are the spring flight's 10 and 50 %, at 149 and 239 (tests: within 2).
- The larval stage is Tatchell 1981's 193.9 °C·d × 1.8 (349); risk is on the larvae alone.
- The development times sum to 739, below the generation time, 840.
- The scouting window opens at 359 and closes at 570 in spring.

### Against iNaturalist records

`scripts/check_imported_cabbageworm.py` (records from the iNaturalist check, `tmp/inat-check/`): each record at its own cell's running total on the model's setting, corrected for observers' effort by Wisconsin's daily research-grade Lepidoptera records placed at the degree days of the records' median cell (43.09 °N, 89.33 °W, near Madison), in 50-degree-day bins (bins with under 300 Lepidoptera records left out), smoothed over three bins. The records are adults seen, so they show butterflies present rather than emerging.

- **Spring:** the index rises from about 100 degree days, is highest at 150 to 300 (42.5, 35.6 and 39.8 records per 1,000 Lepidoptera in the bins from 150 to 300) and falls to its low by about 550 to 700. The records' 10, 50 and 90 % below 700 are at 111, 236 and 436; the middle of the spring flight is at 234 by the flight between troughs, against the model's 239 from UW–Madison's table. The model's spring emergence (10 % at 149, 90 % at 360) runs a little narrower than the records, as butterflies seen outlast their emergence by their lives.
- **Later flights:** the index has troughs near 625 and 1,525. Between them the records' median is at 1,066, and between 1,550 and 2,300 at 1,927: flights 832 and 861 apart. These spacings set the generation time (840), so the model's middles of the second and third flights, 1,083 and 1,924, show the fit, not a test. By development times alone (739) the model's later flights would come about 4 and 9 days earlier in a normal July and August at Arlington.
- After about 2,100 degree days the index stays high to the season's end, as generations overlap and late-summer butterflies accumulate; no fourth flight stands out.
- **Limits of the records:** observers' effort grows from about 25 records a year in 2016 to over 600 in 2025–2026; records cluster near cities (the effort correction uses one cell near Madison); a record lags emergence and rises with abundance. A field check of adult timing, not counts of caterpillars on crops.

### On the normals

`scripts/cole_pest_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (modified average 50/86 °F from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD50, modified) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Spring flight 10 % (149) | April 28 | May 1 | May 8 |
| Spring flight peak (210) | May 6 | May 9 | May 16 |
| Spring flight 50 % (239) | May 10 | May 13 | May 20 |
| Scouting window, spring (359–570) | May 22 to June 7 | May 25 to June 10 | May 31 to June 17 |
| Caterpillars' first peak (662) | June 12 | June 15 | June 23 |
| Second flight 50 % (1,083) | July 4 | July 8 | July 17 |
| Caterpillars' second peak (1,470) | July 23 | July 28 | August 8 |
| Third flight 50 % (1,924) | August 13 | August 20 | September 7 |
| Caterpillars' third peak (2,307) | September 3 | September 15 | after October 15 |
| Normal total on October 15 | 2,788 | 2,578 | 2,225 |

UW–Madison: butterflies emerge in early May; second-generation butterflies emerge in mid-July; usually three generations (UW Veg Ento three to six). The model's spring flight begins in late April and early May and peaks in early to mid-May, as UW describes. Its second flight's middle comes in early July in the south and mid-July at Rhinelander, a week or two before UW's mid-July in southern Wisconsin (the iNaturalist records agree with the model there). Three flights fit in a normal season everywhere, the third in August in the south and early September in the north; a fourth begins at Arlington only in October, after the first fall freezes in most years.

## Limits and open questions

- **XHT1087's numbers have no stated source or years**, and the table doesn't say which shares of the flight 150 and 240 are; reading them as 10 and 50 % fits the iNaturalist records' spring middle.
- **Egg and pupa** come from UW's days converted at about 21 degree days a day, and egg laying's timing is a judgment; Nealis, Jones and Wellington 1984 (paywalled) give stage thresholds and degree days that would replace them.
- **The generation time** (840) leans on iNaturalist records of adults, corrected for effort by a crude baseline; development times alone give 739 to about 820.
- **Equal generations (D37):** the second generation does the most damage by UW's account; every generation counts alike.
- **No caterpillar counts:** neither VDIFN's windows nor this model have been compared with scouting counts. Wisconsin's scouting records of the caterpillar complex (UW Vegetable Entomology, consultants), if any exist, would be the test.
- For UW's sites (`tmp/vegsites-corrections.md`): UW Veg Ento's three to six generations against UW Hort's usually three (already listed); the second flight's timing (mid-July) against the records' early July in southern Wisconsin.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_cole_crop_pests.py
uv run python scripts/check_imported_cabbageworm.py          # needs the archive in data/ and tmp/inat-check/ (records and cache)
uv run app/manage.py shell < scripts/cole_pest_normals.py   # the dates on the normals
```
