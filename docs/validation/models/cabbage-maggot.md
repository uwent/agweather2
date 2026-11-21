# Cabbage maggot (`cabbage-maggot`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H1). The model: `packages/agmodels/src/agmodels/insects/cabbage_maggot.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `cabbage_maggot.md` beside it. Version 0.1 was VDIFN's two windows (single sine 42.8/86 °F, (360, 600, 1521) and (1881, 2121, 3042)); this version replaces it with NEWA's model (D95).

**In short:** NEWA's cabbage maggot model as D36 curves: the simple average above 40 °F from January 1, the spring flight through NEWA's 25–95 % emergence (Jyoti, Shelton and Barnard 2003, upstate New York), larval feeding timed from it, and up to four flights 850 degree days apart. On the same weather at 34 Wisconsin NEWA stations it reproduces NEWA's events to a day or two. Wisconsin's own trap study (Eckenrode and Chapman 1972) agrees on the spring flight but found generations about about half again as long as NEWA's (about 1,300 DD40 against 850), which would put the first summer flight about two weeks later and later flights later still; the model follows NEWA, and no Wisconsin trap data are in hand to settle it.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA's cabbage maggot model (newa.cornell.edu, read 2026-11-21; `tmp/references/insects/notes/newa-insects.md`) | Simple average, base 40 °F, no upper, from January 1. Table 1 ("Model by J.L. Jyoti and A.M. Shelton"): spring emergence first 288 ± 15, 25 % 366, 50 % 452, 75 % 547, 95 % 697; overwintering generation ends 809; first, second and third generation 50 % at 1,261, 2,176 and 3,014. Four generations in New York; highest risk at peak emergence of the first two flights; protect seedlings, transplants and root crops around peak flights | The method, the spring curve, the generation time and the number of flights |
| Jyoti, Shelton and Barnard 2003 ([doi:10.18474/0749-8004-38.4.525](https://doi.org/10.18474/0749-8004-38.4.525); abstract read on Crossref) | Water-pan traps in upstate New York, 1999–2000: four generations; spring emergence first 160.7 ± 8.1, 10 % 176.6, 25 % 204.2, 50 % 251.3, 75 % 297.6, 95 % 390.9 °C·d above 4 °C; 449.2 from first emergence to complete spring emergence; later generations' emergence spans 508, 465 and 399 | NEWA's table is this paper's points × 1.8 (288, 318, 368, 452, 536, 704 °F·d), except 75 % (NEWA 547, the paper 536). The training area. Its calculation method isn't in the abstract |
| Eckenrode and Chapman 1971 ([doi:10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)) | Growth chambers: developmental zero 42 °F (overwintered pupae) and 44 °F (nondiapausing), 43 °F chosen; first fly emergence 243 DD43; egg hatch 82 DD above 44 °F; pre-oviposition 4 days at 70 °F; egg to first egg peak 1,112 DD43 (41.5 days at 69.8 °F); cites Harris and Svec 1966: at 66–72 °F, egg 2–4, larva 18–22, pupa 12–25 days, pre-oviposition 6 | The larval stage's lag and duration (below) |
| Eckenrode and Chapman 1972 ([doi:10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151)) | Cone traps at Kenosha (1965) and Arlington (1966, 1968, 1969), Wisconsin; max–min air thermal units above 43 °F with Arnold's 1960 correction: first spring emergence 290–365 over five years; a generation 1,176 (12 field life cycles; 1,058 Kenosha 1965, 1,261 Arlington 1966); three flights (spring, F1, F2), the F2 small; spring the most damaging (radish injury, 1968–69) | A check (below) |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's windows | Replaced |
| Enviroweather (MSU; `docs/enviroweather-models.md`) | Single sine 43 °F, no upper, from March 1: emergence 300–564, spring peak 565–716, summer peaks from 1,476 and 2,652 | Compared only |

## Choices and differences

- **Degree days:** simple average above 40 °F, no upper threshold, from January 1 (NEWA; the stored total `average_40`). Eckenrode and Chapman counted above 43 °F with Arnold's correction; on the Wisconsin stations' days their spring numbers fall on about the same days as NEWA's (below).
- **Spring flight:** PERT (230, 405, 935) DD40, fitted by least squares to NEWA's 25, 50, 75 and 95 % (residuals under a percentage point: 25.2, 50.6, 74.6, 95.4 %). Its 10, 25, 50, 75 and 95 % come at 308, 365, 450, 549 and 692 against Jyoti et al.'s 318, 368, 452, 536 and 704; NEWA's first emergence (288) falls at 5.9 % of the curve. The curve's own end (935) is earlier than the paper's complete spring emergence (160.7 + 449.2 °C·d, about 1,098 DD40), which the last few percent drawn out; NEWA's "overwintering generation ends 809 ± 3" is the paper's 449.2 ± 1.4 °C·d × 1.8, a span from first emergence read as a total from January 1.
- **Larval feeding** (a `DerivedStage`): from 245 DD40 after each fly emerges (pre-oviposition 4–6 days at about 70 °F, about 150 DD40; egg 82 DD44, about 95 DD40), for 580 DD40 (18–22 days at 66–72 °F). Laboratory days at about 70 °F turned into DD40 at 30 a day: approximate, and the lab's soil temperatures, not air.
- **Generations:** every 850 DD40 (the least-squares fit to NEWA's peaks, 809, 915 and 838 apart: 50 % at 1,304, 2,156 and 3,007 against 1,261, 2,176 and 3,014), SD 85 (10 %; Eckenrode and Chapman saw the spring pattern repeat in later flights, so they spread little). At most four flights: New York's four (NEWA, Jyoti et al.); at 850 a generation southern Wisconsin's normal season would otherwise start a fifth in late September (below), which no source reports.
- **Equal weights (D37):** flight and larval feeding weight 1 in every generation. NEWA and Eckenrode and Chapman both find the spring flight the most damaging; the page says so.
- **Action window:** "Protect seedlings and transplants during fly flight", from 5 % (NEWA's first emergence) to 95 % of each flight: 283–692 DD40 in spring.
- **Against Eckenrode and Chapman 1972 (a difference kept, D95):** their Wisconsin generation, 1,176 DD43, is about 1,300 DD40 in summer, half again NEWA's 850. Their laboratory life cycle (1,112 DD43, 41.5 days at 69.8 °F) supports the longer time; NEWA's numbers come from four flights caught in New York in two years. NEWA is the standard (D95) and Jyoti et al. are the newer source, but they don't show Eckenrode and Chapman wrong: the two disagree.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_maggots.py`, run in CI:

- The spring flight within a percentage point of NEWA's 25, 50, 75 and 95 % (366, 452, 547, 697), and within 15 degree days of Jyoti et al.'s 10–95 % × 1.8; NEWA's first emergence at 288 comes at 5.9 % of the flight (test: 5.9 ± 0.5 %). Against Jyoti et al.'s own points the curve's 10, 25, 50 % are within 10 degree days (308, 365, 450 against 318, 368, 452), and its 75 and 95 % within 13 (549 and 692 against 536 and 704), so the spring flight passes 10, 25, 50, 75 and 95 % emergence within 13 degree days of the paper's points.
- Later flights' 50 % at 1,304, 2,156 and 3,007, within 45 degree days of NEWA's 1,261, 2,176 and 3,014; four flights and no fifth.
- The protection window opens at 283 and closes at 692 in spring (NEWA's 288 and 697).
- Half the spring flight's larvae have begun feeding by about 700 DD40.

### Against Eckenrode and Chapman 1972

`scripts/check_maggots.py` (station days, the single sine above 43 °F without an upper standing in for Arnold's correction), 67 station-seasons:

- Spring: the station's DD43 reaches 290 a median 2 days after our first flies (5.9 %; 10th–90th percentile 0 to 5) and 365 a median 9 days after (6 to 13). So Wisconsin's spring flies first emerged at 290 to 365 degree days above 43 °F, about the same days as NEWA's 288 above 40 °F, or up to about 9 days later.
- Generations: between our spring and first summer peaks the stations accumulated a median 742 DD43 (728 to 760), against their 1,176. By their generation time the first summer peak would come a median 16 days later (13 to 18). Eckenrode and Chapman's generations took 1,176 degree days above 43 °F, about about half again as long as NEWA's 850 above 40 °F (about 1,300 at 40 °F); the model follows NEWA.
- Flights: they trapped three flights at Arlington (spring, F1 from early July, F2 from mid-August, small); the model has four in southern Wisconsin's normal season (below), the fourth in mid-August.

### Against NEWA on the same weather

`scripts/check_maggots.py`; full table in [cabbage-maggot/newa.md](cabbage-maggot/newa.md). NEWA's model is recomputed from its published rules (`scripts/newa_reference.py`: the simple average above 40 °F from January 1, the first day reaching each event) on the hours of 34 Wisconsin NEWA stations, 2024 and 2025 (67 station-seasons). Ours run on the same daily max and min, and on the archive at each station's cell.

<!-- prettier-ignore -->
| Ours − NEWA's, days | Station days: median (10th–90th percentile; range) | Archive: median (10th–90th percentile) |
| --- | --- | --- |
| First emergence (288; ours 5.9 %) | 0 (0 to 0; 0 to 0) | 0 (−3 to +2) |
| Spring 25, 50, 75, 95 % | 0 (within a day) | 0 (−3 to +2) |
| First generation peak (1,261) | +1 (+1 to +2; +1 to +3) | +1 (−1 to +4) |
| Second generation peak (2,176) | −1 (−1 to 0) | −1 (−4 to +2) |
| Third generation peak (3,014) | 0 (−1 to 0) | 0 (−4 to +2) |

The model reproduces NEWA's events: first emergence, the spring peak and each later peak fall within a day or two of NEWA's on the same weather (the first generation's 1 to 3 days late, from the 43-degree-day difference in its peak). On the archive the spread is the grid's weather against the station's, ±3 days for most.

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
| Fourth flight 50 % (3,007) | August 13 | August 20 | September 4 |
| Normal total on October 15 | 4,438 | 4,130 | 3,622 |

UW–Madison (topic page): first flies in mid-May while yellow rocket flowers, a second generation in late June, a third in a long, warm season; at 43 °F from thaw, 300, 1,476 and 2,652. The model's first flies come in early May in the south and mid-May in the north, its second flight in UW's late June, and its third and fourth flights where UW's description has a third.

## Limits and open questions

- **Generation time:** NEWA's 850 DD40 against Eckenrode and Chapman's 1,176 DD43 in Wisconsin (and the lab's 1,112), two weeks apart by the first summer flight. Wisconsin trap counts (UW Vegetable Entomology, DATCP) would decide; until then the model's summer flights may be early.
- **Four flights:** set by New York's count; Wisconsin's study saw three, the third small, and NEWA counts the generations from its four peaks without a fourth flight's own timing.
- **Spring emergence's end:** the curve ends at 935 where Jyoti et al. found complete emergence near 1,098; a few late flies are left out.
- **Equal generations (D37):** the spring flight does most of the damage (NEWA; Eckenrode and Chapman's radish injury; A3422), but every flight counts alike in the risk.
- **The larval stage** comes from laboratory days at about 70 °F turned into degree days, not from field observations.
- **Jyoti et al.'s method** (average or sine, which station) isn't in the abstract; NEWA computes its table's thresholds by the simple average.
- For NEWA (courtesy email): the 75 % point (547 against the paper's 536) and "overwintering generation ends 809", which is the paper's span from first emergence.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_maggots.py
uv run python scripts/fetch_newa.py                     # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_maggots.py                  # needs the archive in data/ and the station hours
uv run app/manage.py shell < scripts/maggot_normals.py  # the dates on the normals
```
