# Cabbage maggot (`cabbage-maggot`): validation

Model version 0.5, written 2026-11-21 and revised 2026-11-23 (D98; part H, H1, and round 2: three flights, generation weights); its papers read in full 2026-11-23, the generation time changed from NEWA's 850 to 1,275 DD40 the same day (version 0.4; Ben, 2026-11-23), and a fourth flight, in the fall, added after it (version 0.5; Ben, 2026-11-23). The model: `packages/agmodels/src/agmodels/insects/cabbage_maggot.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `cabbage_maggot.md` beside it. Version 0.1 was VDIFN's two windows (single sine 42.8/86 °F, (360, 600, 1521) and (1881, 2121, 3042)); this version replaces it with NEWA's model (D95).

**In short:** NEWA's cabbage maggot model as D36 curves, with a longer generation: the simple average above 40 °F from January 1, the spring flight through NEWA's 25–95 % emergence (Jyoti, Shelton and Barnard 2003, upstate New York), larval feeding timed from it, and up to four flights (New York's four, as NEWA has; Wisconsin's study trapped three) a generation of 1,275 degree days apart, the later flights weighing half as much as the spring flight in the risk. The fourth comes in the fall, from about mid-September in southern Wisconsin, and fall freezes end it partway: on the archive's weather, 2016–2025, a median 93 % of it had emerged by then at Arlington, 56 % at Hancock and 2 % at Rhinelander. NEWA's later peaks are 809 to 915 apart, but Jyoti et al. give no generation time: NEWA adds each flight's length, from its first flies to its last, to the spring peak. The paper's own weekly trap counts, on Open-Meteo's weather at Geneva counted above 40 °F, put its flights' peaks 974 to 1,597 apart (a mean of 1,212), and Wisconsin's trap study (Eckenrode and Chapman 1972) found 1,176 DD43, a median 1,350 and 1,321 DD40 on Wisconsin weather. Version 0.4 takes 1,275, the two studies' mean (D95: NEWA's own source shows its interval wrong). On the same weather at 34 Wisconsin NEWA stations the spring flight falls on NEWA's days and the later flights peak a median 15, 26 and 46 days after NEWA's (the fourth against NEWA's 3,014); on the New York trap counts the model's summer peaks fall 1 day before to 12 days after the trapped ones, NEWA's 7 to 26 days before.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA's cabbage maggot model (newa.cornell.edu, read 2026-11-21; `tmp/references/insects/notes/newa-insects.md`) | Simple average, base 40 °F, no upper, from January 1. Table 1 ("Model by J.L. Jyoti and A.M. Shelton"): spring emergence first 288 ± 15, 25 % 366, 50 % 452, 75 % 547, 95 % 697; overwintering generation ends 809; first, second and third generation 50 % at 1,261, 2,176 and 3,014. Four generations in New York; highest risk at peak emergence of the first two flights; protect seedlings, transplants and root crops around peak flights | The method and the spring curve; compared for the later flights (version 0.4 replaces its generation time) |
| Jyoti, Shelton and Barnard 2003 ([doi:10.18474/0749-8004-38.4.525](https://doi.org/10.18474/0749-8004-38.4.525); read in full, `tmp/references/insects/Jyoti, Shelton and Barnard 2003 - Cabbage maggot.pdf`) | Thirty yellow water-pan traps at the Cornell (Geneva) Fruit and Vegetable Research Farm, emptied daily from April through October 1999 and 2000. Degree days by the simple average, (max + min)/2 − 4 °C, from January 1, on the farm's NOAA station (p. 526; they cite Arnold 1960 for the formula, not for his correction table). Logistic fits to spring emergence by year and combined (Fig. 2). Spring emergence, the two years' mean (p. 529): first 160.7 ± 8.1, 10 % 176.6, 25 % 204.2, 50 % 251.3, 75 % 297.6 ± 30.4 (1999 267.2, 2000 328.1), 95 % 390.9 °C·d; 449.2 ± 1.4 from the first flies to the end of spring emergence. Later flights' emergence lasted 508.4 (F1), 465.3 (F2) and 399.1 (F3) °C·d, each counted from the flight's first increase to its end (p. 527, 529), not between flights. Four flights a year; spring and F1 peaks alike (8 to 15 flies a trap a week) and more than twice F2's or F3's (p. 529, Fig. 3); the spring and F1 generations meet the plants when they're most susceptible (p. 531). Fig. 3's weekly counts: spring peaks May 13, 1999 and May 12, 2000; F1 June 24, 1999 and June 30 to July 7, 2000; F2 August 12, 1999 and August 11, 2000 | NEWA's table is this paper's points × 1.8 (288, 318, 368, 452, 536, 704 °F·d), give or take: NEWA has 366 for 25 % (paper 368), 547 for 75 % (paper 536) and 697 for 95 % (paper 704); its 1,261, 2,176 and 3,014 are the spring 50 % (452) plus the flights' lengths (449.2, 508.4 and 465.3 °C·d × 1.8 = 809, 915 and 838). The method (NEWA's base 40 °F for the paper's 4 °C, 39.2 °F). The training area. Half the generation time, from Fig. 3's peaks (below) |
| Eckenrode and Chapman 1971 ([doi:10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079); read in full) | Growth chambers, temperatures measured in the soil at the puparia and eggs: developmental zero 42 °F for overwintered pupae (x-intercept, p. 1081) and 44.3 °F for nondiapausing ones (p. 1080), 43 °F chosen (p. 1082); first fly emergence 235, 259 and 235 DD43 at 69.1, 64.6 and 59.8 °F, mean 243 (p. 1081); egg hatch peak 82 DD above 44 °F; pre-oviposition 4 days at 70 °F with eggs hatching within 2 days (one pair, p. 1080); egg to first egg peak 41.5 days at 69.8 °F, 1,112 DD43 (p. 1083); no flies emerged at 80 °F and many aestivated at 74.3 °F; cites Harris and Svec 1966: at 66–72 °F, egg 2–4, larva 18–22, prepupa 3–5, pupa 12–25 days, pre-oviposition 6 | The larval stage's lag and duration (below) |
| Eckenrode and Chapman 1972 ([doi:10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151); read in full) | Baited cone traps at Kenosha (1965) and Arlington (1966, 1968, 1969), Wisconsin; max–min air thermal units above 43 °F with Arnold's 1960 correction (p. 152). First spring emergence 290 to 365 over five years (p. 156; Arlington 343 in 1966, 311 in 1968, 290 in 1969, when soil at 3 inches had 233, p. 155); 300 suggested for prediction. A generation 1,176: the mean of the 12 field intervals marked on Figs. 1–4 (1,032 to 1,354; Kenosha 1965's 1,032 to 1,077, mean 1,058; Arlington 1966's 1,261; Arlington 1968's 1,176; 1969's 1,227, twice), which also equals 1968's mean (p. 155). The peaks were assigned to generations with the laboratory's 1,112 in mind (p. 152), so the intervals aren't wholly independent of it. Three flights (spring, F1, F2), the F2 "not nearly so pronounced" (p. 155). Radish tunnels per 100 roots in weekly plantings (Figs. 3, 4): 1968, spring 190 then 28, F1 at most about 12, F2 at most about 4; 1969, spring 131, F1 at most about 8, F2 up to about 30; "the greatest damage occurred in the spring" (p. 155) | Half the generation time (1,176 DD43 as DD40 on Wisconsin weather, below); the three flights; a check on the spring flight |
| Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; revised 2012, UW–Madison Division of Extension, Wisconsin Horticulture (`tmp/references/insects/UW Madison XHT1087 2005 - Degree days for fruit and vegetable pests.pdf`; no DOI) | "Base temperature = 43°F; 300, 1476, 2652 DD 43 for 1st, 2nd, & 3rd generations flies"; first-generation eggs laid when the common lilac is in full bloom. No method, upper threshold, start date or source, and not said to be first or peak flies. 1,476 − 300 and 2,652 − 1,476 are both 1,176, Eckenrode and Chapman's generation, and 300 is their suggested spring number, so the table is theirs | Compared (on the normals, below). UW Vegetable Entomology's cabbage maggot page gives the same numbers, counted "after the ground has thawed", and says the first generation "appears" at 300 |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows | Replaced |
| Enviroweather (MSU; `docs/enviroweather-models.md`) | Single sine 43 °F, no upper, from March 1: emergence 300–564, spring peak 565–716, summer peaks from 1,476 and 2,652 | Compared only |

## Choices and differences

- **Degree days:** simple average above 40 °F, no upper threshold, from January 1 (NEWA; the stored total `average_40`). Jyoti et al. counted the same way above 4 °C (39.2 °F), so NEWA's points, × 1.8 but counted from 40 °F, come a little late: on Open-Meteo's weather at Geneva in 1999 and 2000 the 40 °F total ran 30 to 45 °F·d behind the 39.2 °F total by the spring peak, about a day and a half in May. Eckenrode and Chapman counted above 43 °F with Arnold's correction; on the Wisconsin stations' days their spring numbers fall on about the same days as NEWA's (below).
- **Spring flight:** PERT (230, 405, 935) DD40, fitted by least squares to NEWA's 25, 50, 75 and 95 % (residuals under a percentage point: 25.2, 50.6, 74.6, 95.4 %). Its 10, 25, 50, 75 and 95 % come at 308, 365, 450, 549 and 692 against Jyoti et al.'s 318, 368, 452, 536 and 704; NEWA's first emergence (288) falls at 5.9 % of the curve. The curve's own end (935) is earlier than the paper's complete spring emergence (160.7 + 449.2 °C·d, about 1,098 DD40), which the last few percent drawn out; NEWA's "overwintering generation ends 809 ± 3" is the paper's 449.2 ± 1.4 °C·d × 1.8, a span from first emergence read as a total from January 1.
- **Larval feeding** (a `DerivedStage`): from 245 DD40 after each fly emerges (pre-oviposition 4–6 days at about 70 °F, about 150 DD40; egg 82 DD44, about 95 DD40), for 580 DD40 (18–22 days at 66–72 °F). Laboratory days at about 70 °F turned into DD40 at 30 a day: approximate, and the lab's soil temperatures, not air.
- **Generations:** every 1,275 DD40 (version 0.4; Ben, 2026-11-23), SD 128 (10 % of a generation, as version 0.2's 85 was of 850, and about the spring flight's own SD, 125; Eckenrode and Chapman saw the spring pattern repeat in later flights, so they spread little): 50 % at 1,731, 3,007 and 4,283. The number, from the two studies that measured flights a season long:
  - **New York** (Jyoti et al.'s Fig. 3 peaks on Open-Meteo's weather at the farm, counted above 40 °F as NEWA and the model count; [below](#against-jyoti-et-als-trap-counts)): spring to F1 1,040 (1999) and 1,055 to 1,237 (2000, whose F1 peak spans two weekly samples), F1 to F2 1,597 and 974 to 1,156. With 2000's ranges at their midpoints, the four intervals average 1,212. That archive ran 4 to 11 % below the farm's station at the paper's spring points, so on the station they'd likely be longer.
  - **Wisconsin** (Eckenrode and Chapman's 1,176 DD43 with Arnold's correction, the mean of 12 field intervals from 1,032 to 1,354): on the Wisconsin NEWA stations' days (`scripts/check_maggots.py`, 66 station-seasons, the single sine above 43 °F standing in for Arnold's correction), 1,176 DD43 from our spring peak spans a median 1,350 DD40 (10th–90th percentile 1,339 to 1,367), and the next 1,176 a median 1,321 (1,301 to 1,334): a mean of about 1,335. Their peaks were assigned to generations with the laboratory's 1,112 DD43 in mind (p. 152), so the field intervals aren't wholly independent of it.
  - 1,275 is the two studies' mean, each counted once: (1,212 + 1,335) / 2 = 1,274, rounded. The New York figure is likely low and the Wisconsin figure leans on the laboratory's time, so the midpoint is a judgment between two measurements that agree within about 10 %, not a fit. The laboratory's life cycle (1,112 DD43, 41.5 days at 69.8 °F, Eckenrode and Chapman 1971) is 42.5 days at a 70 °F summer mean at 1,275 DD40, against 41.5 and 43.6 for the laboratory and field numbers (`test_maggots.py`).
  - **NEWA's 850** (809, 915 and 838 between its peaks at 1,261, 2,176 and 3,014, a least-squares fit in versions 0.2 and 0.3) isn't a measured generation time: those intervals are Jyoti et al.'s spring, F1 and F2 flights' lengths (449.2, 508.4 and 465.3 °C·d from each flight's first increase to its end, × 1.8) added to the spring peak. That reading holds only where one flight ends as the next peaks; Fig. 3 shows low counts for two to four weeks between the spring flight's decline and F1's rise. A difference from NEWA kept under D95, since NEWA's own source shows the interval wrong.
- **Four flights** (version 0.5; Ben, 2026-11-23; version 0.3 had capped them at three): New York has four (Jyoti et al.; NEWA's table), and Eckenrode and Chapman trapped three in Wisconsin (spring, F1 from early July, F2 from mid-August, small). At 1,275 a generation the fourth flight's first flies (5 %) come at 3,880 DD40 and its peak at 4,283: on the normals about September 14 and October 3 at Arlington, September 26 and November 19 at Hancock, and neither in an average year at Rhinelander, whose normal total reaches 3,729 by December 31; on the Wisconsin NEWA stations' weather its first flies came by October 15 in 60 of 67 station-seasons (2024 and 2025, two warm years). A fall flight can lay eggs on fall crucifers (late cabbage, radish, turnip), so the model shows it in part, at the later flights' weight (0.5). A fifth would start near 5,100, past any Wisconsin season.
- **What ends the fourth flight** is the engine's end of season, not the generations (`agmodels.phenology.freeze_factor`). Each flight's activity is read off its curve at the season's running total, so when fall days stop adding degree days the flight's activity holds where it is rather than falling. From day 251 (September 8, or 7 in a leap year), activity and the risk are multiplied by the freeze factor, max(0, 1 − f/4) for f days in the last 14 with a minimum at or below −2 °C (28.4 °F), held at its lowest that year so a warm spell can't bring flies back. Each freezing day takes a quarter off; once four fall within 14 days the factor is 0, the protection window closes and the season is complete. So the share of the fourth flight a season shows is the share emerged on that day ([below](#the-fourth-flight-and-fall-freezes)).
- **Generation weights** (version 0.3; Ben, 2026-11-23): flight and larval feeding weight 1, the spring generation's 1 and each later generation's 0.5 (the fall flight's too, version 0.5). NEWA (highest risk at the first two flights' peaks), Eckenrode and Chapman (radish injury, 1968–69) and A3422 all find the spring flight the most damaging. They say which flight matters; the papers, read in full, give some sizes. In New York's traps (Jyoti et al., Fig. 3) F1's peak was 0.9 to 1.0 times spring's, F2's 0.24 to 0.40 and F3's 0.05 to 0.19. In Wisconsin's (Eckenrode and Chapman, Figs. 1–4) F1's flies ran from none trapped (1969) to more than spring's (Kenosha 1965, whose spring flight was partly missed), and the radish damage in weekly plantings, which measures egg laying on an equally susceptible crop, was much smaller in summer: F1 about 0.06 of spring's peak in both years and F2 0.02 (1968) to 0.24 (1969), as read from the figures. So 0.5 is a judgment between New York's large F1 and Wisconsin's small summer damage, not a measurement. Version 0.2 weighted every generation alike (D37).
- **Action window:** "Protect seedlings and transplants during fly flight", from 5 % (NEWA's first emergence) to 95 % of each flight: 283–692 DD40 in spring.
- **Against NEWA (a difference kept, D95):** the spring flight and the method are NEWA's; the generation (1,275 against 850) is not, so the model's later flights come about two, four and six to seven weeks after NEWA's (the fourth flight against NEWA's third generation). For NEWA (courtesy email): the generation time, with Fig. 3's peaks.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 234, the first adult flight (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 15 at Madison, April 23 at Hancock, May 3 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) April 12. Where we don't have the normals it opens on April 1. It ends after October 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_maggots.py`, run in CI:

- The spring flight within a percentage point of NEWA's 25, 50, 75 and 95 % (366, 452, 547, 697), and within 15 degree days of Jyoti et al.'s 10–95 % × 1.8; NEWA's first emergence at 288 comes at 5.9 % of the flight (test: 5.9 ± 0.5 %). Against Jyoti et al.'s own points the curve's 10, 25, 50 % are within 10 degree days (308, 365, 450 against 318, 368, 452), and its 75 and 95 % within 13 (549 and 692 against 536 and 704), so the spring flight passes 10, 25, 50, 75 and 95 % emergence within 13 degree days of the paper's points.
- Later flights a generation of 1,275 apart (1,281 and 1,277 between the curves' midpoints, test: within 7), half emerged at 1,731, 3,007 and 4,283, where NEWA's table has 1,261, 2,176 and 3,014, built by adding each flight's length to the spring peak (above). Both have four flights; the fourth comes in the fall, and freezes end it partway (Choices above). The fourth flight's first flies come at 3,880 and its window runs 3,880 to 4,717 until freezes close it. The generation is the mean of New York's 1,212 and Wisconsin's 1,335 (test: within 5).
- The later flights weigh half the spring flight in the risk (a judgment); the spring generation's risk is unchanged.
- On made-up weather that stops adding degree days with the fourth flight part emerged, its activity, window and risk hold until a fourth freezing day in 14 (after day 250), then fall to 0 and stay there.
- The protection window opens at 283 and closes at 692 in spring (NEWA's 288 and 697).
- Half the spring flight's larvae have begun feeding by about 700 DD40.

### Against Eckenrode and Chapman 1972

`scripts/check_maggots.py` (station days, the single sine above 43 °F without an upper standing in for Arnold's correction), 67 station-seasons:

- Spring: the station's DD43 reaches 290 a median 2 days after our first flies (5.9 %; 10th–90th percentile 0 to 5) and 365 a median 9 days after (6 to 13). So Wisconsin's spring flies first emerged at 290 to 365 degree days above 43 °F, about the same days as the model's first flies at 288 above 40 °F, or up to about 9 days later.
- Generations: Wisconsin's generations took 1,176 degree days above 43 °F. From our spring peak, 1,176 DD43 spans a median 1,350 DD40 (1,339 to 1,367) on these stations' weather, and the next 1,176 a median 1,321 (1,301 to 1,334). Between our spring and first summer peaks the stations now accumulate a median 1,131 DD43 (1,115 to 1,148; version 0.3: 742), so the model's 1,275 puts the first summer flight a median 2 days before their generation would (1 to 3; version 0.3: 16 days before).
- Flights: they trapped three flights at Arlington (spring, F1 from early July, F2 from mid-August, small); the model has a fourth, in the fall, as New York has. Its first flies (3,880 DD40) came by October 15 in 60 of 67 station-seasons.

### Against NEWA on the same weather

`scripts/check_maggots.py`; full table in [cabbage-maggot/newa.md](cabbage-maggot/newa.md). NEWA's model is recomputed from its published rules (`scripts/newa_reference.py`: the simple average above 40 °F from January 1, the first day reaching each event) on the hours of 34 Wisconsin NEWA stations, 2024 and 2025 (67 station-seasons). Ours run on the same daily max and min, and on the archive at each station's cell.

<!-- prettier-ignore -->
| Ours − NEWA's, days | Station days: median (10th–90th percentile; range) | Archive: median (10th–90th percentile) |
| --- | --- | --- |
| First emergence (288; ours 5.9 %) | 0 (0 to 0; 0 to 0) | 0 (−3 to +2) |
| Spring 25, 50, 75, 95 % | 0 (within a day) | 0 (−3 to +2) |
| First generation peak (1,261; ours 1,731) | +15 (+13 to +17; +12 to +18) | +15 (+12 to +18) |
| Second generation peak (2,176; ours 3,007) | +26 (+25 to +30; +23 to +36) | +27 (+23 to +32) |
| Third generation peak (3,014; ours, the fourth flight, 4,283) | +46 (+44 to +52; +39 to +65), n = 58 | +46 (+42 to +53), n = 59 |

The spring flight reproduces NEWA's: first emergence and its 25 to 95 % points fall on NEWA's day at the median. The later flights peak a median 15, 26 and 46 days after NEWA's, by design: the model's generation is 1,275 degree days, NEWA's 850. (Version 0.3, on NEWA's 850, had the first two within a day or two, and no fourth.) NEWA's third generation peak (3,014), which version 0.4 had no counterpart for, came between July 28 and September 14 on these stations' days (median August 8); the model's fourth flight reached half emerged between September 5 and October 28 (median September 23) in the 58 station-seasons whose degree days got there by year's end. The count ignores freezes, which end some of those seasons first ([below](#the-fourth-flight-and-fall-freezes)). On the archive the spread is the grid's weather against the station's, ±3 days for most.

### Against Jyoti et al.'s trap counts

Jyoti et al. give no degree days for the summer flights' peaks, only the dates in their Fig. 3 (weekly means of 30 traps). Their degree days, recomputed on Open-Meteo's archive (ERA5) at the farm (42.88 °N, 77.03 °W; daily max and min, the simple average above 4 °C and above 40 °F from January 1, fetched 2026-11-23): this archive ran 4 to 11 % below the farm's station at the paper's spring points (1999: 137, 229 and 380 against the paper's 152.7, 247.8 and 401.0 °C·d at first, 50 % and 95 %; 2000: 150, 244 and 350 against 168.8, 254.9 and 380.8), so on the station the intervals below would be a little longer still.

<!-- prettier-ignore -->
| Peak (Fig. 3) | 1999: date, total °C·d above 4 °C (°F·d) / °F·d above 40 °F | 2000: date, total °C·d above 4 °C (°F·d) / °F·d above 40 °F |
| --- | --- | --- |
| Spring | May 13: 253 (455) / 417 | May 12: 316 (569) / 524 |
| F1 | June 24: 850 (1,530) / 1,457 | June 30 to July 7: 924 to 1,028 (1,663 to 1,850) / 1,579 to 1,761 |
| F2 | August 12: 1,759 (3,166) / 3,054 | August 11: 1,585 (2,853) / 2,735 |
| Spring to F1 | 597 (1,075) / 1,040 | 608 to 712 (1,094 to 1,282) / 1,055 to 1,237 |
| F1 to F2 | 909 (1,636) / 1,597 | 557 to 661 (1,003 to 1,190) / 974 to 1,156 |

Counted above 40 °F, the paper's own flights peaked 974 to 1,597 degree days apart (a mean of 1,212 with 2000's ranges at their midpoints), against NEWA's 809 to 915 and the model's 1,275. On these 40 °F totals:

<!-- prettier-ignore -->
| Peak | Trapped | Model (version 0.4) | NEWA |
| --- | --- | --- | --- |
| F1, 1999 | June 24 | July 3 (1,731): +9 days | June 17 (1,261): −7 days |
| F1, 2000 | June 30 to July 7 | July 6: within the span | June 19: −11 to −18 days |
| F2, 1999 | August 12 | August 11 (3,007): −1 day | July 17 (2,176): −26 days |
| F2, 2000 | August 11 | August 23: +12 days | July 24: −18 days |

The model's summer peaks fall 1 day before to 12 days after the trapped ones; NEWA's fall 7 to 26 days before them. Weekly samples put each trapped peak within about 3 days. The spring peak (450) came May 15, 1999 and May 9, 2000 on these totals, within 3 days of the trapped ones. NEWA's derivation reads each flight's length as the time to the next peak, which holds only where one flight ends as the next begins; Fig. 3 shows low counts for two to four weeks between the spring flight's decline and F1's rise.

### On the normals

`scripts/maggot_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (DD40, simple average, from January 1), version 0.5 and, where it moved, version 0.3 (version 0.4's first three flights fall on the same days as 0.5's). A typical-year calendar, not a forecast, and without fall freezes.

<!-- prettier-ignore -->
| Event (DD40, version 0.5; version 0.3) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First flies, 5.9 % (288) | May 1 | May 6 | May 13 |
| Spring flight 50 % (450) | May 12 | May 17 | May 25 |
| Spring flight 95 % (692) | May 25 | May 30 | June 6 |
| Second flight 50 % (1,731; 1,304) | July 3 (June 18) | July 8 (June 23) | July 17 (July 1) |
| Third flight 50 % (3,007; 2,156) | August 13 (July 17) | August 20 (July 22) | September 4 (August 1) |
| Protection windows, second flight (1,458–2,046; 1,082–1,578) | June 24–July 13 (June 10–28) | June 28–July 18 (June 15–July 2) | July 7–28 (June 23–July 11) |
| Protection windows, third flight (2,663–3,386; 1,892–2,462) | August 1–26 (July 8–26) | August 8–September 3 (July 13–August 1) | August 21–September 24 (July 23–August 13) |
| Fourth flight's first flies, 5 % (3,880; version 0.3 had no fourth, 2,707 without its cap) | September 14 (August 3) | September 26 (August 9) | not reached (August 23) |
| Fourth flight 50 % (4,283) | October 3 | November 19 | not reached |
| Protection window, fourth flight (3,880–4,717) | September 14 until freezes end the season | September 26 until freezes end the season | none |
| Share of the fourth flight emerged, October 1 / October 15 / December 31 | 45 % / 73 % / 92 % | 10 % / 27 % / 52 % | 0 / 0 / 1 % |
| Normal total on October 15 / December 31 | 4,438 / 4,649 | 4,130 / 4,294 | 3,622 / 3,729 |

UW–Madison: Delahaut's XHT1087 gives 300, 1,476 and 2,652 DD43 for the first, second and third generations' flies (no start or method), and UW Vegetable Entomology's page the same, counted after the ground has thawed, the first generation appearing at 300; Lowenstein and Groves (topic page) put the first flies in mid-May while yellow rocket flowers, a second generation in late June and a third in a long, warm season. The 1,176 between XHT1087's numbers is Eckenrode and Chapman's generation, as the model's 1,275 DD40 nearly is, so the model's flights now come where UW's table would put them: its first flies in early May in the south and mid-May in the north, its second flight half emerged in early to mid-July (the flight's first flies, 5 %, at 1,458: June 24 at Arlington, near UW's late June), and its third in mid-August to early September. UW's table has no fourth flight.

#### The fourth flight and fall freezes

The normals have no freezes, so how much of the fourth flight a season shows comes from each year's weather: the model on the archive's daily max and min at each place's cell, 2016–2025, with the engine's freeze factor (a scratch script, 2026-11-23; the recipe is under Reproducing). Each cell: the fourth flight's first flies (5 %), the day freezes end the season (the factor reaches 0), and the share of the fourth flight emerged that day.

<!-- prettier-ignore -->
| Year | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| 2016 | September 6; November 21, 100 % | September 22; November 19, 81 % | October 19; November 19, 13 % |
| 2017 | September 19; November 6, 91 % | September 28; November 3, 49 % | none; November 1, 0 % |
| 2018 | September 9; October 21, 81 % | September 18; October 18, 35 % | October 10; October 18, 5 % |
| 2019 | September 21; October 31, 59 % | October 10; October 29, 9 % | none; October 29, 0 % |
| 2020 | September 24; October 28, 32 % | none; October 19, 3 % | none; October 19, 0 % |
| 2021 | September 6; November 10, 99 % | September 17; November 2, 87 % | October 10; November 1, 17 % |
| 2022 | September 17; November 16, 82 % | October 2; October 27, 23 % | none; November 13, 1 % |
| 2023 | September 10; November 2, 95 % | September 22; October 31, 68 % | none; November 1, 3 % |
| 2024 | September 6; November 26, 100 % | September 19; November 21, 89 % | October 29; November 23, 9 % |
| 2025 | September 13; November 10, 97 % | September 25; November 1, 63 % | none; November 5, 1 % |
| Median | September 11; November 8, 93 % (32 to 100 %) | September 22 (9 of 10 years); November 1, 56 % (3 to 89 %) | 4 of 10 years; November 1, 2 % (0 to 17 %) |

At Arlington the fourth flight starts every year, in early to late September, and in half the years it had all but finished emerging (95 % or more) before freezes ended the season in late October or November; its window then closed at 95 %, between October 10 and 26. At Hancock it starts in most years, from mid-September to early October, and freezes end it about halfway. At Rhinelander it starts in about four years in ten, in October, and the season ends with a few percent emerged. The risk while it emerged (with the third flight's last larvae) peaked at 0.31 to 0.42 at Arlington and 0.28 to 0.41 at Hancock (Moderate, the most a weight-0.5 flight reaches), and 0.21 to 0.28 at Rhinelander in the years it started (Low to Moderate). 2020's archive is missing 8 days.

#### What the weights change

`uv run app/manage.py shell < scripts/generation_weights_normals.py`: the risk on the same normal totals with every generation alike and with the summer flights at 0.5, on version 0.4's timing (three flights; version 0.5's fourth flight adds a fall peak, at most 0.42, Moderate, on the archive's years above), at each peak of the risk through October 15, without fall freezes.

<!-- prettier-ignore -->
| Place | Peak | Equal generations | Weighted |
| --- | --- | --- | --- |
| Arlington | May 8 (spring flight) | 1.00 (Very high) | 1.00 (Very high) |
| Arlington | June 9 (spring larvae) | 1.00 (Very high) | 1.00 (Very high) |
| Arlington | July 4 (second flight) | 0.81 (Very high) | 0.41 (Moderate) |
| Arlington | July 19 (its larvae) | 0.92 (Very high) | 0.46 (Moderate) |
| Arlington | August 28 (third flight's larvae) | 0.87 (Very high) | 0.43 (Moderate) |
| Arlington | Days at High or above | 120 | 49 |
| Hancock | May 13 | 1.00 (Very high) | 1.00 (Very high) |
| Hancock | June 13 | 1.00 (Very high) | 1.00 (Very high) |
| Hancock | July 9 | 0.81 (Very high) | 0.41 (Moderate) |
| Hancock | July 24 | 0.91 (Very high) | 0.46 (Moderate) |
| Hancock | September 6 | 0.87 (Very high) | 0.43 (Moderate) |
| Hancock | Days at High or above | 126 | 48 |
| Rhinelander | May 21 | 1.00 (Very high) | 1.00 (Very high) |
| Rhinelander | June 21 | 1.00 (Very high) | 1.00 (Very high) |
| Rhinelander | July 18 | 0.81 (Very high) | 0.41 (Moderate) |
| Rhinelander | August 4 | 0.92 (Very high) | 0.46 (Moderate) |
| Rhinelander | September 29 | 0.87 (Very high) | 0.43 (Moderate) |
| Rhinelander | Days at High or above | 140 | 49 |

The spring generation stays Very high through its larvae (to mid-June in the south); the summer flights and their larvae peak at Moderate. With the longer generation the second flight no longer overlaps the spring larvae, so a season has about 49 days at High or above (version 0.3: 70 to 74, from the overlap).

## Limits and open questions

- **Generation time:** 1,275 DD40 is the mean of two studies, New York's trap counts on Open-Meteo's weather (1,212, likely a little low) and Wisconsin's 1,176 DD43 converted on recent station weather (about 1,335), each a handful of seasons; the intervals vary from about 970 to 1,600. Wisconsin trap counts (UW Vegetable Entomology, DATCP) would check it.
- **The fourth flight:** New York's four flights (NEWA; Jyoti et al.), where Wisconsin's study trapped three (the third small). No Wisconsin source counts a fall flight, so the fourth flight's size and timing are New York's pattern carried over. How much of it shows is set by the engine's end-of-season rule (four days at or below −2 °C within 14 days, after day 250), which is shared by every insect and not measured for cabbage maggot; it doesn't model flies stopping for other reasons in the fall. Fall trap counts in Wisconsin would check it.
- **Spring emergence's end:** the curve ends at 935 where Jyoti et al. found complete emergence near 1,098; a few late flies are left out.
- **The later flights' weight (0.5)** is a judgment: the sources say the spring flight does most of the damage (NEWA; Eckenrode and Chapman's radish injury; A3422). The papers' figures give sizes that disagree with each other (New York's F1 flight as large as spring's, Wisconsin's summer radish damage a few to 24 % of spring's; Choices above), so neither fixes the weight.
- **The larval stage** comes from laboratory days at about 70 °F turned into degree days, not from field observations.
- **Jyoti et al.'s method** is the simple average above 4 °C from January 1 on the farm's NOAA station (p. 526), as NEWA computes, except that NEWA counts from 40 °F (39.2 °F in the paper), about a day and a half later by the spring peak.
- For NEWA (courtesy email): the 75 % point (547 against the paper's 536; 25 % and 95 % are 2 and 7 off too), "overwintering generation ends 809", which is the paper's span from first emergence, the later peaks built from the flights' lengths, which the paper's Fig. 3 puts 7 to 26 days early in its own years (counted above 40 °F), and the base of 40 °F for the paper's 4 °C.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_maggots.py
uv run python scripts/fetch_newa.py                     # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_maggots.py                  # needs the archive in data/ and the station hours
uv run app/manage.py shell < scripts/maggot_normals.py  # the dates on the normals, versions 0.5 and 0.3
uv run app/manage.py shell < scripts/generation_weights_normals.py  # what the generation weights change
```

The fourth flight against fall freezes: for each year 2016–2025 and each place, the archive's daily max and min at the place's cell (`NDFD.cell_of`, `GridStore.read_point`) run through `PhenologyModel(insect=cabbage_maggot.INSECT).outputs` with the day of year (`runner._context`); the season's end is the first day `freeze_factor` is 0, and the share of the fourth flight emerged is `generations_adult_flight` − 3 that day.

The check against Jyoti et al.'s trap counts: Open-Meteo's archive (`archive-api.open-meteo.com/v1/archive?latitude=42.88&longitude=-77.03&start_date=1999-01-01&end_date=2000-12-31&daily=temperature_2m_max,temperature_2m_min&timezone=America/New_York`), each year's running total of max(0, (max + min)/2 − 4) °C and of max(0, (max + min)/2 − 40) °F from January 1, read on Fig. 3's peak dates.
