# Common asparagus beetle (`common-asparagus-beetle`): validation

Model version 0.2, written 2026-11-21 and revised 2026-11-23 for Taylor and Harcourt 1978 and the original XHT1087 handout, both read in full, with the generation's split taken from Taylor and Harcourt (the same 600; no change to the model's output) (D98; part H, batch H5). The model: `packages/agmodels/src/agmodels/insects/common_asparagus_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `common_asparagus_beetle.md` beside it. Version 0.1 was VDIFN's one larval window (105, 250, 405 degree days, single sine 50/86 °F from January 1), Taylor and Harcourt 1978's sums from egg laying though VDIFN didn't say so, checked only against VDIFN; this report replaces that one.

**In short:** the overwintered beetles feeding and laying eggs on spears, as a curve whose 10 and 50 % are UW–Madison's 150 and 240 degree days (modified average, 50/86 °F, from January 1), larvae timed from them, and up to three generations 600 degree days apart. The spring egg laying comes from UW–Madison's table; the egg, larvae and pupa from Taylor and Harcourt 1978's laboratory sums (104, 301 and 166 °F·d), and the rest of the generation (about 30) from their field peaks, which make the same 600. Adults and larvae both count in the risk. On the normals the beetles are out from late April in the south and early May in the north, as UW–Madison and A3422 describe. No Wisconsin counts are known to compare with.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, K. (2005), _Degree Days for Common Fruit and Vegetable Insect Pests_, University of Wisconsin Garden Facts XHT1087, revised April 20, 2005, University of Wisconsin–Extension, Cooperative Extension (`tmp/references/insects/UW Madison XHT1087 2005 - Degree days for fruit and vegetable pests.pdf`, read in full; no DOI; revised 2012 by UW–Madison Division of Extension, Wisconsin Horticulture, at hort.extension.wisc.edu with the same entry), with XHT1086's method | Two pages of degree-day events with indicator plants, without sources, years or observations. Common asparagus beetle: "Base temperature = 50°F", "Egg laying at 150 – 240 DD50" (Amelanchier full bloom, redbud early to full bloom, Black Hills spruce bud caps splitting), p. 1; the same numbers and plants as its imported cabbageworm butterflies. It gives only the base: the method (the modified average, low raised to 50 °F, high capped at 86 °F) and the start (January 1) are XHT1086's, UW–Madison Extension's degree-day method page | The spring curve's 10 and 50 %; the method from XHT1086 |
| Lowenstein, Groves and Liesch, *Asparagus Beetle* (XHT1137, rev. 2026); UW Vegetable Entomology | Adults overwinter in debris and old fern stems and become active as spears emerge; eggs hatch in about a week; larvae feed about two weeks, then pupate in the soil; new adults about a week later; two to three generations; thresholds for adults, eggs and larvae | A check of the egg's week at late May's rate (until 2026-11-23, version 0.2's split of the generation time, a pupa of 120 and 80 before laying, came from these days) |
| Commercial Vegetable Production in Wisconsin (A3422, 2026) | Common asparagus beetles active in April | The normal dates' comparison |
| Taylor 1979, PhD thesis, Carleton University ([doi:10.22215/etd/1979-00406](https://doi.org/10.22215/etd/1979-00406)), as the part H research notes summarize it (not read in full; not in `tmp/references/insects/`) | Adults overwinter; three generations in eastern Ontario; logistic development rates, eggs 8–34 °C, larvae and pupae 10–34 °C | The cap of three generations, which Taylor and Harcourt 1978 also report (trivoltine in eastern Ontario, p. 57; three generations in their 1976 field counts) |
| Taylor and Harcourt 1978 ([doi:10.4039/Ent11057-1](https://doi.org/10.4039/Ent11057-1); read in full) | Laboratory, Ottawa Research Station: eggs, larvae and pupae from a culture of beetles collected in 1975, reared at ten constant temperatures from 8 to 34 °C (Tables I–II); development fitted by logistic curves, not lines. Base 10 °C (p. 59: eggs hatch from 8 °C but those larvae don't develop). Each stage's degree days above 10 °C, averaged from the curves over 10–26 °C (p. 62): egg 58, instars I–IV 21, 26, 32 and 88 (the fourth includes the prepupa), pupa 92; egg to adult 317 °C·d. In °F above 50 °F: egg 104, larvae 301, pupa 166, egg to adult 571. Field check near Richmond, Ontario, 1976 (weather from Ottawa's Central Experimental Farm; Table III): three generations, eggs peaking June 2, July 4 and August 7 and adults July 2, August 6 and September 8; the degree days between stage peaks didn't differ from the expected (chi-square). Egg peak to adult peak observed 278.4, 313.4 and 270.4 °C·d (501, 564 and 487 °F·d) against the expected 317 (Table III, the sum of its rows: egg 48.2, 51.8, 44.9; fourth instar and pupa together 154.0, 169.8, 154.6 against 180); adult peak to the next generation's egg peak 2 days (July 2 to 4) and 1 day (August 6 to 7), its degree days not given. Trivoltine in eastern Ontario, egg laying peaking in early June, early July and early August; the overwintered adults on spears do most of the damage (p. 57) | The egg (100) and larvae (300), which round its 104 and 301; the pupa (166) and the days from adults to eggs (about 30) inside the generation time (below). VDIFN's window (105 to 405) and its new adults at about 570 are these sums from egg laying |
| VDIFN | 50/86 °F single sine from January 1; (105, 250, 405), first hatch to the last larvae; new adults about 570 (its description); Taylor and Harcourt 1978's sums, though VDIFN doesn't say so | Replaced |

## Choices and differences

- **Degree days:** UW–Madison's modified average, 50/86 °F, from January 1 (the stored `dd_modified_50_86`), XHT1086's method for the table the spring number comes from (XHT1087 itself states only the 50 °F base). VDIFN used the single sine at the same thresholds. NEWA runs no asparagus beetle model.
- **Overwintered beetles:** "Adults feeding and laying eggs", a PERT curve (100, 210, 550): 10 % at 149, 50 % at 239 and 90 % at 360. XHT1087's 150–240 is read as the 10 and 50 % of egg laying, as the same table's 150–240 for imported cabbageworm butterflies; the beetles are on the spears while they lay, so one curve stands for both. The end is a judgment (the old beetles die off in June).
- **Weights:** adults and larvae count alike (weight 1 each). The spring beetles do the harvest damage: their feeding browns and scars spears, and eggs on spears make them unmarketable; UW–Madison's thresholds count adults (5–10 % of plants) and eggs (2 % of spears) as well as larvae (50–75 % of plants). Later generations feed on the ferns, which weakens next year's crop; they count alike too (D37).
- **Larvae:** from 100 degree days after a beetle becomes active (Taylor and Harcourt's egg, 58 °C·d above 10 °C or 104 °F·d; also about a week at late May's normal 14 a day at Arlington, UW's week), for 300 (their four instars, 167 °C·d or 301 °F·d, the fourth including the prepupa in the soil; UW's two weeks at June's normal 16–17 a day would be 230–240). Their sums are on base 10 °C without an upper threshold; the model counts them on the modified average 50/86 °F, which differs little in May and June.
- **Generations:** every 600 degree days: the egg (100), the larvae (300) and the pupa (166, Taylor and Harcourt's 92 °C·d), 571 °F·d from egg to adult, and about 30 from the new adults to their first eggs: in Taylor and Harcourt's field counts each generation's adults peaked a day or two before the next generation's eggs (July 2 and 4, August 6 and 7, 1976), 20 to 40 degree days at July's normal 20 a day at Arlington. That makes 596, kept at 600. Until 2026-11-23 version 0.2 split the same 600 as a pupa of about a week (120 at June's rate) and about 80 of feeding before laying, from UW's days (Ben approved the change, 2026-11-23); since the engine runs a generation as one interval, the model's output doesn't change. The field's own egg-peak-to-adult-peak totals (487–564 °F·d, Table III) were shorter than the laboratory's 571, so the 600 may if anything be long; the third generation's adults peaked September 8, at the season's end. At most three (Taylor's three in eastern Ontario; UW two to three): without the cap, southern Wisconsin's normal season (2,495 degree days by September 15 at Arlington) would start a fourth in late August.
- **Window:** "Scout for beetles and eggs", from 10 to 90 % of each generation's beetles active (149–360 in spring). UW–Madison advises scouting spears from emergence and ferns all summer, whatever the model shows.
- **Against VDIFN:** VDIFN's one window covered only the first larvae (from April 27 to May 31 at Arlington on the normals) and left out the beetles on spears and the summer generations.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 103, the first adults feeding and laying eggs (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 10 at Madison, April 14 at Hancock, April 24 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) April 7. Where we don't have the normals it opens on March 15. It ends after October 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_beetles_and_plant_bug.py`, run in CI:

- The overwintered beetles' 10 % is at 149 degree days and 50 % at 239, against XHT1087's egg laying at 150 to 240.
- The larvae last 300 from 100 after a beetle becomes active: Taylor and Harcourt 1978's egg (104) and larvae (301), rounded.
- Generations come 600 apart, three at most: Taylor and Harcourt's egg (100), larvae (300) and pupa (166), egg to adult 571, plus about 30 for the day or two from adults to the next eggs in their field counts.
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

UW–Madison has the beetles active as the spears come up, in April or early May, with eggs hatching about a week later; A3422 has them out in April. The model's beetles become active in late April in southern Wisconsin and early May in the north, and half are out by May 10 at Arlington and May 20 at Rhinelander. The second generation's beetles peak in late June (early July at Rhinelander) and the third in late July (early August at Rhinelander), and the third generation's larvae feed on the ferns into August. Version 0.1's window ran from about April 27 to May 31 at Arlington and May 9 to June 11 at Rhinelander.

## Limits and open questions

- The spring egg laying comes from XHT1087, which gives no years or data behind its numbers. The egg, larvae and pupa come from Taylor and Harcourt 1978's laboratory sums (Ottawa, base 10 °C, without an upper threshold), and the 30 before laying from their field's one or two days between peaks; the generation, 596, is kept at 600. Their field totals from egg peak to adult peak (487–564 °F·d) were shorter than the laboratory's 571, so a generation of 550–600 would fit their one season as well.
- Their field check is one season (1976) near Ottawa, timed by peaks of counts; they compared degree days between peaks, not dates predicted from a start, and the spring start (the overwintered adults' egg laying) isn't in their model.
- Whether XHT1087's 150–240 means the start and the middle of egg laying (as read here) or its whole span isn't stated. The entry is word for word the table's imported cabbageworm entry (the same numbers and the same three indicator plants), so it may be a spring indicator-plant window shared by several pests rather than a measured event of this beetle.
- The spotted asparagus beetle, which appears later (often late May), isn't modeled.
- No Wisconsin counts of beetles, eggs or larvae are known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_beetles_and_plant_bug.py -k asparagus
uv run app/manage.py shell < scripts/beetle_bug_normals.py   # the normal dates
```
