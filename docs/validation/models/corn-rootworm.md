# Corn rootworm (`corn-rootworm`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H4). The model: `packages/agmodels/src/agmodels/insects/corn_rootworm.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `corn_rootworm.md` beside it. Version 0.1 was VDIFN's window (329, 472, 636 degree days, single sine 52 °F from January 1), whose source, species and temperature basis aren't known (not UC IPM's page, now or in 2014), checked only against VDIFN; this report replaces that one.

**In short:** egg hatch of the northern corn rootworm as Apple, Walgenbach and Knee 1971 measured it in Wisconsin (base 52 °F; first hatch about 300, median 533 degree days in air), larvae feeding on roots for about 350 degree days after hatch (the risk), and beetles half out at about 1,075, from UW–Madison's 1,300 DD50. On the normals half the eggs hatch around June 14 at Arlington, a week after central Iowa's average peak, and the larvae peak in late June, a week or two before UW–Madison's early to mid-July. The air totals stand in for soil temperatures, which the eggs and larvae live in; no soil feature is built.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Apple, Walgenbach and Knee 1971 ([doi:10.1093/jee/64.4.853](https://doi.org/10.1093/jee/64.4.853)), abstract; Madison, Wisconsin | Northern corn rootworm eggs taken from soil and incubated at constant temperatures in early spring 1967–1969 (2,193 eggs): thresholds 10.66 °C (51.2 °F) for first hatch and 11.43 °C (52.6 °F) for median hatch; above 52 °F (11.1 °C), first hatch at 304.2 and median at 529.9 degree days. Eggs buried 2 inches deep in the field reached median hatch on June 13, 1970, when official air temperatures gave 533 degree days above 52 °F. The abstract gives no method or start date | The base; hatch's start (300) and median (533) |
| UC IPM, northern corn rootworm models | Apple et al. as Model 1 (method "not specified"; UC IPM recommends the single sine); Chiang and Sisson 1968 (St. Paul: first hatch 500 in air, 400 in soil, 52 °F); Dominique and Yule 1983 (Quebec: 49.5 °F from April 1, soil median 612) | The single sine |
| Delahaut, XHT1087 (UW–Madison, rev. 2012), with XHT1086's method | Corn rootworm adult beetles at 1,300 DD50 (modified average, 50/86 °F, from January 1) | Beetles half out at the normals' equivalent above 52 °F, 1,054–1,094 |
| UW Vegetable Entomology; A3646 (2025) | Eggs develop once soil reaches 50–52 °F; larvae feed by mid-June and peak in early to mid-July; each feeds about three weeks; beetles in July at Arlington; dig roots in July or August | The larvae's duration (a judgment); the window; comparison |
| Iowa State (Dean and Hodgson 2024; *Biology and Ecology of Corn Rootworm*) | Half the eggs hatched at 684–767 soil degree days above 52 °F from January 1 (no depth or citation); average peak hatch June 6 in central Iowa; hatch from mid-May to early June, lasting about a month; northern males begin emerging 5–7 days after western | Comparison only |
| University of Minnesota (Wang and Yang, June 5, 2026) | The same 684–767 soil degree days; southern Minnesota had reached it by June 3, 2026 | Comparison only |
| VDIFN | 52 °F, no upper, January 1; (329, 472, 636) as larval feeding, with first instars at 329 and adults at 681 in its sheet | Replaced |

## Choices and differences

- **Species:** the timing is the northern corn rootworm's (_Diabrotica barberi_), the species Apple et al. studied. No study in hand gives the western corn rootworm's (_D. virgifera virgifera_) hatch in degree days; Iowa State's and Minnesota's soil numbers are given for corn rootworms without naming one, and Iowa State notes northern males begin emerging 5–7 days after western ones. The larvae can't be told apart in the field, and one model serves both.
- **Degree days:** single sine above 52 °F from January 1 with no upper threshold (stored). Apple et al.'s abstract doesn't say how their air totals were computed or from when; the single sine is UC IPM's recommendation, and little accumulates above 52 °F before April, so the start matters little. Their 1970 total of 533 was probably a daily average from the official station (not checked); the sine gives more on cool spring days, which may put hatch a little early.
- **Air, not soil:** the eggs and larvae live in the soil. Apple et al.'s 304 and 530 were measured at constant temperatures, so they are the eggs' own degree days; their 533 in air is one field season's match to buried eggs. Iowa State's 684–767 soil degree days for half hatched can't be set against air totals: the two differ with depth, soil and cover. On the calendar the model's median hatch comes about a week after central Iowa's average peak at Arlington (below). A soil feature from the hourly soil temperatures wasn't built (Ben's question 6 in the part H plan).
- **Egg hatch:** a PERT curve (300, 495, 1000), weight 0: 10 % at 388, 50 % at 534 and 90 % at 723. The start is Apple's first hatch; the median their 533; the end (1,000) is a judgment, spreading hatch over about four weeks (Iowa State: about a month).
- **Larvae feeding on roots:** from hatch for 350 degree days, the risk (weight 1). UW Vegetable Entomology and A3646 give about three weeks; at the normal rate from mid-June to mid-July (15 to 19 a day at Arlington, 12 to 16 at Rhinelander) that's about 350. A judgment.
- **Beetles:** from 542 after hatch, for 700 (weight 0: silk clipping and egg laying are scouted, not modeled as risk). XHT1087's 1,300 DD50 is reached on the normals on the days the total above 52 °F reaches 1,094 (Arlington, July 15), 1,073 (Hancock, July 19) and 1,054 (Rhinelander, July 29); read as half the beetles out, at about 1,075, 542 after the median hatch. What's left after the larvae, 192 (about 11 days in July), is the pupa. The beetles' 700 (about six weeks) is a judgment.
- **One generation:** the eggs laid in August hatch the next spring. Extended diapause and the soybean-laying variant don't change the timing.
- **Window:** "Dig and rate roots for larval injury", from half the larvae done feeding to 95 % (885–1,123): UW Vegetable Entomology and A3646 advise digging in July or August, before root decay hides the injury.
- **Against VDIFN:** VDIFN's window (329 to 636) put the end of larval feeding in late June; its source isn't known.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_beetles_and_plant_bug.py`, run in CI:

- Hatch begins at 300, against Apple et al.'s first hatch at 304 in the laboratory, and half the eggs have hatched at 533 degree days above 52 °F (534 on the grid), the air total on June 13, 1970, when buried eggs reached median hatch.
- Half the beetles are out at 1,075 (533 + 542), within 1,054 to 1,094, the normals' totals above 52 °F on the days they reach XHT1087's 1,300 DD50.
- The larvae feed for 350 after hatch (UW's three weeks); the pupa takes the remaining 192.
- One generation; the window runs from 885 to 1,123.

### On the normals

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 52 °F with no upper threshold, from January 1; `scripts/beetle_bug_normals.py`):

<!-- prettier-ignore -->
| Event (degree days from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| 10 % hatched (388) | June 4 | June 8 | June 15 |
| Half hatched (534) | June 14 | June 18 | June 26 |
| 90 % hatched (723) | June 25 | June 29 | July 8 |
| Larvae peak (703) | June 24 | June 28 | July 7 |
| Window opens: half the larvae done feeding (885) | July 4 | July 9 | July 19 |
| Half the beetles out (1,076) | July 15 | July 20 | July 31 |
| Window closes (1,123) | July 17 | July 22 | August 3 |
| Beetles peak (1,541) | August 7 | August 15 | September 3 |

Half the eggs hatch around June 14 at Arlington and June 26 at Rhinelander, one to three weeks after central Iowa's average peak hatch (June 6, Iowa State), which is farther south. Larvae peak in late June in the south and early July in the north, a week or two before UW–Madison's early to mid-July peak of larvae, and half the beetles are out around mid-July at Arlington, where A3646 has beetles appearing in July. Version 0.1's window ran from about May 31 to June 21 at Arlington and June 10 to July 3 at Rhinelander.

## Limits and open questions

- **First beetles at Arlington:** an old three-year study at Arlington (UW Vegetable Entomology) found the first beetles July 16–24, after the model has half of them out (about July 15 on the normals); A3646's early July matches the model's first beetles. The page and topic page say the model may run early (Ben, 2026-11-23; no shift).
- Apple et al. 1971 isn't in hand; its numbers come from its abstract and UC IPM. Its method and start date aren't known.
- **Air temperatures stand in for the soil** (Ben, 2026-11-23: air degree days stay for now; the page says the model may run early). A later step: a daily soil degree-day feature (from the archive's 4 and 10 cm soil temperatures) would let the model use Iowa State's soil numbers or Apple's laboratory ones directly; it needs a check of how ERA5-Land's lag and the forecast's soil temperatures would affect it, and of whether soil totals move the larvae and beetles toward UW–Madison's dates and Arlington's first beetles.
- The western corn rootworm's hatch isn't separately timed. Jackson and Elliott 1988 ([doi:10.1093/ee/17.2.166](https://doi.org/10.1093/ee/17.2.166)) and Davis, Brenes and Allee 1996 ([doi:10.1093/ee/25.4.767](https://doi.org/10.1093/ee/25.4.767); soil base 11 °C) aren't in hand; they would give its development and a check on the larvae's 350 and the pupa.
- The larvae run a week or two ahead of UW–Madison's description of their peak; a shorter larval period or a later hatch would widen the gap or close it, and we have no Wisconsin counts to choose between them.
- No Wisconsin observations of hatch or larvae are known to us.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_beetles_and_plant_bug.py -k corn_rootworm
uv run app/manage.py shell < scripts/beetle_bug_normals.py   # the normal dates and the 1,300 DD50 conversion
```
