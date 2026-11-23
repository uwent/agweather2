# European corn borer (`european-corn-borer`): validation

Model version 0.3, written 2026-11-21 and revised 2026-11-23 for the one-flight form (D98; part H, round 2); UW–Madison's degree-day table (XHT1087) read in full in its 2005 printing 2026-11-23, every number confirmed, with no change to the model. The model: `packages/agmodels/src/agmodels/insects/european_corn_borer.py`, run by the insect engine (`agmodels.phenology`, D36, D37); its page: `european_corn_borer.md` beside it. Rebuilt in part H, batch H2 (`docs/plans/models.md`); the research notes this condenses are in the project's working notes (part H sources, "European corn borer").

**In short:** rebuilt on Wisconsin's own degree-day lineage (UW–Madison's table, in the line of Apple's borer degree days at Madison, though not his numbers, which run later): the modified average, 50/86 °F, from January 1; a spring flight from 374 degree days (peak 631) and a summer flight 1,100 later (peak near 1,733), with egg masses and young larvae timed from them and a window to treat larvae before they bore in. On DATCP's black light traps, 2020–2026, the flights' midpoints fall within a day of the observed weeks in southern and central Wisconsin, where VDIFN's ran 4 and 14 days late. In the north (Wausau, Marshfield, Antigo) the traps show one flight in mid-July to mid-August, which two flights don't fit; since version 0.3 the model runs one flight where the 30-year normal total by August 1 is below 1,500 (Ben, 2026-11-23), whose midpoint falls a median 0 days from Wausau's observed weeks.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Delahaut, K. *Degree Days for Common Fruit and Vegetable Insect Pests* (University of Wisconsin Garden Facts XHT1087, revised April 20, 2005; University of Wisconsin–Extension, Cooperative Extension; UW–Madison Fresh Market Vegetable Program), read in full 2026-11-23 (`tmp/references/insects/`); its current web version (UW–Madison Extension, Wisconsin Horticulture, rev. 2012, hort.extension.wisc.edu) gives the same numbers | "Base temperature = 50°F" and nothing more on the method: no upper threshold, way of averaging or start date, and no sources or years. First spring moths 375 (*Spiraea × vanhouttei* in full bloom), first eggs 450 (pagoda dogwood late bloom), peak spring moths 631 (black locust full bloom), first summer moths 1,400 (mountain-ash fruit golden yellow, most Canada thistle seed ripe), first eggs 1,450, first egg hatch 1,550, peak summer moths 1,733, summer treatment period 1,550–2,100 (Queen Anne's lace full bloom, 1,500, to goldenrod early bloom, 2,100) | The flights' starts and peaks, egg laying 76 after the first moths, hatch ~100 after laying (the summer eggs and hatch: 1,450 and 1,550) |
| Delahaut, *Calculating Degree Days* (XHT1086, UW–Madison Extension, Wisconsin Horticulture; hort.extension.wisc.edu, read 2026-11-21) | Two methods, from January 1 ("from the first of the year"): the simple average, and the modified average (the low raised to the base, the high capped at 86 °F). It doesn't say which the tables use or recommend one (reread 2026-11-23). Flandermeyer and Bick time corn borer sprays in "modified base 50°F" degree days | The method, on which XHT1087's numbers are read |
| Apple 1952 ([doi:10.1093/jee/45.5.877](https://doi.org/10.1093/jee/45.5.877)), read 2026-11-23 | "Borer degree-days": the simple average above 50 °F, no upper, from the first day whose mean is above 50 (p. 878). Field examinations of canning corn in north-central Illinois (Sycamore, 1946–1948) and south-central Wisconsin (Madison, 1949–1951); Table 1, first of each stage, six-year mean ± SD: pupa 246 ± 11, moth 423 ± 26, eggs 603 ± 67, hatch 699 ± 70; first-generation pupa 1,446 ± 45, moth 1,716 ± 79; second-generation eggs 1,787 ± 57, hatch 1,901 ± 49. Table 2: in central Iowa, 1949–1951, 17 of 23 stages within 3 days of the predicted date. P. 879: 1,000 = 50 % hatch (assess egg masses), treat at 1,100 (75 % hatch) and again at 1,200 | Base 50 °F, the lineage UMN's VegEdge names ("similar to the original model from Dr. J. W. Apple"). Not his numbers: they run later than UW's table (below, "Against Apple 1952") |
| Matteson and Decker 1965 ([doi:10.1093/jee/58.2.344](https://doi.org/10.1093/jee/58.2.344)) | Laboratory rearing at constant 55–95 °F, an Illinois multivoltine colony (Champaign County). Thresholds: eggs 57.3, larvae 52, pupae 54.5 °F; development linear over 65–80 °F (eggs), 60–90 (larvae), 60–85 (pupae), all immature stages to about 90 °F. Table 1: eggs 6.08, 4.33 and 3.33 days at 70, 75 and 80 °F (122, 108 and 100 DD50), slower again above 80. Table 2: larval stage 26.1, 21.9 and 16.1 days (523, 547 and 484 DD50), the first four stadia 57–63 % of it | A check: hatch ~100 after laying, young larvae ~300 from hatch to the fifth instar (286–329 DD50 at 70–80 °F), and an upper cutoff near 86 °F |
| Hazzard 2017 (UMass) | 374, eggs 450, peak 631, hatch ~100 after laying, second flight 1,400, eggs 1,450, hatch 1,550 | A check that UW's table is the shared Upper Midwest–Northeast lineage |
| Potter 2020, UMN (field corn, Table 3) | Base 50 from March; multivoltine first moths 374, scout 800–1,000; second generation first moths 1,400, scout 1,550–2,100; univoltine first moths < 911, scout 1,100–1,300; "a first moth capture biofix will be more accurate" | The univoltine timing, compared with Wausau's traps (below) |
| Flandermeyer and Bick (UW–Madison, 2025); A3646 | Sprays for first-generation larvae at 800–1,000 DD50, second at 1,500–2,100, before larvae bore in | The window's purpose; its edges compared |
| Showers et al. 1989, NCR 327 (Iowa State), Table 2 | Simple average above 50 from the first significant spring capture: peak hatch 100, 1st–2nd instars 200+, 3rd 350+, 4th 400+, 5th 550+ (boring), pupation 900+; second generation peak hatch 1,260, boring 1,650; says January 1 starts "have not been accurate" | Young larvae last ~300 from hatch (to the 4th instar); NCR 327's first-capture biofix is the alternative (Limits) |
| Bessin, EF-106 (Kentucky) | Simple average above 50 from January 1, no upper; Grayson Brown's unpublished model: flights 550/690/740/790/900 and 1,660/1,880/1,950/2,030/2,190 | Nothing: these are VDIFN's numbers exactly, a Kentucky model that VDIFN ran on single sine 50/86 |
| Enviroweather (MSU) | Baskerville-Emin sine 50, no upper, from March 1; flights 450–950, 1,450–1,950, 2,450–2,950 ("rough numbers") | Compared only |
| Hoard and Weiss 1995 ([doi:10.1093/ee/24.3.564](https://doi.org/10.1093/ee/24.3.564)), read 2026-11-23 | North Dakota, 1990–1993: larvae collected statewide each September and a field study at Carrington; post-diapause development to pupation (°C·d above 10 °C, simple average, in a 30 °C chamber) shortest in the southeast (Hankinson, 50 % at 272 and 180 °C·d in 1990 and 1991) and longer to the north and west (Bowbells 506 in 1990; Driscoll 428 and 462 in 1991 and 1992), and shorter for the bivoltine than the univoltine component (50 % at 218 against 298 °C·d, Fig. 2). Larvae pupating by 220 °C·d have progeny that reach the third instar before the critical photoperiod (15.5 h, July 15 in North Dakota) and can make a second generation; from pupation to the next generation's fifth instar takes 425 °C·d. At Carrington a second generation flew in 1991 (statewide, a season 142 °C·d above the 30-year average) and not in the cool 1992 (161 below) or 1993; the share pupating by 220 °C·d fell from about 30 % to 9 % and 3 %. Conclusion: the current season's length is the major factor, and univoltine populations keep a bivoltine remnant | The north's one generation as a property of the place's population and season (the one-flight form); a limit (partial second flights in warm years). No degree-day bound by date |
| Showers et al. 1975 ([doi:10.1093/ee/4.5.753](https://doi.org/10.1093/ee/4.5.753)), read 2026-11-23 | Ten populations infested at seven test sites from Tifton, Georgia, to Morris, Minnesota, 1967–1972 (Wooster, Ohio, in the 1970–1972 study): three ecotypes by diapause, northern (Minnesota's Ottertail County, Quebec; diapause genetically fixed, one generation), central (Iowa, Nebraska, Ohio; two) and southern (three or four). Central-ecotype borers diapaused less at the northern sites (longer days) and the most at Wooster, Ohio (cool) | Background for the one-flight form: in the north, a univoltine ecotype; no degree days |
| Ikten et al. 2011 ([doi:10.1603/AN09149](https://doi.org/10.1603/AN09149)); A1220 | Critical photoperiods 14.80 h (bivoltine Nebraska) and 15.33 h (univoltine northwest Minnesota); most borers in northern Wisconsin diapause after one generation | The north's one generation |
| Anderson, Kennedy and Stinner 1982 ([doi:10.1093/ee/11.6.1307](https://doi.org/10.1093/ee/11.6.1307)), read 2026-11-23 | North Carolina: a nonlinear rate model of post-diapause development from laboratory rearing at 13.7–35 °C (Table 1), started on January 1 (chosen by comparing start dates), checked on black light traps in four coastal counties, 1977–1978: 10 % and 50 % spring emergence within 5 days, 90 % up to 18 days early | Background: a January 1 start for the spring flight, against NCR 327's caution |
| DATCP black light traps, 2020–2026 (`docs/validation/data/datcp-blacklight-traps/`) | Weekly corn borer moths at 6–13 sites a year, 59–293 moths a year | The check below |

NEWA runs no European corn borer model, so D95 doesn't apply.

## Choices and differences

- **Degree days:** the modified average, 50/86 °F, from January 1 (the modified of XHT1086's two methods, the one Flandermeyer and Bick use for corn borer; the table, XHT1087, gives only the base, 50 °F; stored on the grid as `dd_modified_50_86`). VDIFN ran EF-106's numbers on single sine 50/86, a method neither EF-106 nor UW uses.
- **Adult flight:** PERT (374, 631, 1,000), weight 0 (moths don't feed). Its 1, 50 and 99 % are 420, 645 and 911. The end, ~1,000, is the research's estimate: UW and UMN give no last moths, but scout first-generation larvae to 1,000 and have summer moths from 1,400.
- **Egg masses:** from 76 after each moth's emergence (UW: first moths 375, first eggs 450) for 100 (hatch ~100 after laying, UW and UMass; Matteson and Decker's eggs took 100–122 DD50 at constant 70–80 °F), weight 0.
- **Young larvae:** from hatch (176 after emergence) for 300, to about the 4th instar (NCR 327, Table 2, which puts stalk boring at the 5th, 550+), as larvae begin tunneling into midribs and then stalks (UW–Madison). Weight 1: the crop's risk.
- **Generations:** 1,100 apart (UW's peaks 631 and 1,733 are 1,102 apart; first moths 374 and 1,400, 1,026), with D36's default spread (the first flight's SD, ~117): the summer flight's 1 % at 1,388, peak 1,737, 99 % at 2,144, against UW's 1,400, 1,733 and summer treatments to 2,100. Two generations (`max_generations=2`), weighted alike (D37); no third, which MSU's code doesn't expect in most years either.
- **Window:** "Scout and treat young larvae before they bore in", 10–90 % of each generation's hatch: 671–986 and 1,713–2,142 degree days, against UW–Madison's 800–1,000 and 1,550–2,100. It opens before UW's first-generation window (UW's 800 is near peak hatch, 807) and closes after its second (UW's 1,550 is first hatch). Neither is wrong for scouting; sprays go by scouting thresholds.
- **One flight where the normal season is short** (version 0.3; Ben, 2026-11-23): where the 30-year normal total of degree days (modified 50/86 °F) from January 1 through August 1 is below 1,500, the model runs one flight, PERT (900, 1,400, 1,900), weight 0 (10, 50 and 90 % at 1,146, 1,400 and 1,653, against the northern traps' 1,112, 1,402 and 1,715: a little narrower than their few moths), with egg masses and young larvae timed from it as in the south, one generation. Its window to treat young larvae runs 1,323–1,828. The normal comes from the 30-year normal maps (`last30`, now 1996–2025; it moves a year each January), read at a point's cell and per cell on a map (`agmodels.spec.PlaceNormal`, `agmodels.phenology.PlaceForm`). Where it isn't available (outside the normals' area, such as a point outside the box), the model runs two flights and says so in a warning. Outputs `one_flight` (1 or 0) and `normal_dd_modified_50_86_to_08_01` say which form ran and on what normal. Why the normal and not this year's total, or latitude: this year's total by August 1 isn't known until after the one flight has begun, and it overlaps between north and south (Sparta 2020 reached 1,566 and caught both flights; Wausau 2021 reached 1,559 and caught one); latitude misses the cool Lake Michigan shore. UMN gives 1,100–1,300 for scouting univoltine larvae in Minnesota, earlier than this form's window; the form follows Wausau's traps.
- **Not EF-106:** VDIFN's first flight (550–900) began 176 degree days after UW's first moths and peaked 109 after; with single sine in place of the modified average (lower in spring), its dates ran later still (below).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_european_corn_borer.py`, run in CI:

- The modified average on hand-computed days (a minimum raised to 50, a maximum capped at 86), and the model's daily degree days the same.
- The spring flight begins at 374 (UW: 375) and peaks at 631 (UW: 631); the summer flight's first moths (1 %) at 1,388 (UW: 1,400) and peak 1,737 (UW: 1,733); its 99 % at 2,144 (UW's summer treatment ends at 2,100); two generations and no third.
- First eggs at 450 (UW: 450) and first hatch at 550 (UW: summer hatch 100 after eggs); young larvae begin at first hatch and carry the risk.
- The windows run from 671 to 986 and from 1,713 to 2,142, bracketing UW–Madison's 800 to 1,000 and 1,550 to 2,100.

### Against Apple 1952

Apple's stages are on his own method (the simple average above 50 °F, no upper, from the first day whose mean is above 50), so they were read off on the archive: at the Arlington cell (43.30, −89.35), 2016–2025, the day his method's total reached each stage, and the modified 50/86 total from January 1 that day (daily minimum and maximum from `/api/v2/weather/daily` through Django's test client in `uv run app/manage.py shell`; a one-off, not a committed script). His start day fell from February 20 to April 23.

<!-- prettier-ignore -->
| Apple's stage (Table 1, first found) | Apple's DD | Modified 50/86 from January 1, median (range) | UW's table, the model |
| --- | --- | --- | --- |
| Spring moths | 423 | 585 (506–626) | 374 first, 631 peak |
| First-generation eggs | 603 | 771 (687–821) | 450 first eggs |
| First-generation hatch | 699 | 858 (789–910) | ~550 first hatch |
| 50 % hatch (p. 879) | 1,000 | 1,156 (1,077–1,208) | 821 (the model's 50 % hatch) |
| Summer moths | 1,716 | 1,870 (1,773–1,912) | 1,400 first, 1,733 peak |
| Second-generation eggs | 1,787 | 1,940 (1,846–1,981) | 1,450 |
| Second-generation hatch | 1,901 | 2,050 (1,954–2,089) | 1,550 |

- UW's table isn't Apple's numbers on another method: on today's weather his first spring moths come about 210 degree days after the table's, near its spring peak, and his first summer moths about 470 after the table's, after its summer peak. Sycamore, Illinois (41.99, −88.69), gives the same within 15 degree days.
- DATCP's traps side with the table: the observed spring 50 % came at a median 694 and the summer 50 % at 1,651 (below), so Apple's first summer moths (1,870) would come after half the summer flight had been caught. Apple's "first" is the first stage found in plant examinations, which lags the first individuals, and his populations of 1946–1951 may have differed; either way his numbers would time the model one to three weeks late.
- His treatment timing (50 % hatch at 1,000, sprays at 1,100 and 1,200 of his own degree days) is 1,156–1,350 on the modified average, later than UW–Madison's 800–1,000 (Flandermeyer and Bick) and the model's window (671–986).

### Against Wisconsin's black light traps

`scripts/check_european_corn_borer.py`; full table in [european-corn-borer/traps.md](european-corn-borer/traps.md); data in [../data/datcp-blacklight-traps/](../data/datcp-blacklight-traps/README.md). The model runs on the archive at each black light site's cell from January 1, 2020–2026. Each site-year's weeks are split into spring and summer flights at the model's own trough there (`check_insect_traps.py` splits at July 7 instead). Days off: 0 inside the observed week, else days before (−) or after (+) it. "South" is everything below 44.6 °N (Arlington, Beaver Dam, East Troy, Hancock, Janesville, Manitowoc, Pardeeville, Prairie du Chien, Ripon, Sparta); "north" is Wausau, Marshfield and Antigo.

<!-- prettier-ignore -->
| Event (model against the observed week) | n | Within a week | Median, days | 10th–90th percentile |
| --- | --- | --- | --- | --- |
| South, spring flight, 50 % | 14 | 11 | 0 | −4 to +10 |
| South, spring flight, 50 %: VDIFN's peak (740, single sine) | 14 | 10 | +4 | 0 to +16 |
| South, spring flight, peak week | 14 | 10 | 0 | −8 to +8 |
| South, spring, first moths (1 %) against first catch | 24 | 15 | −6 | −12 to +3 |
| South, summer flight, 50 % | 23 | 12 | +1 | −8 to +20 |
| South, summer flight, 50 %: VDIFN's peak (1,950, single sine) | 23 | 9 | +14 | 0 to +33 |
| South, summer flight, peak week | 23 | 7 | +4 | −12 to +25 |
| North, the one flight's 50 % against the two-flight form's summer 50 % | 7 | 2 | +19 | +4 to +26 |
| North, the same against VDIFN's summer peak | 7 | 0 | +35 | +29 to +47 |
| One-flight sites, the one flight's 50 % against the one-flight form's | 7 | 4 | 0 | −9 to +8 |

- Leaving out Arlington 2021–2023, whose mid-May "corn borers" may be misidentified (data README, Caveats), the southern spring midpoint is −1 day (11 site-years) and the summer 0 (20).
- The model's first moths (1 %) come a median 6 days before the first week with a catch: a weekly trap with one to a few moths a week catches its first moth after the flight has begun, as codling moth's traps showed (D97).
- Observed degree days (modified 50/86 from January 1) at the middle of the observed weeks, south: spring 50 % median 694 (25th–75th percentile 647–731), against the model's 645; summer 50 % median 1,651 (1,387–1,881), against 1,745.
- The summer flight is wide in the traps (10th–90th percentile of days off −8 to +20): a split by the model's trough sorts late spring moths and early summer moths by the model's clock, and a site's flight rests on a handful of moths.

#### One flight or two

From the same run ([traps.md](european-corn-borer/traps.md), "One flight or two"):

- **South:** 34 site-years caught corn borers, 26 of them before the model's trough (236 moths before, 733 after). The season's 969 moths by degree days: 10, 50 and 90 % at 620, 1,400 and 2,075, two flights.
- **North:** 12 site-years caught corn borers, 4 of them before the trough, with 4 moths between them (145 after). The season's 149 moths, almost all at Wausau: 10, 25, 50, 75 and 90 % at 1,112, 1,287, 1,402, 1,600 and 1,715 degree days: one flight from mid-July to mid-August, between the bivoltine strain's two, as UMN's univoltine scouting window (1,100–1,300 for larvae) implies. Wausau never caught a June moth in six years.
- Degree days by August 1 in the trap years: south median 1,736 (1,309–2,020), north 1,462 (1,263–1,651). The research's guess for a second generation, 1,400 by about August 1, doesn't separate them: the north passed 1,400 by August 1 in most years and still had one flight.
- On the 1996–2025 normals, August 1 totals are Arlington 1,684, Hancock 1,567, Marshfield 1,453, Wausau 1,441 and Rhinelander 1,355. A threshold near 1,500 on the normal total separates the traps' two-flight sites from the one-flight sites (Sparta 2020, at 1,566 that year, caught both flights; Wausau 2021, at 1,559, one).

#### The one-flight form

From the same run ([traps.md](european-corn-borer/traps.md), "The one-flight form"), each site's 30-year normal by August 1 as the model reads it from the normal maps: Antigo 1,292, Manitowoc 1,309, Wausau 1,441 (Wausau E the same, Wausau N and North 1,460) and Marshfield 1,452 run one flight; Hancock 1,571, Ripon 1,596, Beaver Dam 1,638, Arlington 1,682, Sparta 1,686, Pardeeville 1,724, East Troy 1,736, Janesville 1,799 and Prairie du Chien 1,906 run two. So the rule puts every northern site in the one-flight form and every southern and central site but one in the two-flight form. The exception is Manitowoc, on the Lake Michigan shore, whose cool summers put it below 1,500; its trap caught two corn borers in four years (June 2, 2021 and August 19, 2020), which can't say how many flights it has.

At the one-flight sites, the season's whole catch against the form's flight: the 50 % week a median 0 days off (7 site-years, 4 within a week; 10th–90th percentile −9 to +8), the peak week a median 0 (7, 4 within a week), against the two-flight form's summer flight a median 19 days late. The first catch comes a median 5 days after the form's first moths (13 site-years, 5 within a week), the same lead as in the south, with a wide spread from single moths caught in June or late August.

### Typical dates on the normals

`uv run app/manage.py shell < scripts/corn_moth_normals.py`: the day each event's degree days are reached on AgWeather's 1996–2025 normal running total (modified 50/86 °F from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event | DD | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- | --- |
| Spring moths, first (1 %) | 420 | May 27 | May 30 | Jun 5 |
| Spring flight, peak | 631 | Jun 10 | Jun 13 | Jun 21 |
| Treat young larvae, first generation | 672–985 | Jun 13 to Jun 29 | Jun 16 to Jul 3 | Jun 23 to Jul 12 |
| Summer moths, first (1 %) | 1,388 | Jul 19 | Jul 24 | Aug 3 |
| Summer flight, peak | 1,737 | Aug 4 | Aug 10 | Aug 25 |
| Treat young larvae, second generation | 1,713–2,142 | Aug 3 to Aug 25 | Aug 9 to Sep 3 | Aug 24 to Sep 30 |
| Normal total, August 1 |  | 1,684 | 1,567 | 1,355 |

Rhinelander's normal by August 1, 1,355, is below 1,500, so the model runs one flight there; the two-flight rows above are what it would show without the normal. The one-flight form (the same script):

<!-- prettier-ignore -->
| Event | DD | Rhinelander | Wausau | Marshfield |
| --- | --- | --- | --- | --- |
| One flight, first moths (1 %) | 1,005 | Jul 13 | Jul 9 | Jul 9 |
| One flight, 50 % and peak | 1,400 | Aug 4 | Jul 30 | Jul 30 |
| One flight, 99 % | 1,794 | Aug 29 | Aug 22 | Aug 22 |
| Treat young larvae | 1,323–1,828 | Jul 31 to Sep 1 | Jul 26 to Aug 24 | Jul 26 to Aug 24 |
| Normal total, August 1 |  | 1,355 | 1,441 | 1,453 |

Against UW–Madison's descriptions: first eggs in southern Wisconsin from late May to mid-June (the model: first eggs ~450, about May 29 at Arlington; spring peak June 10); the summer flight "from late July or early August", peaking "around mid-August in central Wisconsin" (Hancock August 10); first-generation sprays "mid-June to early July in southern Wisconsin" (Arlington's window June 13–29). At Rhinelander, Wausau and Marshfield the model now runs one flight, from mid-July to late August, peaking at the end of July or early August, as Wausau's traps show it (from about mid-July, 1,112, to mid-August, 1,715).

## Limits and open questions

- **The one-flight form's bound** (1,500 on the 30-year normal by August 1) rests on three northern trap sites, mostly Wausau's six years; the line between them and Hancock (1,571) isn't pinned closer than that. No published source gives a degree-day bound: Hoard and Weiss 1995 and Showers et al. 1975 support the form's premise (voltinism is a property of the local population and its season), and neither has degree days by date. Places near 1,500 may have both strains, or a partial second generation, which neither form shows: at Carrington, North Dakota, a mostly univoltine population kept a bivoltine share that flew a second time in 1991, a season about 255 °F·d (142 °C·d) above the state's 30-year average, and not in the cool 1992 and 1993 (Hoard and Weiss 1995). A warm year in the one-flight area may do the same. Manitowoc's lake-shore normal (1,309) puts it in the one-flight form without trap evidence either way. On the normal maps (read 2026-11-23) the shore is below 1,500 from about Port Washington (1,439) north (Sheboygan 1,431, Two Rivers 1,184, Sturgeon Bay 1,274), and above it at Milwaukee (1,641) and Kenosha (1,591); inland, Green Bay (1,556), Stevens Point (1,563) and in the northwest Spooner (1,536), Ladysmith (1,512) and New Richmond (1,554) run two flights, so "from Wausau and Marshfield north" is approximate.
- **The normal moves:** it's the 30-year normal maps' (`last30`), which become 1997–2026 in January 2027; a place near the bound could change forms between years. A point outside the normals' area (outside the box) runs two flights with a warning; computing a 30-year normal there from Open-Meteo was judged too costly for a point request.
- **The one flight's spread** (PERT 900–1,900) is a little narrower than the northern traps' (10–90 % 1,146–1,653 against 1,112–1,715), and its window (1,323–1,828) is later than UMN's 1,100–1,300 for univoltine larvae in Minnesota.
- **Few moths.** Black light catches are 59–293 moths a year across the network, a handful at most sites; the north rests on Wausau (6 years) and a few moths at Marshfield and Antigo. DATCP doesn't split the Z and E pheromone races.
- **First catch:** the model's first moths come about a week before a weekly trap's first catch; that is expected, but it means "first moths" on the page is earlier than the first moth a grower's trap will show.
- **NCR 327's alternative:** a biofix at the first significant spring capture (simple average 50 °F) with larval stages from it; it says January 1 starts "have not been accurate". UW's table from January 1 fits Wisconsin's traps within days in the south, so the January 1 start stays (Anderson et al. 1982 also chose January 1 for post-diapause development in North Carolina); a grower's first-catch date isn't offered (it would need NCR 327's numbers and the simple average).
- **The table states no method.** XHT1087 gives only "base temperature = 50°F" for its corn borer numbers, with no upper threshold, way of averaging, start date, source or years (both the 2005 printing and the current web version). The model reads them on the modified of XHT1086's two methods (50/86 °F, from January 1), the one Flandermeyer and Bick use for corn borer and UMN's VegEdge uses for its corn borer model ("similar to the original model developed at the University of Wisconsin"; its page gives no stage numbers); that reading is an inference, though DATCP's traps fit it.
- **Apple 1952's numbers aren't used.** The table's provenance is unstated; Apple's own stages, on today's weather, fall one to three weeks after the table's and after the traps' flights ("Against Apple 1952"). The model's training-area years (1952–2012) run from his paper to the table's last revision.
- **The end of the spring flight (1,000)** is an estimate, not a published number; it sets the first window's close (986).
- **Young larvae's 300 degree days** come from NCR 327's instar timings on the simple average from first capture, applied on UW's method; Matteson and Decker's constant-temperature rearing agrees (the first four stadia in 286–329 DD50 at 70–80 °F), though in the field larvae see swings the laboratory didn't.
- The window follows hatch, not plant stage: sweet corn's risk depends on silking (A3422), which the model can't see.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_european_corn_borer.py
uv run python scripts/check_european_corn_borer.py    # needs the archive in data/
uv run app/manage.py shell < scripts/corn_moth_normals.py
```
