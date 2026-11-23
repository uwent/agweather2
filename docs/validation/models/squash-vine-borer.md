# Squash vine borer (`squash-vine-borer`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H5). The model: `packages/agmodels/src/agmodels/insects/squash_vine_borer.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `squash_vine_borer.md` beside it. Version 0.1 was VDIFN's window (750, 900, 1,000 degree days, single sine 50 °F from January 1), with no known source; this version rebuilds it from the extension guides as D36 curves.

**In short:** no primary research source is known, so the model is a judgment across the extension guides: UW–Madison's modified-average degree days (50/86 °F from January 1), a moth flight and egg-laying curve from the first moths at about 825 through half at about 1,085 to the last by 1,900, the larvae in the vines timed from it by South Dakota State's stage lengths, and a window to protect stems from the first moths until three quarters have flown (about 1,240), UW–Madison's three weeks of egg laying around 1,000. The curve was drawn to the guides' numbers. Against 235 iNaturalist records of moths, its leading edge agrees, but the records' median is about 195 degree days (8 days) later and their tail much longer than the guides' three weeks.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Liesch and Groves, Squash Vine Borer (XHT1136), UW–Madison Extension, Wisconsin Horticulture (2026) | Moths emerge at about 900 degree days (base 50 °F), when chicory is in full bloom; treat when moths are first seen and repeat every 5–7 days through about three weeks of egg laying centered on about 1,000; hatch in one to two weeks; larvae feed two to six weeks | First moths, egg laying's length and center, the window |
| Delahaut, Degree Days for Common Fruit and Vegetable Insect Pests (XHT1087), UW–Madison Extension (2012), with XHT1086's method | Squash vine borer egg laying 900–1,000; degree days by the modified average, the low raised to 50 °F and the high capped at 86 °F, from January 1 | The method |
| UW Vegetable Entomology, squash vine borer (2026) | One generation in Wisconsin; moths emerge after about 1,000 degree days | Compared |
| Varenhorst et al., SDSU Extension, squash vine borer activity estimates (2021–2023) | Simple average above 50 °F: moths emerge at 1,000; eggs hatch 245–300 degree days after they're laid; larvae feed inside the plant for 660; pupae need 745 more (a second generation possible but not normally seen in South Dakota) | The larvae's lag and duration |
| Ruger and Leach, Squash Vine Borer (ENT-0106), Ohio State (2026) | Moths emerge at about 1,000 degree days, the daily average above 50 °F | Compared |
| Michigan State's Enviroweather model (`docs/enviroweather-models.md`) | Single sine 50 °F, no upper, from March 1: emergence 800; flight and egg laying from 900; declining from 1,800; complete 2,000 | The flight's tail and end |
| iNaturalist (`tmp/inat-check/`, 2026-11-19) | 235 research-grade records of moths inside AgWeather's grid in the upper Midwest, 2016–2026 | A field check, below |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's window | Replaced |

## Choices and differences

- **Degree days: UW–Madison's modified average, 50/86 °F from January 1** (stored). The Wisconsin guides' numbers (900 moths, egg laying 900–1,000) are on this method, and it's a stored total. South Dakota State and Ohio State count the simple average above 50 °F, which isn't stored and runs later in spring: on the archive's daily highs and lows, 2016–2025, it reaches 1,000 a median 7 days after the modified average at Arlington (2 to 10), 7 at Hancock (3 to 11) and 10 at Rhinelander (5 to 15). Single sine without an upper threshold (Michigan State, VDIFN) reaches it 3 to 5 days after (median 3.5, 3 and 5). Their 1,000 is therefore a later date than UW's 1,000 on the same weather, which narrows the gap between UW's 900 and their 1,000.
- **Moth flight and egg laying** (weight 0): PERT (750, 1,000, 1,900), a judgment across the guides: 5 % at 824 (MSU's emergence 800, UW's first moths 900), half at 1,083 (SDSU and Ohio State's emergence and UW's center of egg laying, 1,000), 75 % at 1,242 (UW: egg laying continues about a week and a half past 1,000, about 240 degree days in July), 95 % at 1,479, the last by 1,900 (MSU's decline from 1,800, complete at 2,000). Females lay as they fly, so one curve stands for both. Moths don't feed: no risk (as western bean cutworm's and mint root borer's moths).
- **Larvae in vines** (a `DerivedStage`, weight 1): from 270 degree days after each moth (SDSU's hatch, 245–300 after laying; UW's one to two weeks) for 660 (SDSU's feeding inside the plant; UW's two to six weeks). SDSU counts these on the simple average, slightly fewer per day than the modified; the difference is within the range SDSU gives.
- **One generation** (all the Wisconsin, Michigan and South Dakota guides).
- **Action window:** "Protect stems during egg laying", from 5 % (824) to 75 % (1,242) of the flight: UW–Madison's three weeks of egg laying around 1,000, treating when moths are first seen. Later moths still lay eggs (MSU, the iNaturalist records); the page says to keep stems protected while moths are seen.
- **Training area:** the extension guides' states (Wisconsin, South Dakota, Ohio, Michigan) and years (2012, XHT1087, to 2026).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_specialty_insects.py`, run in CI:

- Our first moths (5 %) come at 824 degree days (test: between MSU's 800 and UW's 900) and half have flown at 1,083 (test: 1,000 to 1,100, the guides' 1,000); 75 % at 1,242 (test: 1,200 to 1,280, a week and a half past 1,000); the last moths fly by 1,900 (test: by MSU's 2,000).
- The larvae hatch 270 degree days after laying (SDSU's 245–300) and feed for 660.
- The protection window runs from 824 to 1,242, three weeks around 1,000 in an average Wisconsin July (June 21 to July 12 at Arlington, below).
- The curve was drawn to these numbers; no field data were used.

### Against iNaturalist records

`tmp/inat-check/` (2026-11-19), each record's degree days at its own grid cell and date, here recomputed on the modified average 50/86 °F. 235 research-grade records of moths inside AgWeather's grid in the upper Midwest, 2016–2026; raw percentiles:

<!-- prettier-ignore -->
| Share of records | 5 % | 10 % | 25 % | 50 % | 75 % | 90 % | 95 % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Records, modified 50/86 | 809 | 887 | 1,076 | 1,278 | 1,516 | 1,765 | 2,073 |
| Our curve | 824 | 862 | 949 | 1,083 | 1,242 | 1,392 | 1,479 |

The first 5 and 10 % of the records came at 809 and 887 degree days, close to our 824 and 862, but half came at 1,278, about 195 degree days (8 days) after our half, and 90 % at 1,765 against our 1,392: moths are seen later and longer than the guides' three weeks of egg laying. On the single sine the records' effort-corrected median is later again (1,292 against a raw 1,210). Records follow abundance and lag emergence, and a moth seen isn't necessarily laying, so the leading edge is the part that checks the model; the tail agrees with MSU's flight declining from 1,800 more than with UW's three weeks. The model wasn't fitted to these records.

### On the normals

`scripts/specialty_insect_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (modified average 50/86 °F from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (modified DD50/86) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First moths, 5 % (824) | June 21 | June 24 | July 2 |
| Half the moths (1,083) | July 4 | July 8 | July 17 |
| 75 % (1,242) | July 12 | July 16 | July 26 |
| 95 % (1,479) | July 23 | July 28 | August 9 |
| Larvae in vines, peak (1,708) | August 3 | August 9 | August 24 |
| Half the larvae out of the vines (2,013) | August 18 | August 26 | September 16 |
| Protection window (824–1,242) | June 21 to July 12 | June 24 to July 16 | July 2 to July 26 |
| Normal total on October 15 | 2,788 | 2,578 | 2,225 |

UW–Madison: watch for moths by the last week of June, and protect stems through three weeks of egg laying. The model's first moths come about June 21 at Arlington and its window closes about July 12; in the north both come about 10 days later.

## Limits and open questions

- **No primary source:** the flight curve is a judgment across extension guides that don't cite their data (Ohio State's basis for 1,000, MSU's numbers).
- **The flight's tail:** UW's three weeks of egg laying against MSU's flight to 2,000 and the iNaturalist records' late median; Wisconsin pheromone or yellow-pan trap counts would decide. Ben (2026-11-23): no shift; the page and topic page caution that the window may close before egg laying ends, and to keep stems protected while moths are seen.
- **Methods differ by a week:** the guides at 1,000 degree days count it three ways, which put the same number a week apart on Wisconsin's weather.
- **iNaturalist's check** is from the exploratory pull in `tmp/inat-check`; the 768 upper Midwest records outside the grid could triple it with Open-Meteo or gridMET degree days, and a citable GBIF download is H0's to-do.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_specialty_insects.py
uv run app/manage.py shell < scripts/specialty_insect_normals.py  # the dates on the normals
```
