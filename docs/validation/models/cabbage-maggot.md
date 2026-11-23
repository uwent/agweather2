# Cabbage maggot (`cabbage-maggot`): validation

Model version 0.3, written 2026-11-21 and revised 2026-11-23 (D98; part H, H1, and round 2: three flights, generation weights); its papers read in full 2026-11-23, with no change to the model. The model: `packages/agmodels/src/agmodels/insects/cabbage_maggot.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `cabbage_maggot.md` beside it. Version 0.1 was VDIFN's two windows (single sine 42.8/86 °F, (360, 600, 1521) and (1881, 2121, 3042)); this version replaces it with NEWA's model (D95).

**In short:** NEWA's cabbage maggot model as D36 curves: the simple average above 40 °F from January 1, the spring flight through NEWA's 25–95 % emergence (Jyoti, Shelton and Barnard 2003, upstate New York), larval feeding timed from it, and up to three flights 850 degree days apart (Wisconsin's three, where NEWA has New York's four), the summer flights weighing half as much as the spring flight in the risk. On the same weather at 34 Wisconsin NEWA stations it reproduces NEWA's events to a day or two. Wisconsin's own trap study (Eckenrode and Chapman 1972) agrees on the spring flight but found generations about half again as long as NEWA's (about 1,300 DD40 against 850), which would put the first summer flight about two weeks later and later flights later still. Read in full (2026-11-23), Jyoti et al. give no generation time: NEWA's later peaks add each flight's length, from its first flies to its last, to the spring peak, and the paper's own weekly trap counts, on Open-Meteo's weather at Geneva, put the spring and first summer peaks 1,075 to 1,282 °F·d apart, near Wisconsin's interval rather than NEWA's 809 (below). The model still follows NEWA (no change without Ben), and its page says Wisconsin's summer flights may come later.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA's cabbage maggot model (newa.cornell.edu, read 2026-11-21; `tmp/references/insects/notes/newa-insects.md`) | Simple average, base 40 °F, no upper, from January 1. Table 1 ("Model by J.L. Jyoti and A.M. Shelton"): spring emergence first 288 ± 15, 25 % 366, 50 % 452, 75 % 547, 95 % 697; overwintering generation ends 809; first, second and third generation 50 % at 1,261, 2,176 and 3,014. Four generations in New York; highest risk at peak emergence of the first two flights; protect seedlings, transplants and root crops around peak flights | The method, the spring curve, the generation time and the number of flights |
| Jyoti, Shelton and Barnard 2003 ([doi:10.18474/0749-8004-38.4.525](https://doi.org/10.18474/0749-8004-38.4.525); read in full, `tmp/references/insects/Jyoti, Shelton and Barnard 2003 - Cabbage maggot.pdf`) | Thirty yellow water-pan traps at the Cornell (Geneva) Fruit and Vegetable Research Farm, emptied daily from April through October 1999 and 2000. Degree days by the simple average, (max + min)/2 − 4 °C, from January 1, on the farm's NOAA station (p. 526; they cite Arnold 1960 for the formula, not for his correction table). Logistic fits to spring emergence by year and combined (Fig. 2). Spring emergence, the two years' mean (p. 529): first 160.7 ± 8.1, 10 % 176.6, 25 % 204.2, 50 % 251.3, 75 % 297.6 ± 30.4 (1999 267.2, 2000 328.1), 95 % 390.9 °C·d; 449.2 ± 1.4 from the first flies to the end of spring emergence. Later flights' emergence lasted 508.4 (F1), 465.3 (F2) and 399.1 (F3) °C·d, each counted from the flight's first increase to its end (p. 527, 529), not between flights. Four flights a year; spring and F1 peaks alike (8 to 15 flies a trap a week) and more than twice F2's or F3's (p. 529, Fig. 3); the spring and F1 generations meet the plants when they're most susceptible (p. 531). Fig. 3's weekly counts: spring peaks May 13, 1999 and May 12, 2000; F1 June 24, 1999 and June 30 to July 7, 2000; F2 August 12, 1999 and August 11, 2000 | NEWA's table is this paper's points × 1.8 (288, 318, 368, 452, 536, 704 °F·d), give or take: NEWA has 366 for 25 % (paper 368), 547 for 75 % (paper 536) and 697 for 95 % (paper 704); its 1,261, 2,176 and 3,014 are the spring 50 % (452) plus the flights' lengths (449.2, 508.4 and 465.3 °C·d × 1.8 = 809, 915 and 838). The method (NEWA's base 40 °F for the paper's 4 °C, 39.2 °F). The training area. A check of the generation time on Fig. 3 (below) |
| Eckenrode and Chapman 1971 ([doi:10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079); read in full) | Growth chambers, temperatures measured in the soil at the puparia and eggs: developmental zero 42 °F for overwintered pupae (x-intercept, p. 1081) and 44.3 °F for nondiapausing ones (p. 1080), 43 °F chosen (p. 1082); first fly emergence 235, 259 and 235 DD43 at 69.1, 64.6 and 59.8 °F, mean 243 (p. 1081); egg hatch peak 82 DD above 44 °F; pre-oviposition 4 days at 70 °F with eggs hatching within 2 days (one pair, p. 1080); egg to first egg peak 41.5 days at 69.8 °F, 1,112 DD43 (p. 1083); no flies emerged at 80 °F and many aestivated at 74.3 °F; cites Harris and Svec 1966: at 66–72 °F, egg 2–4, larva 18–22, prepupa 3–5, pupa 12–25 days, pre-oviposition 6 | The larval stage's lag and duration (below) |
| Eckenrode and Chapman 1972 ([doi:10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151); read in full) | Baited cone traps at Kenosha (1965) and Arlington (1966, 1968, 1969), Wisconsin; max–min air thermal units above 43 °F with Arnold's 1960 correction (p. 152). First spring emergence 290 to 365 over five years (p. 156; Arlington 343 in 1966, 311 in 1968, 290 in 1969, when soil at 3 inches had 233, p. 155); 300 suggested for prediction. A generation 1,176: the mean of the 12 field intervals marked on Figs. 1–4 (1,032 to 1,354; Kenosha 1965's 1,032 to 1,077, mean 1,058; Arlington 1966's 1,261; Arlington 1968's 1,176; 1969's 1,227, twice), which also equals 1968's mean (p. 155). The peaks were assigned to generations with the laboratory's 1,112 in mind (p. 152), so the intervals aren't wholly independent of it. Three flights (spring, F1, F2), the F2 "not nearly so pronounced" (p. 155). Radish tunnels per 100 roots in weekly plantings (Figs. 3, 4): 1968, spring 190 then 28, F1 at most about 12, F2 at most about 4; 1969, spring 131, F1 at most about 8, F2 up to about 30; "the greatest damage occurred in the spring" (p. 155) | A check (below); the three flights |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows | Replaced |
| Enviroweather (MSU; `docs/enviroweather-models.md`) | Single sine 43 °F, no upper, from March 1: emergence 300–564, spring peak 565–716, summer peaks from 1,476 and 2,652 | Compared only |

## Choices and differences

- **Degree days:** simple average above 40 °F, no upper threshold, from January 1 (NEWA; the stored total `average_40`). Jyoti et al. counted the same way above 4 °C (39.2 °F), so NEWA's points, × 1.8 but counted from 40 °F, come a little late: on Open-Meteo's weather at Geneva in 1999 and 2000 the 40 °F total ran 30 to 45 °F·d behind the 39.2 °F total by the spring peak, about a day and a half in May. Eckenrode and Chapman counted above 43 °F with Arnold's correction; on the Wisconsin stations' days their spring numbers fall on about the same days as NEWA's (below).
- **Spring flight:** PERT (230, 405, 935) DD40, fitted by least squares to NEWA's 25, 50, 75 and 95 % (residuals under a percentage point: 25.2, 50.6, 74.6, 95.4 %). Its 10, 25, 50, 75 and 95 % come at 308, 365, 450, 549 and 692 against Jyoti et al.'s 318, 368, 452, 536 and 704; NEWA's first emergence (288) falls at 5.9 % of the curve. The curve's own end (935) is earlier than the paper's complete spring emergence (160.7 + 449.2 °C·d, about 1,098 DD40), which the last few percent drawn out; NEWA's "overwintering generation ends 809 ± 3" is the paper's 449.2 ± 1.4 °C·d × 1.8, a span from first emergence read as a total from January 1.
- **Larval feeding** (a `DerivedStage`): from 245 DD40 after each fly emerges (pre-oviposition 4–6 days at about 70 °F, about 150 DD40; egg 82 DD44, about 95 DD40), for 580 DD40 (18–22 days at 66–72 °F). Laboratory days at about 70 °F turned into DD40 at 30 a day: approximate, and the lab's soil temperatures, not air.
- **Generations:** every 850 DD40 (the least-squares fit to NEWA's peaks, 809, 915 and 838 apart, which are Jyoti et al.'s spring, F1 and F2 flights' lengths × 1.8, read as the time between peaks: 50 % at 1,304, 2,156 and 3,007 against 1,261, 2,176 and 3,014), SD 85 (10 %; Eckenrode and Chapman saw the spring pattern repeat in later flights, so they spread little). At most three flights (version 0.3; Ben, 2026-11-23): Eckenrode and Chapman's Wisconsin count (spring, F1 from early July, F2 from mid-August, small). Version 0.2 allowed New York's four (NEWA, Jyoti et al.), which put a fourth flight in southern Wisconsin in mid-August (below), where Wisconsin's study found the small third; NEWA's own table has no timing for a fourth flight's end, only its peak.
- **Generation weights** (version 0.3; Ben, 2026-11-23): flight and larval feeding weight 1, the spring generation's 1 and each summer generation's 0.5. NEWA (highest risk at the first two flights' peaks), Eckenrode and Chapman (radish injury, 1968–69) and A3422 all find the spring flight the most damaging. They say which flight matters; the papers, read in full, give some sizes. In New York's traps (Jyoti et al., Fig. 3) F1's peak was 0.9 to 1.0 times spring's, F2's 0.24 to 0.40 and F3's 0.05 to 0.19. In Wisconsin's (Eckenrode and Chapman, Figs. 1–4) F1's flies ran from none trapped (1969) to more than spring's (Kenosha 1965, whose spring flight was partly missed), and the radish damage in weekly plantings, which measures egg laying on an equally susceptible crop, was much smaller in summer: F1 about 0.06 of spring's peak in both years and F2 0.02 (1968) to 0.24 (1969), as read from the figures. So 0.5 is a judgment between New York's large F1 and Wisconsin's small summer damage, not a measurement. Version 0.2 weighted every generation alike (D37).
- **Action window:** "Protect seedlings and transplants during fly flight", from 5 % (NEWA's first emergence) to 95 % of each flight: 283–692 DD40 in spring.
- **Against Eckenrode and Chapman 1972 (a difference kept, D95):** their Wisconsin generation, 1,176 DD43 (12 intervals, 1,032 to 1,354), is about 1,300 DD40 in summer, half again NEWA's 850. Their laboratory life cycle (1,112 DD43, 41.5 days at 69.8 °F) supports the longer time. NEWA's 850 isn't a measured generation time: Jyoti et al. report how long each flight lasted, and NEWA's table adds those lengths to the spring peak. Their own trap counts put the peaks about as far apart as Wisconsin's ([below](#against-jyoti-et-als-trap-counts)), so the papers agree with each other and disagree with NEWA's reading of them. The model keeps NEWA's 850 until Ben decides (D95: NEWA wins unless a published source shows it wrong; here its own source does).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_maggots.py`, run in CI:

- The spring flight within a percentage point of NEWA's 25, 50, 75 and 95 % (366, 452, 547, 697), and within 15 degree days of Jyoti et al.'s 10–95 % × 1.8; NEWA's first emergence at 288 comes at 5.9 % of the flight (test: 5.9 ± 0.5 %). Against Jyoti et al.'s own points the curve's 10, 25, 50 % are within 10 degree days (308, 365, 450 against 318, 368, 452), and its 75 and 95 % within 13 (549 and 692 against 536 and 704), so the spring flight passes 10, 25, 50, 75 and 95 % emergence within 13 degree days of the paper's points.
- Later flights' 50 % at 1,304 and 2,156, within 45 degree days of NEWA's 1,261 and 2,176; three flights and no fourth, where NEWA has a fourth (3,014). So the second and third flights are half emerged within 45 degree days of NEWA's 1,261 and 2,176.
- The summer flights weigh half the spring flight in the risk (a judgment); the spring generation's risk is unchanged.
- The protection window opens at 283 and closes at 692 in spring (NEWA's 288 and 697).
- Half the spring flight's larvae have begun feeding by about 700 DD40.

### Against Eckenrode and Chapman 1972

`scripts/check_maggots.py` (station days, the single sine above 43 °F without an upper standing in for Arnold's correction), 67 station-seasons:

- Spring: the station's DD43 reaches 290 a median 2 days after our first flies (5.9 %; 10th–90th percentile 0 to 5) and 365 a median 9 days after (6 to 13). So Wisconsin's spring flies first emerged at 290 to 365 degree days above 43 °F, about the same days as NEWA's 288 above 40 °F, or up to about 9 days later.
- Generations: between our spring and first summer peaks the stations accumulated a median 742 DD43 (728 to 760), against their 1,176. By their generation time the first summer peak would come a median 16 days later (13 to 18). Eckenrode and Chapman's generations took 1,176 degree days above 43 °F, about half again as long as NEWA's 850 above 40 °F (about 1,300 at 40 °F); the model follows NEWA.
- Flights: they trapped three flights at Arlington (spring, F1 from early July, F2 from mid-August, small); the model stops at three since version 0.3 (version 0.2 had a fourth in mid-August in southern Wisconsin's normal season).

### Against NEWA on the same weather

`scripts/check_maggots.py`; full table in [cabbage-maggot/newa.md](cabbage-maggot/newa.md). NEWA's model is recomputed from its published rules (`scripts/newa_reference.py`: the simple average above 40 °F from January 1, the first day reaching each event) on the hours of 34 Wisconsin NEWA stations, 2024 and 2025 (67 station-seasons). Ours run on the same daily max and min, and on the archive at each station's cell.

<!-- prettier-ignore -->
| Ours − NEWA's, days | Station days: median (10th–90th percentile; range) | Archive: median (10th–90th percentile) |
| --- | --- | --- |
| First emergence (288; ours 5.9 %) | 0 (0 to 0; 0 to 0) | 0 (−3 to +2) |
| Spring 25, 50, 75, 95 % | 0 (within a day) | 0 (−3 to +2) |
| First generation peak (1,261) | +1 (+1 to +2; +1 to +3) | +1 (−1 to +4) |
| Second generation peak (2,176) | −1 (−1 to 0) | −1 (−4 to +2) |
| Third generation peak (3,014; version 0.2, which had a fourth flight) | 0 (−1 to 0) | 0 (−4 to +2) |

The model reproduces NEWA's events: first emergence, the spring peak and each later peak it has fall within a day or two of NEWA's on the same weather (since version 0.3 it stops at three flights, so NEWA's fourth, its third generation, has no counterpart) (the first generation's 1 to 3 days late, from the 43-degree-day difference in its peak). On the archive the spread is the grid's weather against the station's, ±3 days for most.

### Against Jyoti et al.'s trap counts

Jyoti et al. give no degree days for the summer flights' peaks, only the dates in their Fig. 3 (weekly means of 30 traps). Their degree days, recomputed on Open-Meteo's archive (ERA5) at the farm (42.88 °N, 77.03 °W; daily max and min, the simple average above 4 °C from January 1, fetched 2026-11-23): this archive ran 4 to 11 % below the farm's station at the paper's spring points (1999: 137, 229 and 380 against the paper's 152.7, 247.8 and 401.0 at first, 50 % and 95 %; 2000: 150, 244 and 350 against 168.8, 254.9 and 380.8), so on the station the intervals below would be a little longer still.

<!-- prettier-ignore -->
| Peak (Fig. 3) | 1999: date, total °C·d (°F·d) | 2000: date, total °C·d (°F·d) |
| --- | --- | --- |
| Spring | May 13: 253 (455) | May 12: 316 (569) |
| F1 | June 24: 850 (1,530) | June 30 to July 7: 924 to 1,028 (1,663 to 1,850) |
| F2 | August 12: 1,759 (3,166) | August 11: 1,585 (2,853) |
| Spring to F1 | 597 (1,075) | 608 to 712 (1,094 to 1,282) |
| F1 to F2 | 909 (1,636) | 557 to 661 (1,003 to 1,190) |

The paper's own flights peaked 1,075 to 1,282 °F·d apart from spring to F1, against NEWA's 809 and the model's 850, and close to Eckenrode and Chapman's (1972) Wisconsin generation of 1,176 DD43 (about 1,300 DD40). NEWA's later peaks thus fall 10 to 29 days before the trapped ones. On these totals NEWA's F1 peak (1,261 °F·d, 700 °C·d) falls on June 14, 1999 and June 16, 2000, 10 to 21 days before the trapped peaks; its F2 peak (2,176, 1,209 °C·d) on July 14 and July 20, 22 to 29 days before them. Weekly samples put each peak within about 3 days. NEWA's derivation reads each flight's length as the time to the next peak, which holds only where one flight ends as the next begins; Fig. 3 shows low counts for two to four weeks between the spring flight's decline and F1's rise.

### On the normals

`scripts/maggot_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (DD40, simple average, from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD40) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First flies, 5.9 % (288) | May 1 | May 5 | May 13 |
| Spring flight 50 % (450) | May 12 | May 17 | May 25 |
| Spring flight 95 % (692) | May 25 | May 30 | June 6 |
| Second flight 50 % (1,304) | June 18 | June 23 | July 1 |
| Third flight 50 % (2,156) | July 17 | July 22 | August 1 |
| Fourth flight 50 % (3,007; version 0.2 only) | August 13 | August 20 | September 4 |
| Normal total on October 15 | 4,438 | 4,130 | 3,622 |

UW–Madison (topic page): first flies in mid-May while yellow rocket flowers, a second generation in late June, a third in a long, warm season; at 43 °F from thaw, 300, 1,476 and 2,652. The model's first flies come in early May in the south and mid-May in the north, its second flight in UW's late June, and its third (its last since version 0.3) in mid-July to early August, where UW's description has a third.

#### What the weights change

`uv run app/manage.py shell < scripts/generation_weights_normals.py`: the risk on the same normal totals with every generation alike (version 0.2's weights, three flights) and with version 0.3's (summer flights 0.5), at each peak of the risk through October 15, without fall freezes.

<!-- prettier-ignore -->
| Place | Peak | Equal generations | Weighted |
| --- | --- | --- | --- |
| Arlington | May 8 (spring flight) | 1.00 (Very high) | 1.00 (Very high) |
| Arlington | June 14 (spring larvae, second flight) | 1.48 (Very high) | 1.11 (Very high) |
| Arlington | July 12 | 1.38 (Very high) | 0.69 (High) |
| Arlington | August 1 | 0.92 (Very high) | 0.46 (Moderate) |
| Arlington | Days at High or above | 104 | 70 |
| Hancock | May 13 | 1.00 (Very high) | 1.00 (Very high) |
| Hancock | June 18 | 1.48 (Very high) | 1.12 (Very high) |
| Hancock | July 18 | 1.38 (Very high) | 0.69 (High) |
| Hancock | August 8 | 0.92 (Very high) | 0.46 (Moderate) |
| Hancock | Days at High or above | 106 | 70 |
| Rhinelander | May 21 | 1.00 (Very high) | 1.00 (Very high) |
| Rhinelander | June 26 | 1.48 (Very high) | 1.12 (Very high) |
| Rhinelander | July 28 | 1.38 (Very high) | 0.69 (High) |
| Rhinelander | August 21 | 0.92 (Very high) | 0.46 (Moderate) |
| Rhinelander | Days at High or above | 114 | 74 |

The spring generation stays Very high; the summer flights fall from Very high to High, and the third flight's tail to Moderate, so a season has about five fewer weeks at High or above.

## Limits and open questions

- **Generation time:** NEWA's 850 DD40 against Eckenrode and Chapman's 1,176 DD43 in Wisconsin (and the lab's 1,112), two weeks apart by the first summer flight. Read in full, NEWA's own source doesn't support 850: its flights' lengths became NEWA's intervals, and its trap counts put the spring and F1 peaks 1,075 to 1,282 °F·d apart on Open-Meteo's weather ([above](#against-jyoti-et-als-trap-counts)), so New York's and Wisconsin's studies agree on a generation near 1,100 to 1,300 DD40. A generation of about 1,250 DD40 would fit both; it's proposed to Ben, not made. Wisconsin trap counts (UW Vegetable Entomology, DATCP) would settle it; until then the model's summer flights may be early, and its page says so.
- **Three flights:** set by Wisconsin's study (the third small); New York has four (NEWA). In a long, warm season a fourth may start in southern Wisconsin that the model doesn't show.
- **Spring emergence's end:** the curve ends at 935 where Jyoti et al. found complete emergence near 1,098; a few late flies are left out.
- **The summer flights' weight (0.5)** is a judgment: the sources say the spring flight does most of the damage (NEWA; Eckenrode and Chapman's radish injury; A3422). The papers' figures give sizes that disagree with each other (New York's F1 flight as large as spring's, Wisconsin's summer radish damage a few to 24 % of spring's; Choices above), so neither fixes the weight.
- **The larval stage** comes from laboratory days at about 70 °F turned into degree days, not from field observations.
- **Jyoti et al.'s method** is the simple average above 4 °C from January 1 on the farm's NOAA station (p. 526), as NEWA computes, except that NEWA counts from 40 °F (39.2 °F in the paper), about a day and a half later by the spring peak.
- For NEWA (courtesy email): the 75 % point (547 against the paper's 536; 25 % and 95 % are 2 and 7 off too), "overwintering generation ends 809", which is the paper's span from first emergence, the later peaks built from the flights' lengths, which the paper's Fig. 3 puts 10 to 29 days early in its own years, and the base of 40 °F for the paper's 4 °C.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_maggots.py
uv run python scripts/fetch_newa.py                     # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_maggots.py                  # needs the archive in data/ and the station hours
uv run app/manage.py shell < scripts/maggot_normals.py  # the dates on the normals
uv run app/manage.py shell < scripts/generation_weights_normals.py  # what the generation weights change
```

The check against Jyoti et al.'s trap counts: Open-Meteo's archive (`archive-api.open-meteo.com/v1/archive?latitude=42.88&longitude=-77.03&start_date=1999-01-01&end_date=2000-12-31&daily=temperature_2m_max,temperature_2m_min&timezone=America/New_York`), each year's running total of max(0, (max + min)/2 − 4) from January 1, read on Fig. 3's peak dates.
