# Tarnished plant bug (`tarnished-plant-bug`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H5). The model: `packages/agmodels/src/agmodels/insects/tarnished_plant_bug.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `tarnished_plant_bug.md` beside it. Version 0.1 was VDIFN's one window (275, 1,000, 2,000 degree days, single sine 52 °F from January 1), checked only against VDIFN; this report replaces that one.

**In short:** the generations of _Lygus lineolaris_ from Ugine 2012's development times at constant temperatures (nymphs 393 degree days above 52 °F, adults 540, a generation 640), with the spring hatch placed so that young nymphs peak at 275, the number UW–Madison's vegetable newsletter uses. That 275 comes from Simko's model of a western lygus bug in Oregon and Idaho: **no source gives a spring degree-day timing for this species**, so the first generation's timing is unsupported, and everything after it inherits that. On the normals the first nymphs appear in mid-May at Arlington, as UW–Madison's fruit program reports in strawberries. We recommend retiring the model unless a spring timing for _L. lineolaris_ turns up.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Ugine 2012 ([doi:10.1603/EN10210](https://doi.org/10.1603/EN10210); open access), Tables 1, 2, 4 and 5 | _L. lineolaris_ from the USDA-ARS colony at Stoneville, Mississippi, reared on green beans at 17–32 °C. Thresholds and thermal constants by linear regression: egg 5.9 °C, 149.3 °C·d; first instar 8.2, 62.5; second 7.9, 50.0; third 7.7, 51.0; fourth 8.4, 54.3; fifth 7.5, 87.0; all nymphs 9.8, 250.0; egg to adult 7.9 °C, 416.7 ± 31.3 °C·d. Generation time 49.2, 36.2, 28.5, 25.7 and 21.0 days at 18, 21, 25, 27 and 30 °C (61.5 at 17, 21.3 at 32). Female longevity 24.5–34.7 days at 18–27 °C, 17.6 at 30. Preoviposition 13.2 days at 18 °C to 4.9 at 30 | The nymphs, the adults and the generation time, converted |
| Groves, vegetable insect update, UW–Madison Vegetable Pathology, June 5, 2021 | "Lygus bugs are active most of the summer after early-season nymph development (starting at an accumulated 275 DD52)"; sweep threshold for potatoes and snap beans | The spring anchor: young nymphs peak at 275 |
| Simko 2000, USPest.org `lyg` ("Lygus bug [alfalfa seed]") | Single sine 52 °F from January 1; 275, the peak of first- and second-stage nymphs; for seed alfalfa in eastern Oregon and southwestern Idaho; no species named (likely _L. hesperus_ there) | The setting and the 275, by way of UW's newsletter |
| van Zoeren and Guédot 2018, UW–Madison Fruit Program | Adults overwinter and are active early in spring; nymphs in strawberries around mid-May, once temperatures reach about 68 °F; four to five generations a year in the Midwest | Comparison |
| NC State (Lopez, *Tarnished Plant Bug in Strawberries*, 2014, revised April 17, 2026) | Overwintered adults become active in early to mid spring once temperatures consistently exceed 46 °F; egg laying once days average 60–68 °F; two to three generations in the mid-Atlantic and Southeast; no degree days | Nothing usable as a degree-day start |
| Rougoor (University of Guelph), *Tarnished Plant Bug: Up Close and Personal*, on Cornell Cooperative Extension's site | Adults emerge when temperatures reach 8 °C and lay eggs at 20 °C or higher; three to five generations; nymphs in strawberries in mid-May | Nothing usable as a degree-day start |
| Fleischer and Gaylor 1988 ([doi:10.1093/ee/17.2.246](https://doi.org/10.1093/ee/17.2.246)) | Nymphal thresholds near 10 °C on weeds and cotton (from the part H research notes; no totals in its abstract) | Not used; agrees with Ugine's 9.8 °C for nymphs |
| VDIFN | 52 °F, January 1, (275, 1,000, 2,000) | 275 kept as the spring anchor; 1,000 and 2,000 have no source and are dropped |

We searched for a spring degree-day timing for _L. lineolaris_ (UW–Madison, Michigan State, Cornell, NC State, Penn State, UMass, Guelph) and found none: the extension pages give calendar months or temperature cues. UC IPM's lygus model (54 °F, from first adults in strawberries, 252 to first nymphs) is for the western species in California.

## Choices and differences

- **Degree days:** single sine above 52 °F from January 1 with no upper threshold, as version 0.1 and UW's newsletter (stored). Ugine's threshold for development from egg to adult is 7.9 °C (46.2 °F), 9.8 °C (49.6 °F) for the nymphs; Penn State and Fleischer and Gaylor put it near 50 °F. Rather than add a running total at 46.2 °F for a model without a supported spring timing, Ugine's sums are converted to degree days above 52 °F by the ratio of June–August totals on the normals: 0.737 for those above 46.2 °F (Arlington 0.754, Hancock 0.741, Rhinelander 0.716) and 0.873 for those above 49.6 °F (0.882, 0.875, 0.862). A model kept for the long term should count above 46 °F itself.
- **Egg hatch:** a PERT curve (50, 193, 500), weight 0: 10 % at 115, 50 % at 213, 90 % at 335. Placed so that first- and second-stage nymphs (62.5 + 50.0 °C·d, 202.5 °F·d, × 0.737 = 150 after hatch) peak at 275 (the curve gives 275). The start and end, which spread hatch over the overwintered adults' weeks of egg laying, are judgments.
- **Nymphs:** from hatch for 393 (Ugine's 250.0 °C·d above 9.8 °C, 450 °F·d, × 0.873), weight 1. They do more damage than adults in strawberries (UW–Madison), and insecticides work better on them.
- **Adults:** from 393 after hatch for 540 (females' longevity, a mean of 408 °C·d above 7.9 °C over 17.6–34.7 days at 18–30 °C, 735 °F·d, × 0.737), weight 1: they feed on the same buds, flowers and fruit, and sweep thresholds in beans and potatoes count both.
- **Generations:** every 640 degree days: Ugine's generation times at 18–30 °C are 497, 474, 487, 491 and 464 °C·d above 7.9 °C, a mean of 483 (869 °F·d), × 0.737. Egg to adult converts to 553 (416.7 °C·d, 750 °F·d). No cap: on the normals about four hatches begin at Arlington by mid-September and three at Rhinelander, against UW–Madison's four to five in the Midwest.
- **Not modeled:** the overwintered adults themselves (active from early spring, before the model's first nymphs), and the influx when alfalfa is cut or weedy borders are mowed.
- **No window:** scouting runs all season (strawberries before the first flowers to harvest; sweeps in beans and potatoes), so a window would add nothing.
- **Against VDIFN:** the 275 stays, now as the young nymphs' peak; VDIFN's peak at 1,000 and end at 2,000, which have no known source, give way to repeating generations.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_beetles_and_plant_bug.py`, run in CI:

- Nymphs last 393 degree days above 52 °F and a generation 640, from Ugine's 250.0 degree-days Celsius above 9.8 °C for the nymphs and a mean generation time of 483 above 7.9 °C, converted by the ratios above.
- Young nymphs peak at 275 degree days, the number UW–Madison's newsletter uses. That number comes from a model of the western lygus bug in Oregon and Idaho, so the spring timing is unsupported for this species.
- Hatches repeat every 640, without a cap.

### On the normals

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 52 °F, no upper threshold, from January 1; `scripts/beetle_bug_normals.py`):

<!-- prettier-ignore -->
| Event (degree days from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Spring hatch, 10 %: first nymphs (115) | May 5 | May 8 | May 16 |
| Spring hatch, 50 % (213) | May 19 | May 23 | May 29 |
| Young nymphs peak (275) | May 26 | May 29 | June 5 |
| Nymphs peak (447) | June 9 | June 12 | June 20 |
| First summer adults, 50 % (606) | June 19 | June 23 | July 1 |
| Second hatch, 50 % (855) | July 3 | July 7 | July 17 |
| Third hatch, 50 % (1,496) | August 5 | August 12 | August 30 |
| Fourth hatch, 50 % (2,136) | September 13 | October 6 | not reached |
| Normal total, October 15 | 2,390 | 2,173 | 1,816 |

The first nymphs appear in mid-May at Arlington, as UW–Madison's fruit program reports in strawberries, but young nymphs peak only in late May in the south and early June in the north. The model has about four generations at Arlington and three at Rhinelander, against the four to five UW–Madison counts in the Midwest. Version 0.1's window opened about May 26 at Arlington and June 5 at Rhinelander and peaked about July 10 at Arlington.

## Limits and open questions

- **The spring timing is unsupported for this species.** The 275 is Simko's peak of young nymphs for a western lygus bug on seed alfalfa, repeated in UW's newsletter; no study or extension source gives a degree-day timing for _L. lineolaris_'s overwintered adults or first nymphs. Everything after the first generation inherits that start. **Recommendation: retire the model** (Ben's call; part H question 1) unless Ben or the UW labs have Wisconsin counts to time the spring generation.
- Ugine's insects were a long-reared laboratory colony from Mississippi, fed on green beans at constant temperatures; field development on Wisconsin's hosts and fluctuating temperatures may differ (Ugine notes his preoviposition periods were shorter than others report).
- Sums converted to 52 °F by summer ratios on the normals, not counted at Ugine's threshold.
- The overwintered adults and the influx from cut alfalfa aren't modeled.
- No Wisconsin field counts are known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_beetles_and_plant_bug.py -k tarnished
uv run app/manage.py shell < scripts/beetle_bug_normals.py   # the normal dates and the conversion ratios
```
