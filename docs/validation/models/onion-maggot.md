# Onion maggot (`onion-maggot`): validation

Model version 0.4, written 2026-11-21 and revised 2026-11-23 for generation weights (D98; part H, H1, and round 2: 0.5 for both summer flights in version 0.3, then 0.1 and 0.5 in version 0.4 after Eckenrode et al. 1975 and Liu et al. 1982 were read in full; Ben, 2026-11-23). The model: `packages/agmodels/src/agmodels/insects/onion_maggot.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `onion_maggot.md` beside it. Version 0.1 was VDIFN's two windows (single sine 39.2/86 °F, (510, 680, 850) and (1460, 1950, 2435), source "XHT1087": the peaks are Delahaut's 680 and 1,950 DD40, below, and her third, 3,230, was left out); this version replaces it with NEWA's model (D95).

**In short:** NEWA's onion maggot model as D36 curves: the simple average above 40 °F from January 1, three flights from NEWA's first emergence and peak of each, larval feeding timed from each flight by Liu, McEwen and Ritcey's (1982) development times. On the same weather at 34 Wisconsin NEWA stations it matches NEWA's spring events to the day and its later flights within a few days. Against the New York trapping NEWA's numbers rest on (Eckenrode, Vea and Stone 1975), the spring midpoint agrees and the generation time is about 10 % shorter. In the risk the spring generation weighs 1, the second 0.1 and the third 0.5, a judgment from the papers' damage counts: the second brood was the smallest and did a tenth or less of the first's damage, while the third damages bulbs near harvest and in storage. No Wisconsin trap data are in hand.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA's onion maggot model (newa.cornell.edu, read 2026-11-21; `tmp/references/insects/notes/newa-insects.md`) | Simple average, base 40 °F, no upper, from January 1. First and peak emergence per generation: overwintering 390 ± 103 / 735 ± 122, first 1,218 ± 167 / 1,752 ± 292, second 2,415 ± 260 / 2,975 ± 347. Three generations in the north; the spring generation the most destructive (stands cut by over half); eggs 7–10 days after emergence; treated seed or an in-furrow drench at planting, or row covers before flies emerge kept three weeks past the spring peak; foliar sprays against adults not effective; the first and second generations rarely damage. Sources: Eckenrode et al. 1975; Andaloro, Rose and Eckenrode 1984 (Search: Agriculture, Cornell; not in hand, no DOI) | The method, the flights' first emergence and peaks, three generations, the window |
| Eckenrode, Vea and Stone 1975 ([doi:10.1093/ee/4.5.785](https://doi.org/10.1093/ee/4.5.785); read in full) | Cone traps baited with cull onions at the edges of commercial muck onion fields at Elba, Potter (1971–74) and Oswego (1973–74), New York, emptied twice a week May 1 to October 15. Base 40 °F from eight constant temperatures (the x-intercept "slightly over 40 °F", p. 788); max–min air thermal units with Arnold's correction when the minimum fell below the base (p. 786); the start of the count isn't stated. Table 2: spring 50 % catch 501–957 (site averages 607, 740, 867; overall 712); second and third broods 1,187 and 1,257 overall (with Oswego's two low-catch estimates), Elba's and Potter's averages 1,167 and 1,160, 1,329 and 1,315; these TU run from the previous brood's 50 % (Elba's 1971 second brood, 7/24, is 1,104). Table 3: initial increase averaged 389 (spring), 1,554 and 2,743 overall (Elba 364, 1,585, 2,782; Potter 391, 1,416, 2,817; Oswego 433); initial increases came at least 7 days before damage (p. 788). Three broods; the most flies in spring everywhere, the fewest "invariably" in the second, perhaps because of thrips sprays (p. 787). At Elba in 1971 spring-brood maggots killed 47 % of 1,127 seedlings by July 23, there was no midsummer injury, and the late-season brood injured up to about 15 of each 200 bulbs sampled August 24 to October 21 (Fig. 1, read from the figure): "an economically important late-season brood" (p. 787). 27–91 % of second-brood pupae diapause (LaFrance and Perron 1959) | Checks; the spring first emergence as about 5 % of the flight |
| Liu, McEwen and Ritcey 1982 ([doi:10.1093/ee/11.3.751](https://doi.org/10.1093/ee/11.3.751); read in full) | Keswick Marsh, Ontario, 1980: sticky and interception traps, dissected females, weekly damage counts in treated and untreated onions; Allen's sine above 4 °C on air and soil (3 and 15 cm) temperatures (p. 751–752). Laboratory times (Ritcey and McEwen, unpublished), above their x-intercept threshold of 4.38 °C: pre-oviposition 103, egg 50, larva 287, pupa 306 °C·d; a generation 746 °C·d (1,343 °F·d). Three generations; first flies May 21, 58 % of the first generation's flies June 3–18. In the untreated bed (Fig. 4, read from the figure) about 22–25 % of onions were invaded at the first generation's peak in late June, 1–2 % by the second at the end of July and under 1 % by the third before harvest (September 10–19), which came before the third's expected peak. Seed-furrow granules controlled the first generation; sprays against the second are "debatable"; the third generation, attacking mature bulbs that go into storage, is "the most destructive economically" in Ontario (p. 754). Growers who sprayed by the forecast had fewer than 3 % of onions damaged with one to five sprays | The larval stage's lag and duration |
| Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture (`tmp/references/insects/UW Madison XHT1087 2005 - Degree days for fruit and vegetable pests.pdf`; no DOI) | "Base temperature = 40°F; 680, 1950, 3230 DD 40 for 1st, 2nd, & 3rd generation flies"; "1st generation eggs laid 230-280 DD40". No method, upper threshold, start date or source, and not said to be peaks. Its 230–280 for the first eggs comes before its own 680 for the first flies and before NEWA's first emergence (390), so it can't be eggs from this year's flies on any count we know | Compared (on the normals, below). VDIFN's two windows peaked at its 680 and 1,950. UW Vegetable Entomology's onion maggot page gives the same three numbers as "peak flight", counted from when the ground thaws |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows | Replaced |

## Choices and differences

- **Degree days:** simple average above 40 °F, no upper threshold, from January 1 (NEWA; the stored total `average_40`). Eckenrode et al. counted above 40 °F with Arnold's correction (from a start they don't state), Liu et al. by sine above 4 °C (39.2 °F).
- **Spring flight:** PERT (200, 721, 1,349) DD40, set so NEWA's first emergence (390) is its 5 % and NEWA's peak (735) its 50 %: 5, 50 and 95 % at 389, 734 and 1,102 (the 95 % before NEWA's first summer flies at 1,218). 5 % is a choice: NEWA's cabbage maggot table puts first emergence at 5.9 % of its curve, and Eckenrode et al.'s "initial increase" (389) is the first surge in catches, not the first fly. The start (200) is free within what the two points allow; a start of 150 or 250 moves the 95 % between 1,050 and 1,175.
- **Larval feeding** (a `DerivedStage`): from 275 °F·d after each fly emerges (pre-oviposition 103 + egg 50 °C·d) for 517 (larva 287 °C·d), Ritcey and McEwen's laboratory times (above 4.38 °C, 39.9 °F, which Liu et al. ran above 4 °C in the field) read as DD40. NEWA's "eggs 7–10 days after emergence" is about 200–300 DD40 in late May.
- **Generations:** every 1,100 DD40, the least-squares fit to NEWA's peaks (1,017 and 1,223 apart): 50 % at 1,831 and 2,930 against NEWA's 1,752 and 2,975. SD 200: NEWA's later flights start 534 and 560 before their peaks, against 345 in spring, so each spreads more than the last; the curves' first flies (5 %) come at 1,366 and 2,367 against NEWA's 1,218 and 2,415. Eckenrode et al. measured 1,187 and 1,257, Liu et al.'s lab generation 1,343 °F·d: NEWA's, and so the model's, is about 10 % shorter. Three flights at most (NEWA, Eckenrode et al., Liu et al.).
- **Generation weights** (version 0.4; Ben, 2026-11-23): flight and larval feeding weight 1; the spring generation weighs 1, the second 0.1 and the third 0.5. A judgment the papers bound but don't fix:
  - **Spring, 1:** NEWA calls it the most destructive; at Elba in 1971 its maggots killed 47 % of 1,127 seedlings by July 23 (Eckenrode et al., p. 787).
  - **Second, 0.1:** the smallest brood in every New York catch, "invariably" (Eckenrode et al., p. 787; in Fig. 2 its peaks run about 0.03 to 0.4 of spring's: Oswego 1974 about 4 flies against 145, Potter 1974 about 20 against 70), with no midsummer injury at Elba in 1971 and no grower complaints of damage in July and August (p. 785), though thrips sprays may have suppressed it. In Ontario's untreated bed (Liu et al., Fig. 4) it invaded 1 to 2 % of onions against the first generation's 22 to 25 %, 0.04 to 0.09 of it, and sprays against it are "debatable" (p. 753). So 0.1: the top of the damage ratio and the lower half of the catches' ratios. NEWA: the first and second generations "rarely damage".
  - **Third, 0.5** (kept from version 0.3): it damages maturing bulbs near harvest (up to about 15 of 200 bulbs at Elba, Fig. 1, "an economically important late-season brood") and goes into storage with them, "the most destructive economically" in Ontario (Liu et al., p. 754), though harvest often comes before its peak (Liu et al.'s did). Half, rather than the spring generation's full weight, because the damage depends on whether onions are still in the field.
  - Version 0.3 weighted both summer generations 0.5; version 0.2 weighted every generation alike (D37).
- **Action window:** "Protect onion seedlings during fly flight", from 5 % to 95 % of each flight (390–1,102 in spring): NEWA's advice to have treated seed, an in-furrow treatment or row covers in place before flies emerge and for three weeks past the peak.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 251, the first adult flight (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 17 at Madison, April 24 at Hancock, May 4 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) April 14. Where we don't have the normals it opens on April 1. It ends after October 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_maggots.py`, run in CI:

- The spring flight's first flies (5 %) come at 390 degree days and half at 735, as NEWA's table has them (test: within 3); 95 % before NEWA's next first emergence (1,218).
- Later flights' midpoints come 79 degree days after NEWA's 1,752 (1,831) and 45 before its 2,975 (2,930); their 5 % within 150 of NEWA's first emergence (1,366 against 1,218, 2,367 against 2,415). Three flights, no fourth.
- Eckenrode et al. 1975: in New York fields the spring flight's midpoint averaged 712 (ours 734) and the next two came 1,187 and 1,257 later, against the model's 1,100 (1,097 and 1,099 between our midpoints).
- Larval feeding's lag and duration are Liu et al.'s 153 and 287 °C·d × 1.8.
- The generation weights are 1, 0.1 and 0.5: past the generations' overlap, the risk is the equal-weights risk times the third generation's 0.5, and the second flight's peak, after the spring larvae, stays below 0.2.

### Against NEWA on the same weather

`scripts/check_maggots.py`; full table in [onion-maggot/newa.md](onion-maggot/newa.md). NEWA's model recomputed from its published rules (`scripts/newa_reference.py`) on the hours of 34 Wisconsin NEWA stations, 2024 and 2025 (67 station-seasons); ours on the same daily max and min, and on the archive at each station's cell.

<!-- prettier-ignore -->
| Ours − NEWA's, days | Station days: median (10th–90th percentile) | Archive: median (10th–90th percentile) |
| --- | --- | --- |
| First emergence (390; ours 5 %) | 0 (0 to 0) | 0 (−3 to +2) |
| Spring peak (735) | 0 (0 to 0) | 0 (−3 to +3) |
| First generation's first flies (1,218) | +5 (+4 to +6) | +5 (+2 to +8) |
| First generation peak (1,752) | +3 (+2 to +3) | +3 (0 to +5) |
| Second generation's first flies (2,415) | +1 (0 to +1) | +1 (−3 to +3) |
| Second generation peak (2,975) | −2 (−2 to −1) | −2 (−6 to +1) |

The model reproduces NEWA's events: first emergence and the spring peak fall on NEWA's day, and the later flights within 2 to 3 days at the median, the first summer flight's first flies 5 days later. (One station-season, Mount Horeb 2025, whose record breaks after mid-June, puts our first summer flies 51 days after NEWA's; it's left in the table.)

### On the normals

`scripts/maggot_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (DD40, simple average, from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD40) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First flies, 5 % (390) | May 8 | May 13 | May 21 |
| Spring flight 50 % (734) | May 27 | May 31 | June 8 |
| Spring flight 95 % (1,102) | June 11 | June 15 | June 23 |
| Second flight 5 % (1,366) | June 21 | June 25 | July 3 |
| Second flight 50 % (1,831) | July 6 | July 11 | July 20 |
| Third flight 50 % (2,930) | August 10 | August 17 | September 1 |
| Protection windows | May 8–June 11, June 21–July 22, July 23–August 31 | May 13–June 15, June 25–July 28, July 29–September 10 | May 21–June 23, July 3–August 8, August 9–October 5 |

UW–Madison: UW Vegetable Entomology's scouting calendar (topic page) has flies from mid-May to mid-June, early July to mid-August, and late August through September, and its onion maggot page puts peak flights at 680, 1,950 and 3,230 DD40 counted from when the ground thaws; Delahaut's XHT1087 gives the same three numbers for the first, second and third generations' flies, without a start or method. The spring flight agrees; the model's second flight starts in late June, a week or so before UW's, and its third peaks in mid-August, 10 to 14 days before UW's third peak (3,230 DD40: August 20 at Arlington, August 28 at Hancock, September 15 at Rhinelander on the normals) and before UW's late-August-to-September flight.

#### What the weights change

`uv run app/manage.py shell < scripts/generation_weights_normals.py`: the risk on the same normal totals with every generation alike (version 0.2) and with version 0.4's generation weights, at each peak of the equal-weights risk through October 15, without fall freezes; version 0.3's (0.5 for both summer flights) from the previous run of the same script.

<!-- prettier-ignore -->
| Place | Peak | Equal generations | Version 0.3 (1, 0.5) | Version 0.4 (1, 0.1, 0.5) |
| --- | --- | --- | --- | --- |
| Arlington | June 5 | 1.27 (Very high) | 1.27 (Very high) | 1.26 (Very high) |
| Arlington | June 23 | 1.21 (Very high) | 1.01 (Very high) | 0.86 (Very high) |
| Arlington | July 18 | 1.21 (Very high) | 0.60 (High) | 0.15 (Low) |
| Arlington | Days at High or above | 124 | 108 | 67 |
| Hancock | June 9 | 1.27 (Very high) | 1.27 (Very high) | 1.26 (Very high) |
| Hancock | June 28 | 1.21 (Very high) | 1.00 (Very high) | 0.83 (Very high) |
| Hancock | July 23 | 1.21 (Very high) | 0.60 (High) | 0.15 (Low) |
| Hancock | Days at High or above | 131 | 112 | 69 |
| Rhinelander | June 17 | 1.27 (Very high) | 1.27 (Very high) | 1.26 (Very high) |
| Rhinelander | July 6 | 1.21 (Very high) | 1.01 (Very high) | 0.86 (Very high) |
| Rhinelander | August 2 | 1.21 (Very high) | 0.60 (High) | 0.15 (Low) |
| Rhinelander | Days at High or above | 146 | 125 | 75 |

The spring flight and its maggots are unchanged (the June peak, where the spring larvae overlap the second flight's start, eases a little). The second flight and its maggots peak at Low (0.15) in July. The third generation, which the equal-weights risk doesn't separate from the second, peaks at 0.55 (High) at 3,164 DD40 on the model's risk curve, mid-August at Arlington. A season has 67 to 75 days at High or above, against 108 to 125 in version 0.3.

## Limits and open questions

- **Generation time:** NEWA's peaks are 1,017 and 1,223 apart, Eckenrode et al.'s 1,187 and 1,257, UW's 1,270 and 1,280; the model's 1,100 fits NEWA's, so its later flights may be early for Wisconsin. Wisconsin trap counts would decide.
- **NEWA's sources:** Andaloro, Rose and Eckenrode 1984 isn't in hand; the training area's last year (1983) is an estimate.
- **The spring flight's shape** rests on two numbers (first emergence and peak); 5 % for "first emergence" is a choice.
- **The generation weights (1, 0.1, 0.5)** are a judgment: the spring generation does most of the damage to seedlings (NEWA, Eckenrode et al.); the second generation did a tenth or less of it in Ontario and was the smallest in New York, while the third damages bulbs at harvest and in storage (Eckenrode et al., Liu et al.). The papers' damage counts are single fields and years, read from figures, and the second brood's small size in New York may owe something to thrips sprays. Where onions are harvested before the third flight peaks, its 0.5 overstates the risk to the crop in the field.
- **XHT1087's first eggs at 230–280 DD40** fit none of its own numbers or NEWA's; perhaps they were counted from a different start, or on a different base. Not used.
- **The larval stage** comes from Ontario laboratory times, not from field observations in Wisconsin.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_maggots.py
uv run python scripts/fetch_newa.py                     # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_maggots.py                  # needs the archive in data/ and the station hours
uv run app/manage.py shell < scripts/maggot_normals.py  # the dates on the normals
uv run app/manage.py shell < scripts/generation_weights_normals.py  # what the generation weights change
```
