# Cabbage looper (`cabbage-looper`): validation

Model version 0.3, written 2026-11-21 and revised 2026-11-23 for generation weights (D98; part H, H3, and round 2). The model: `packages/agmodels/src/agmodels/insects/cabbage_looper.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `cabbage_looper.md` beside it. Version 0.1 was VDIFN's two windows (single sine 50/90 °F from May 15: (325, 520, 750) and (1115, 1310, 1540)); this version replaces them.

**In short:** USPest.org's cabbage looper model (Toba et al. 1973's development times, single sine 50/90 °F) as D36 curves, counted from the first moth caught in a pheromone trap, or from July 15 without one (UW–Madison: moths arrive from mid-July). Egg laying, eggs and caterpillar feeding follow USPest's events, and generations repeat every 912 degree days to the season's end, so the second generation, which UW–Madison says does the most damage, is now covered. No Wisconsin trap or scouting records were found to check the timing.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| USPest.org's cabbage looper model (`cbl`, on Oregon State University's USPest.org, which credits the model to the University of Minnesota; uspest.org/cgi-bin/ddmodel2.pl?spp=cbl; events as VDIFN's model sheet and the part H research record them) | Single sine 50/90 °F from the first pheromone-trap catch; "not fully tested", Pacific Northwest. After the biofix: 120 first egg laying, 218 first hatch, 325 small larvae, 428 first fourth instar, 520 large larvae, 638 first pupae, 750 last large larvae, 912 first adults | The method, the biofix and every stage's timing |
| Toba, Kishaba, Pangaldan and Vail 1973 ([doi:10.1093/aesa/66.5.965](https://doi.org/10.1093/aesa/66.5.965); read in full) | Laboratory, USDA at Riverside, California, on a modified Ignoffo artificial diet, at constant and cycled temperatures (4 replicates of 25): no hatch or development at 7.3 °C (the abstract's 7.2); no adults after exposure to 10.0 °C, and practically all deformed from 12.7 °C; six larval instars instead of five at 10.0 and 12.7 °C; at 32.2 °C development like 26.7 °C, but the adults' eggs didn't hatch (pp. 965–967). Table 1, days from a half-day-old egg at 16.6, 21.0 and 27.2 °C: to the first instar 8.2, 4.5 and 3.5; to the pupa 47.6, 27.4 and 14.4; to the adult (both sexes) 73.5, 42.2 and 21.5. Outdoors in the shade (mean 15.6 °C, 6.1–29.4 °C), egg to adult 69.8 days. The paper gives no threshold or degree days | USPest's events, which are Table 1's days times (T − 10 °C) × 1.8, averaged over the three constant temperatures: hatch 97, 89 and 108 (mean 98, USPest's 218 − 120), pupation 566, 543 and 446 (mean 518, its 638 − 120), adult 873, 836 and 666 (mean 791.5, its 912 − 120). Confirmed: every number the model takes |
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
- **Generation weights** (version 0.3; Ben, 2026-11-23): UW–Madison says the second generation does the most damage. Its caterpillars weigh 1 in the risk and the other generations' 0.5. The source says which generation matters, not by how much, so 0.5 is a judgment. Version 0.2 weighted every generation alike (D37).
- **Season (D128):** a migrant, so its season opens on the calendar, July 15, everywhere, and ends after October 31.

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

#### What the weights change

`uv run app/manage.py shell < scripts/generation_weights_normals.py`: the risk on the same normal totals with every generation alike (version 0.2) and with version 0.3's generation weights, at each peak of the risk through October 15, without fall freezes. From the July 15 default biofix.

<!-- prettier-ignore -->
| Place | Peak | Equal generations | Weighted |
| --- | --- | --- | --- |
| Arlington | August 12 | 1.00 (Very high) | 0.50 (High) |
| Arlington | October 11 | 0.99 (Very high) | 0.99 (Very high) |
| Arlington | Days at High or above | 50 | 33 |
| Hancock | August 15 | 1.00 (Very high) | 0.50 (High) |
| Hancock | Days at High or above | 43 | 25 |
| Rhinelander | August 20 | 1.00 (Very high) | 0.50 (High) |
| Rhinelander | Days at High or above | 27 | 6 |

On the normals from July 15, only Arlington's second generation of caterpillars peaks before October 15 (October 11); at Hancock and Rhinelander the season's only caterpillar peak is the first generation's, now High at its peak (0.50) rather than Very high, with fewer days at High or above (Arlington 33 instead of 50, Hancock 25 instead of 43, Rhinelander 6 instead of 27). So the weights lower the risk most where the damaging second generation doesn't arrive before fall: there the first generation is all there is, and a grower may read its lower risk as less to watch. Fall freezes end the season before most second-generation caterpillars mature in the north.

## Limits and open questions

- **The default biofix** (July 15) is UW–Madison's description, not a fit; Minnesota's account starts two weeks earlier. Wisconsin pheromone-trap first catches (UW Vegetable Entomology, consultants, or a DATCP trap if one is added) would fit it as black cutworm's and corn earworm's were fitted to DATCP's traps (D97).
- **Egg laying's spread** (to 450) is a judgment standing in for moths that keep arriving into September; a single biofix can't follow a second wave of migrants.
- **USPest's model is "not fully tested"**, from laboratory development times in California; its events haven't been compared with field observations here.
- **The base, 50 °F, is USPest's, not Toba et al.'s.** On it the same development takes fewer degree days the warmer the chamber (egg to adult 873 at 16.6 °C, 836 at 21.0 °C, 666 at 27.2 °C), the sign of a base set too low: a line through Table 1's three rates crosses zero at about 12.7 °C (55 °F), where Toba et al. got almost no normal adults, and gives about 318 °C·d (573 °F·d) above it. USPest's averages fit mid-summer temperatures; in a cool spell the model runs ahead of the insect and in a hot one behind it. The laboratory larvae fed on artificial diet, and the paper discusses development on plants as sometimes slower and sometimes faster (p. 972).
- **The other generations' weight (0.5)** is a judgment: UW–Madison says the second generation does the most damage, not by how much. Where the second generation doesn't arrive before fall (central and northern Wisconsin on the normals), the weight halves the season's only caterpillar peak.
- **Not compared:** scouting counts of looper caterpillars in Wisconsin (none found).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_cole_crop_pests.py
uv run app/manage.py shell < scripts/cole_pest_normals.py   # the dates on the normals
uv run app/manage.py shell < scripts/generation_weights_normals.py  # what the generation weights change
```
