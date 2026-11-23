# Common asparagus beetle (`common-asparagus-beetle`): validation

Model version 0.2, written 2026-11-21 and revised 2026-11-23 for Taylor and Harcourt 1978, read in full (D98; part H, batch H5). The model: `packages/agmodels/src/agmodels/insects/common_asparagus_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `common_asparagus_beetle.md` beside it. Version 0.1 was VDIFN's one larval window (105, 250, 405 degree days, single sine 50/86 °F from January 1), Taylor and Harcourt 1978's sums from egg laying though VDIFN didn't say so, checked only against VDIFN; this report replaces that one.

**In short:** the overwintered beetles feeding and laying eggs on spears, as a curve whose 10 and 50 % are UW–Madison's 150 and 240 degree days (modified average, 50/86 °F, from January 1), larvae timed from them, and up to three generations 600 degree days apart. The spring egg laying comes from UW–Madison's table; the egg and larvae from Taylor and Harcourt 1978's laboratory sums (read in full 2026-11-23), which also agree with the generation time. Adults and larvae both count in the risk. On the normals the beetles are out from late April in the south and early May in the north, as UW–Madison and A3422 describe. No Wisconsin counts are known to compare with.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, *Degree Days for Common Fruit & Vegetable Insect Pests* (XHT1087, UW–Madison, rev. 2012; now hort.extension.wisc.edu), with XHT1086's method | Asparagus beetle egg laying at 150–240 DD50; the modified average (low raised to 50 °F, high capped at 86 °F) from January 1 | The method; the spring curve's 10 and 50 % |
| Lowenstein, Groves and Liesch, *Asparagus Beetle* (XHT1137, rev. 2026); UW Vegetable Entomology | Adults overwinter in debris and old fern stems and become active as spears emerge; eggs hatch in about a week; larvae feed about two weeks, then pupate in the soil; new adults about a week later; two to three generations; thresholds for adults, eggs and larvae | A check of the egg's week at late May's rate; the split of the generation time between the pupa and the days before laying |
| Commercial Vegetable Production in Wisconsin (A3422, 2026) | Common asparagus beetles active in April | The normal dates' comparison |
| Taylor 1979, PhD thesis, Carleton University ([doi:10.22215/etd/1979-00406](https://doi.org/10.22215/etd/1979-00406)), as the part H research notes summarize it (not read in full; not in `tmp/references/insects/`) | Adults overwinter; three generations in eastern Ontario; logistic development rates, eggs 8–34 °C, larvae and pupae 10–34 °C | The cap of three generations |
| Taylor and Harcourt 1978 ([doi:10.4039/Ent11057-1](https://doi.org/10.4039/Ent11057-1); read in full) | Laboratory, Ottawa Research Station: eggs, larvae and pupae from a culture of beetles collected in 1975, reared at ten constant temperatures from 8 to 34 °C (Tables I–II); development fitted by logistic curves, not lines. Base 10 °C (p. 59: eggs hatch from 8 °C but those larvae don't develop). Each stage's degree days above 10 °C, averaged from the curves over 10–26 °C (p. 62): egg 58, instars I–IV 21, 26, 32 and 88 (the fourth includes the prepupa), pupa 92; egg to adult 317 °C·d. In °F above 50 °F: egg 104, larvae 301, pupa 166, egg to adult 571. Field check near Richmond, Ontario, 1976 (weather from Ottawa's Central Experimental Farm; Table III): three generations, eggs peaking June 2, July 4 and August 7 and adults July 2, August 6 and September 8; the degree days between stage peaks didn't differ from the expected (chi-square). Trivoltine in eastern Ontario, egg laying peaking in early June, early July and early August; the overwintered adults on spears do most of the damage (p. 57) | The egg (100) and larvae (300), which round its 104 and 301; a check of the generation time (below). VDIFN's window (105 to 405) and its new adults at about 570 are these sums from egg laying |
| VDIFN | 50/86 °F single sine from January 1; (105, 250, 405), first hatch to the last larvae; new adults about 570 (its description); Taylor and Harcourt 1978's sums, though VDIFN doesn't say so | Replaced |

## Choices and differences

- **Degree days:** UW–Madison's modified average, 50/86 °F, from January 1 (the stored `dd_modified_50_86`), the method of the table the spring number comes from. VDIFN used the single sine at the same thresholds. NEWA runs no asparagus beetle model.
- **Overwintered beetles:** "Adults feeding and laying eggs", a PERT curve (100, 210, 550): 10 % at 149, 50 % at 239 and 90 % at 360. XHT1087's 150–240 is read as the 10 and 50 % of egg laying, as the same table's 150–240 for imported cabbageworm butterflies; the beetles are on the spears while they lay, so one curve stands for both. The end is a judgment (the old beetles die off in June).
- **Weights:** adults and larvae count alike (weight 1 each). The spring beetles do the harvest damage: their feeding browns and scars spears, and eggs on spears make them unmarketable; UW–Madison's thresholds count adults (5–10 % of plants) and eggs (2 % of spears) as well as larvae (50–75 % of plants). Later generations feed on the ferns, which weakens next year's crop; they count alike too (D37).
- **Larvae:** from 100 degree days after a beetle becomes active (Taylor and Harcourt's egg, 58 °C·d above 10 °C or 104 °F·d; also about a week at late May's normal 14 a day at Arlington, UW's week), for 300 (their four instars, 167 °C·d or 301 °F·d, the fourth including the prepupa in the soil; UW's two weeks at June's normal 16–17 a day would be 230–240). Their sums are on base 10 °C without an upper threshold; the model counts them on the modified average 50/86 °F, which differs little in May and June.
- **Generations:** every 600 degree days: the egg (100), the larvae (300), the pupa (about a week, 120 at June's rate) and a few days of feeding before new beetles lay (about 80), a judgment from UW's days. Taylor and Harcourt 1978 give the same total another way: egg to adult 571 °F·d (with a pupa of 166, not 120), and in their field counts each generation's adults peaked only a day or two before the next generation's eggs (July 2 and 4, August 6 and 7, 1976), about 30 more. At most three (Taylor's three in eastern Ontario; UW two to three): without the cap, southern Wisconsin's normal season (2,495 degree days by September 15 at Arlington) would start a fourth in late August.
- **Window:** "Scout for beetles and eggs", from 10 to 90 % of each generation's beetles active (149–360 in spring). UW–Madison advises scouting spears from emergence and ferns all summer, whatever the model shows.
- **Against VDIFN:** VDIFN's one window covered only the first larvae (from April 27 to May 31 at Arlington on the normals) and left out the beetles on spears and the summer generations.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_beetles_and_plant_bug.py`, run in CI:

- The overwintered beetles' 10 % is at 149 degree days and 50 % at 239, against XHT1087's egg laying at 150 to 240.
- The larvae last 300 from 100 after a beetle becomes active: Taylor and Harcourt 1978's egg (104) and larvae (301), rounded.
- Generations come 600 apart, three at most: Taylor and Harcourt's egg to adult (571) and the day or two from adults to the next eggs in their field counts.
- The window opens at 149 and closes at 360 in spring, three times a season.

### On the normals

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, modified average 50/86 °F from January 1; `scripts/beetle_bug_normals.py`):

<!-- prettier-ignore -->
| Event (degree days from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Overwintered beetles, 10 % (149): window opens | April 28 | May 1 | May 8 |
| Overwintered beetles, 50 % (239) | May 10 | May 13 | May 20 |
| Overwintered beetles, 90 % (360): window closes | May 22 | May 25 | May 31 |
| First larvae peak (509) | June 3 | June 6 | June 12 |
| Second generation's beetles peak (829) | June 21 | June 25 | July 3 |
| Second generation's larvae peak (1,091) | July 4 | July 9 | July 18 |
| Third generation's beetles peak (1,433) | July 21 | July 26 | August 6 |
| Third generation's larvae peak (1,689) | August 2 | August 8 | August 22 |
| Normal total, September 15 | 2,495 | 2,313 | 2,006 |

UW–Madison has the beetles active as the spears come up, in April or early May, with eggs hatching about a week later; A3422 has them out in April. The model's beetles become active in late April in southern Wisconsin and early May in the north, and half are out by May 10 at Arlington and May 20 at Rhinelander. The second generation's beetles peak in mid to late June and the third in mid to late July, and the third generation's larvae feed on the ferns into August. Version 0.1's window ran from about April 27 to May 31 at Arlington and May 9 to June 11 at Rhinelander.

## Limits and open questions

- The spring egg laying comes from XHT1087, which gives no years or data behind its numbers. The egg and larvae come from Taylor and Harcourt 1978's laboratory sums (Ottawa, base 10 °C), and the generation time agrees with their egg-to-adult sum and field peaks; the split inside the generation is UW's days (the pupa 120 against their 166, and about 80 before laying against their field's day or two). A proposal for Ben, not adopted: the pupa 166 and about 30 before laying, the same 600 in all.
- Their field check is one season (1976) near Ottawa, timed by peaks of counts; they compared degree days between peaks, not dates predicted from a start, and the spring start (the overwintered adults' egg laying) isn't in their model.
- Whether XHT1087's 150–240 means the start and the middle of egg laying (as read here) or its whole span isn't stated.
- The spotted asparagus beetle, which appears later (often late May), isn't modeled.
- No Wisconsin counts of beetles, eggs or larvae are known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_beetles_and_plant_bug.py -k asparagus
uv run app/manage.py shell < scripts/beetle_bug_normals.py   # the normal dates
```
