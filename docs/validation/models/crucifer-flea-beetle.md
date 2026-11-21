# Crucifer flea beetle (`crucifer-flea-beetle`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H3). The model: `packages/agmodels/src/agmodels/insects/crucifer_flea_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `crucifer_flea_beetle.md` beside it. Version 0.1 was VDIFN's two summer windows (single sine 50 °F, no upper, from January 1: (820, 965, 1155) and (1640, 1785, 1975)), which were Kinoshita et al. 1979's stage sums from egg laying (UC IPM's table) run from January 1; this version replaces them.

**In short:** the overwintered adults' spring feeding on seedlings, the damage, is now the first stage: UW–Madison's degree-day table (Delahaut's XHT1087: flea beetles at 150–200 DD50, modified average 50/86 °F from January 1) as the curve's 10 % and peak. Their egg laying follows, and the new summer adults come 1,350 degree days after the spring adults, from Kinoshita et al.'s 820.6 °F·d from egg to adult converted to the model's degree days. Both kinds of adults count alike in the risk. On the normals the spring adults peak in early to mid-May and the summer adults in late July to mid-August. No counts were compared.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, XHT1087, Degree Days for Common Fruit & Vegetable Insect Pests (UW–Madison Extension, rev. 2012; hort.extension.wisc.edu, read 2026-11-21) and XHT1086 (the method) | "Fleabeetle: 150-200 DD50" (base 50 °F); phenology: Norway maple late bloom, serviceberry blooming, redbud early bloom. Method: modified average, low raised to the base, high capped at 86 °F, from January 1 | The method and the spring adults (the curve's 10 % and peak). The table names no species and gives no years |
| Kinoshita, Svec, Harris and McEwen 1979 ([doi:10.4039/Ent1111395-12](https://doi.org/10.4039/Ent1111395-12); abstract as published; numbers as UC IPM's model database gives them) | Laboratory and field, southwestern Ontario (Guelph). Adults overwinter in leaf litter and the top layer of soil and emerge in early spring. Egg to adult above about 11 °C (51.8 °F): 455.9 °C·d (820.6 °F·d; eggs 146.2, larvae 378.0, prepupae 82.3, pupae 214.2 °F·d), single sine; the females can lay after about 61 °C·d above about 17 °C; new adults predicted within ±3.7 days from sums of soil temperatures. One generation in 1974, two in 1975 | The new adults' timing (converted, below) and the egg-laying delay (judged, below) |
| UMass Extension Vegetable Program, Flea Beetle Biology | Overwintered adults move into fields in early May; the new generation appears in late June and a second in late July in Massachusetts; beetles leave fields in mid-September | Compared |
| UW Vegetable Entomology's flea beetles page | Active in early spring once temperatures reach about 50 °F; eggs in the soil in May; larvae feed about a month; pupae 11–13 days; one to three generations depending on the species; scout new plantings every one to two days | The window, the calendar checks |
| Ulmer and Dosdall 2006 ([doi:10.1016/j.cropro.2005.03.003](https://doi.org/10.1016/j.cropro.2005.03.003)) | Emergence of overwintered and new-generation adults on the Canadian prairies | Not read (paywalled) |
| VDIFN (`../ag-vdifn/db/seeds.rb`) and UC IPM's crucifer flea beetle model | Version 0.1: Kinoshita's sums from egg laying (145 hatch, 335, 525, 605, 820 first adults) run from January 1, as if eggs were laid then | Replaced |

## Choices and differences

- **Degree days:** the modified average, 50/86 °F, from January 1 (XHT1086/XHT1087; the stored total `dd_modified_50_86`). Kinoshita et al.'s 51.8 °F (11.0 °C) single sine isn't stored, and it was counted on soil temperatures. Rather than add a stored total for one sum, their 820.6 is converted: on the archive's daily air temperatures from May 15 to August 15, 2016–2025, the model's degree days are 1.100 times theirs at Arlington (years 1.080–1.112), 1.111 at Hancock (1.084–1.129) and 1.144 at Rhinelander (1.106–1.167). At 1.11, 820.6 is 911 (903 to 939 by place). NEWA runs no flea beetle model.
- **Overwintered adults** (`LifeStage` "Adults feeding", weight 1): PERT (100, 200, 600). XHT1087's 150–200 are its 10 % (144) and peak (200), read as the span from the first tenth of the beetles becoming active to their peak; the end (600) is a judgment: the old beetles feed into June and die off as they finish laying. These beetles chewing seedlings and transplants are the damage (UW, UMN, UMass), and the page says so.
- **Egg laying** (a `DerivedStage`, weight 0): from 300 after each beetle becomes active, for 300 (a judgment). Kinoshita et al.'s threshold for egg laying, 61 °C·d (110 °F·d) above 17 °C (62.6 °F), takes a median 31 days and 361 model degree days from the spring peak at Arlington (276–454 over 2016–2025), 34 days and 372 at Hancock, 30 days and 371 at Rhinelander; UW and UMass describe eggs in May. 300 sits between the two. The larvae, on root hairs, rarely matter and aren't a stage.
- **New summer adults** (the adults' second generation): 1,350 after the spring adults, the middle of egg laying (300 + 150) plus 911 from egg to adult (1,361, rounded). They feed on leafy and late cole crops and then overwinter. `max_generations=2`: the overwintered and the summer adults. Kinoshita et al. found a second generation in 1975 but not 1974, and UMass one in late July in Massachusetts; a partial further generation isn't modeled.
- **Equal weights (D37):** both kinds of adults weight 1. UW Veg Ento and UMN call flea beetles an early-season pest; the spring adults do the damage to stands.
- **Action window:** "Scout new plantings every one to two days" (UW Veg Ento), from 5 to 95 % of each generation's adults active: 129–410 in spring, 1,409–1,811 in summer.

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

- **XHT1087's numbers have no stated source**, species or years, and the table doesn't say which shares of the beetles' activity 150 and 200 are.
- **The summer adults may be late.** Two judgments set their timing: when the overwintered beetles lay (300 after becoming active, between Kinoshita et al.'s threshold and UW's "May") and the conversion of a sum on soil temperatures to air (the conversion uses air for both). Earlier laying, as UW and UMass describe, would bring the summer adults forward by up to about two weeks, toward UMass's late June. Ulmer and Dosdall 2006 and Kinoshita et al.'s full text would settle both.
- **One or two generations:** Ontario saw one in 1974 and two in 1975; any eggs the summer adults lay aren't modeled.
- **No counts compared:** no Wisconsin trap or scouting records were found; iNaturalist holds no Wisconsin records of _P. cruciferae_ (`tmp/inat-check/report.md`).
- **Species:** the model is for the crucifer flea beetle; the striped flea beetle (_P. striolata_) on the same crops may differ.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_cole_crop_pests.py
uv run python scripts/check_crucifer_flea_beetle.py          # the conversions (needs the archive in data/)
uv run app/manage.py shell < scripts/cole_pest_normals.py   # the dates on the normals
```
