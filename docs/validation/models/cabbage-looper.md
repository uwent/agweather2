# Cabbage looper (`cabbage-looper`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H3). The model: `packages/agmodels/src/agmodels/insects/cabbage_looper.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `cabbage_looper.md` beside it. Version 0.1 was VDIFN's two windows (single sine 50/90 °F from May 15: (325, 520, 750) and (1115, 1310, 1540)); this version replaces them.

**In short:** USPest.org's cabbage looper model (Toba et al. 1973's development times, single sine 50/90 °F) as D36 curves, counted from the first moth caught in a pheromone trap, or from July 15 without one (UW–Madison: moths arrive from mid-July). Egg laying, eggs and caterpillar feeding follow USPest's events, and generations repeat every 912 degree days to the season's end, so the second generation, which UW–Madison says does the most damage, is now covered. No Wisconsin trap or scouting records were found to check the timing.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| USPest.org's cabbage looper model (`cbl`, Oregon State University; uspest.org/cgi-bin/ddmodel2.pl?spp=cbl; events as VDIFN's model sheet and the part H research record them) | Single sine 50/90 °F from the first pheromone-trap catch; "not fully tested", Pacific Northwest. After the biofix: 120 first egg laying, 218 first hatch, 325 small larvae, 428 first fourth instar, 520 large larvae, 638 first pupae, 750 last large larvae, 912 first adults | The method, the biofix and every stage's timing |
| Toba, Kishaba, Pangaldan and Vail 1973 ([doi:10.1093/aesa/66.5.965](https://doi.org/10.1093/aesa/66.5.965); in hand) | Constant and cycled temperatures in the laboratory, Riverside, California: no development of the immature stages at 7.2 °C (45 °F); few normal adults from 10.0 or 12.7 °C; egg-to-adult times in Table 1 (73.5 days at 16.6 °C, 42.2 at 21.0 °C, 21.5 at 27.2 °C: 873, 836 and 666 degree days above 50 °F, a mean of 791.5) | The check of USPest's generation (791.5 + 120 = 912) |
| Delahaut, Cabbage Looper (UW–Madison Extension, Wisconsin Horticulture) and UW Vegetable Entomology's cabbage looper page | Moths migrate into Wisconsin from mid-July through September; females lay over 10 to 12 days; eggs hatch in 3 to 6 days; larvae feed up to five weeks; moths emerge 10 to 14 days after pupating; their offspring, the second generation, do the most damage | The default biofix (July 15) and the calendar check |
| Schuh, Hahn and Wold-Burkness, Caterpillars on Cole Crops (University of Minnesota Extension) | Moths in Minnesota from early July to late August; one to three generations | Compared: the default |
| DATCP's black light traps, 2020–2026 (`docs/validation/data/datcp-blacklight-traps/`) | Celery looper and forage looper, not cabbage looper | Nothing |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows (USPest's 325, 520, 750 and those plus 790), from May 15 | Replaced |

## Choices and differences

- **Degree days:** single sine, 50/90 °F (USPest; both thresholds stored), from the biofix. NEWA runs no looper model.
- **Biofix:** the first moth caught in a pheromone trap (USPest). Loopers don't overwinter in Wisconsin; moths fly in from the south each summer, so their arrival follows weather systems, not local degree days, and a fixed date stands in where a grower has no trap. **Default July 15**, from UW–Madison's "mid-July through September" (UW Hort, UW Veg Ento). Minnesota's early July would be two weeks earlier. No Wisconsin or Minnesota records of first catches were found (DATCP's light traps count other loopers), so the default is a typical arrival, not a forecast; the page says so. VDIFN's May 15 had no source and put the first caterpillars a month before the moths arrive.
- **Egg laying:** PERT (120, 200, 450) from the biofix, weight 0. USPest's first eggs at 120; its single cohort lays for about 110 degree days (its last large larvae at 750), but migrants keep arriving for weeks, so the curve is wider (a judgment): half of the first generation's eggs laid by 221, 90 % by about 310.
- **Eggs** (a `DerivedStage`, weight 0): 98 degree days (USPest's 120 to 218).
- **Larval feeding** (a `DerivedStage`, the risk): from hatch to pupation, 420 degree days (USPest's 218 to 638); large caterpillars from 210 after hatch (its 428). Weight 1; moths and eggs carry no risk of their own.
- **Generations:** every 912 degree days from egg laying to egg laying (USPest's first adults at 912 and first eggs at 120 after the catch: 791.5 from egg to adult, Toba et al., plus 120 before laying), with no cap: fall freezes end the season. The spread is the default (egg laying's SD, 59).
- **Action window:** "Scout for small caterpillars", from 10 to 90 % of each generation's eggs hatched: 254–408 after the biofix. Small caterpillars are the target for sprays (A3422).
- **Equal generations (D37):** UW–Madison says the second generation does the most damage; every generation counts alike in the risk, and the page says so.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_cole_crop_pests.py`, run in CI:

- Egg laying starts at USPest's 120 after the first catch; eggs hatch 98 degree days after laying (USPest's 218) and caterpillars pupate 420 later (USPest's 638).
- The next generation's egg laying follows 912 after this one's: Toba et al.'s 791.5 from egg to adult (the mean of Table 1's times, converted to degree days above 50 °F) plus USPest's 120 before laying. The two generations' middles are within 10 degree days of 912 apart (the delay's spread shifts them slightly).
- Risk is on the caterpillars alone; the scouting window opens at 254 and closes at 408 in the first generation, and opens again at 1,134.

### On the normals

`scripts/cole_pest_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (single sine 50/90 °F) from the July 15 default. A typical-year calendar, not a forecast; a grower's own first catch moves every date.

<!-- prettier-ignore -->
| Event (DD50/90 from July 15) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Egg laying 50 % (221) | July 25 | July 25 | July 27 |
| Scouting window, first generation (254–408) | July 26 to August 2 | July 27 to August 3 | July 29 to August 7 |
| Caterpillars' first peak (547) | August 9 | August 11 | August 15 |
| Second generation's egg laying 10 % (1,036) | September 4 | September 9 | September 23 |
| Second generation's egg laying 50 % (1,136) | September 10 | September 17 | October 11 |
| Scouting window, second generation (1,134–1,347) | September 10 to 27 | September 17 to October 15 | from October 11 |
| Caterpillars' second peak (1,460) | October 11 | after October 15 | after October 15 |
| Normal total on October 15 | 1,478 | 1,349 | 1,148 |

From the July 15 default, the first generation's caterpillars peak in early to mid-August and the second generation's eggs are laid in early to mid-September at Arlington and Hancock, so the generation UW–Madison calls the most damaging is covered; at Rhinelander the season ends during the second generation's egg laying. Fall freezes (after early September) end the season before the second generation's caterpillars peak in most of the state, so in practice the late caterpillars are those of the first generation and of moths still arriving.

## Limits and open questions

- **The default biofix** (July 15) is UW–Madison's description, not a fit; Minnesota's account starts two weeks earlier. Wisconsin pheromone-trap first catches (UW Vegetable Entomology, consultants, or a DATCP trap if one is added) would fit it as black cutworm's and corn earworm's were fitted to DATCP's traps (D97).
- **Egg laying's spread** (to 450) is a judgment standing in for moths that keep arriving into September; a single biofix can't follow a second wave of migrants.
- **USPest's model is "not fully tested"**, from laboratory development times in California; its events haven't been compared with field observations here.
- **Equal generations (D37):** UW–Madison says the second generation does the most damage.
- **Not compared:** scouting counts of looper caterpillars in Wisconsin (none found).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_cole_crop_pests.py
uv run app/manage.py shell < scripts/cole_pest_normals.py   # the dates on the normals
```
