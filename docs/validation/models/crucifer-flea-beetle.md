# Crucifer flea beetle (`crucifer-flea-beetle`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H3); XHT1087 read in full and its citation corrected 2026-11-23 (no output change). The model: `packages/agmodels/src/agmodels/insects/crucifer_flea_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `crucifer_flea_beetle.md` beside it. Version 0.1 was VDIFN's two summer windows (single sine 50 °F, no upper, from January 1: (820, 965, 1155) and (1640, 1785, 1975)), which were Kinoshita et al. 1979's stage sums from egg laying (UC IPM's table) run from January 1; this version replaces them.

**In short:** the overwintered adults' spring feeding on seedlings, the damage, is now the first stage: UW–Madison's degree-day table (Delahaut's XHT1087, 2005: "Fleabeetles … 150-200 DD50") on UW–Madison's modified average, 50/86 °F from January 1 (XHT1086), as the curve's 10 % and peak. Their egg laying follows, and the new summer adults come 1,350 degree days after the spring adults, from Kinoshita et al.'s 820.6 °F·d from egg to adult converted to the model's degree days. Both kinds of adults count alike in the risk. On the normals the spring adults peak in early to mid-May and the summer adults in late July to mid-August. No counts were compared.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, K. (2005). Degree Days for Common Fruit and Vegetable Insect Pests (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005). University of Wisconsin–Extension, Cooperative Extension; read in full (`tmp/references/insects/UW Madison XHT1087 2005 - Degree days for fruit and vegetable pests.pdf`, two pages, © 2002, by Karen Delahaut of UW–Madison's Fresh Market Vegetable Program). Its successor is online without an author or date (hort.extension.wisc.edu, read 2026-11-23, crediting Delahaut for earlier versions; revised 2012 by our earlier reading), listing "Fleabeetle" with the same numbers. XHT1086 (the method) | "Fleabeetles. Base temperature = 50oF. 150-200 DD50 (Norway maple late bloom, Amelanchier blooming, redbud early bloom)" (p. 1; confirmed; Amelanchier is serviceberry). It names no species, stage or event (not even "adults" or "activity"), and gives no method, upper threshold, start date, source, place or years: the modified average, 50/86 °F, from January 1 is XHT1086's | The spring adults (the curve's 10 % and peak), reading the entry as the overwintered adults' activity; the method from XHT1086 |
| Kinoshita, Svec, Harris and McEwen 1979 ([doi:10.4039/Ent1111395-12](https://doi.org/10.4039/Ent1111395-12); read in full) | Laboratory (culture at 24 °C; stages at 15–32 °C) and field at Agriculture Canada's field station in London, Ontario, 1974–1975 (a University of Guelph thesis). Adults overwinter in leaf litter and the top 2.5 cm of soil and appear in early spring (on cabbage seedlings by April 24, 1974). Egg to adult 456 (428–491) °C·d above 11 °C (p. 1402; 820.6 °F·d above 51.8 °F); by stage, each on its own threshold: eggs 80 (75–85) °C·d above 11.2 °C, larvae 197 (182–208) above 11.8, prepupae 44 (41–47) above 11.5, pupae 112 (107–119) above 11.8 (pp. 1400–1401). UC IPM's stage numbers (eggs 146.2, larvae 378.0, prepupae 82.3, pupae 214.2 °F·d) split the 456 total over the stages; they aren't in the paper. Before laying, females need 64 (52–73) °C·d above 16.7 °C (p. 1399), rounded to 61 (46–69) above 17 °C (p. 1402); preoviposition 22 days at 20 °C to 3.8 at 32 °C, none laid in 40 days at 15 °C. A generation, without preoviposition, 35 days at 24 °C. Field tests: emergence from eggs set out predicted from soil sums at 8 cm (single sine, Baskerville and Emin 1969) within 1 to 6 days, a mean of 3.7 (Table IV). Overwintered adults peaked on or before June 5, 1974 and on May 21, 1975; the new adults peaked toward the end of August in 1974 (one generation, no eggs found) and on July 2 and August 13 in 1975 (two); soil sums above 11 °C from May 30 to September 1, 938 °C·d in 1974 and 1,199 in 1975 | The new adults' timing (the 456 total, converted, below) and the egg-laying delay (judged, below) |
| UMass Extension Vegetable Program, Flea Beetle Biology | Overwintered adults move into fields in early May; the new generation appears in late June and a second in late July in Massachusetts; beetles leave fields in mid-September | Compared |
| UW Vegetable Entomology's flea beetles page | Active in early spring once temperatures reach about 50 °F; eggs in the soil in May; larvae feed about a month; pupae 11–13 days; one to three generations depending on the species; scout new plantings every one to two days | The window, the calendar checks |
| Ulmer and Dosdall 2006 ([doi:10.1016/j.cropro.2005.03.003](https://doi.org/10.1016/j.cropro.2005.03.003); read in full) | Field, emergence cages near Lethbridge, Alberta, 2003–2004. Overwintered adults began emerging April 23, 2003 and April 29, 2004, when soil at 5 cm reached 10–12 °C, and peaked when it reached 14–15 °C: the week before May 28 in 2003 (65.2 % of all), the week of June 4 in 2004 (47.4 %; 91.7 % from mid-May to June 4); emergence spread over 10–12 weeks, to late June or mid-July. New adults from canola seeded May 7 and 14, 2004 emerged from mid-August to late September, peaking August 20 and 27. No degree days: the authors found no threshold and call for one (p. 28) | Background, compared: the spring flight's single sharp peak and one summer generation on the prairies; no numbers taken |
| VDIFN (`../ag-vdifn/db/seeds.rb`) and UC IPM's crucifer flea beetle model | Version 0.1: Kinoshita's sums from egg laying (145 hatch, 335, 525, 605, 820 first adults) run from January 1, as if eggs were laid then | Replaced |

## Choices and differences

- **Degree days:** the modified average, 50/86 °F, from January 1 (XHT1086; XHT1087 gives only the base, 50 °F; the stored total `dd_modified_50_86`). Kinoshita et al.'s 51.8 °F (11.0 °C) single sine isn't stored, and it was counted on soil temperatures. Rather than add a stored total for one sum, their 820.6 is converted: on the archive's daily air temperatures from May 15 to August 15, 2016–2025, the model's degree days are 1.100 times theirs at Arlington (years 1.080–1.112), 1.111 at Hancock (1.084–1.129) and 1.144 at Rhinelander (1.106–1.167). At 1.11, 820.6 is 911 (903 to 939 by place). NEWA runs no flea beetle model.
- **Overwintered adults** (`LifeStage` "Adults feeding", weight 1): PERT (100, 200, 600). XHT1087's 150–200 are its 10 % (144) and peak (200), read as the span from the first tenth of the beetles becoming active to their peak; the end (600) is a judgment: the old beetles feed into June and die off as they finish laying. These beetles chewing seedlings and transplants are the damage (UW, UMN, UMass), and the page says so.
- **Egg laying** (a `DerivedStage`, weight 0): from 300 after each beetle becomes active, for 300 (a judgment). Kinoshita et al.'s threshold for egg laying, 61 °C·d (110 °F·d) above 17 °C (62.6 °F), takes a median 31 days and 361 model degree days from the spring peak at Arlington (276–454 over 2016–2025), 34 days and 372 at Hancock, 30 days and 371 at Rhinelander; UW and UMass describe eggs in May. 300 sits between the two. The larvae, on root hairs, rarely matter and aren't a stage.
- **New summer adults** (the adults' second generation): 1,350 after the spring adults, the middle of egg laying (300 + 150) plus 911 from egg to adult (1,361, rounded). They feed on leafy and late cole crops and then overwinter. `max_generations=2`: the overwintered and the summer adults. Kinoshita et al. found a second generation in 1975 but not 1974, and UMass one in late July in Massachusetts; a partial further generation isn't modeled.
- **Equal weights (D37):** both kinds of adults weight 1. UW Veg Ento and UMN call flea beetles an early-season pest; the spring adults do the damage to stands.
- **Action window:** "Scout new plantings every one to two days" (UW Veg Ento), from 5 to 95 % of each generation's adults active: 129–410 in spring, 1,409–1,811 in summer.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 101, the first adults feeding (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 10 at Madison, April 13 at Hancock, April 24 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) April 7. Where we don't have the normals it opens on March 15. It ends after September 30 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_cole_crop_pests.py`, run in CI:

- XHT1087's flea beetles at 150 to 200 degree days are the spring adults' 10 % at 144 and peak at 200 (test: the 10 % within 7 of 150, the peak at 200); at the peak the stage's activity is 1.
- The generation time is the middle of egg laying plus Kinoshita et al.'s 820.6 × 1.11 (911), within 15; the summer adults' middle comes within 10 of 1,350 after the spring adults'. Two generations of adults and no third.
- Risk is on the adults alone; the scouting window opens at 129 and closes at 410 in spring.

### On the normals

`scripts/cole_pest_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (modified average 50/86 °F from January 1). A typical-year calendar, not a forecast. The conversions above: `scripts/check_crucifer_flea_beetle.py`.

<!-- prettier-ignore -->
| Event (DD50, modified) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Spring adults 10 % (144) | April 27 | April 30 | May 7 |
| Spring adults' peak (200) | May 5 | May 8 | May 15 |
| Scouting window, spring (129–410) | April 24 to May 26 | April 27 to May 29 | May 5 to June 5 |
| Egg laying's peak (707) | June 15 | June 18 | June 25 |
| Summer adults 10 % (1,446) | July 21 | July 27 | August 7 |
| Summer adults' peak (1,579) | July 28 | August 2 | August 15 |
| Scouting window, summer (1,409–1,811) | July 20 to August 8 | July 25 to August 14 | August 5 to August 31 |

UW Veg Ento: beetles active in early spring once temperatures reach about 50 °F; eggs in May. UMass: beetles in fields from early May; new adults in late June and late July (Massachusetts). On the normals the new summer adults peak in late July in southern Wisconsin and early August in the north, after UMass's late June in Massachusetts. The spring adults are active from late April in the south and early May in the north, as both describe. Egg laying peaks in mid- to late June, later than UW's "May" (which covers flea beetles in general).

## Limits and open questions

- **XHT1087's numbers have no stated source**, species or years, and the entry doesn't name the event (just "150-200 DD50" under "Fleabeetles", with indicator plants): reading it as the overwintered adults becoming active, and 150 and 200 as their 10 % and peak, is ours.
- **The summer adults may be late.** Two judgments set their timing: when the overwintered beetles lay (300 after becoming active, between Kinoshita et al.'s threshold and UW's "May") and the conversion of a sum on soil temperatures to air (the conversion uses air for both). Earlier laying, as UW and UMass describe, would bring the summer adults forward by up to about two weeks, toward UMass's late June. Kinoshita et al.'s full text doesn't settle it: in London, Ontario the new adults peaked 42 days after the overwintered ones in 1975 (May 21 to July 2, two generations) but about 12 weeks after in 1974 (by June 5 to late August, one generation), when cool soil delayed egg laying to early to mid-June. The model's gap, 84 to 92 days from peak to peak on the normals, is like 1974's and twice 1975's: in a warm spring, the summer adults could come about six weeks earlier than the model has them. Ulmer and Dosdall 2006 give no degree days.
- **The spring peak in the field came later than the model's** in both papers: May 21, 1975 and by June 5, 1974 in London, Ontario (sweeps and sticky traps on crops), and the end of May or early June near Lethbridge, Alberta (emergence cages), against May 5 to 15 on Wisconsin's normals. Neither gives degree days, and both places' springs run later than southern Wisconsin's, so this isn't a test; the timing rests on XHT1087.
- **One or two generations:** Ontario saw one in 1974 and two in 1975; any eggs the summer adults lay aren't modeled.
- **No counts compared:** no Wisconsin trap or scouting records were found; iNaturalist holds no Wisconsin records of _P. cruciferae_ (`tmp/inat-check/report.md`).
- **Species:** the model is for the crucifer flea beetle; the striped flea beetle (_P. striolata_) on the same crops may differ.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_cole_crop_pests.py
uv run python scripts/check_crucifer_flea_beetle.py          # the conversions (needs the archive in data/)
uv run app/manage.py shell < scripts/cole_pest_normals.py   # the dates on the normals
```
