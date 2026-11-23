# Black cutworm (`black-cutworm`): validation

Model version 0.4, written 2026-11-21 and revised 2026-11-23 for the cutting window (version 0.3) and Kaster and Showers 1984's outdoor development times (version 0.4) (D98; part H, batch H2, round 2, and the papers' second round). The model: `packages/agmodels/src/agmodels/insects/black_cutworm.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `black_cutworm.md` beside it. Version 0.1 was VDIFN's window (300, 700, 1,000 degree days, single sine 50/86 °F from May 15), checked only against VDIFN; this report replaces that one.

**In short:** the caterpillars follow Kaster and Showers 1984's development times, measured outdoors in weather shelters in Iowa in spring, after Luckmann et al. 1976's egg, counted from a significant moth capture; the first caterpillars hatch where Purdue's and Iowa State's table says and reach cutting size a day or so before it, and each caterpillar pupates near the table's pupae (613 after its egg, the table's 641). Version 0.3 used Luckmann's constant-temperature laboratory times, which ran behind larvae outdoors. Without a grower's date the capture is May 1, the median first week with 9 or more moths in DATCP's pheromone traps. Cutting itself hasn't been compared with field reports.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Luckmann, Shaw, Sherrod and Ruesink 1976 ([doi:10.1093/jee/69.3.386](https://doi.org/10.1093/jee/69.3.386)), read in full | A colony from moths caught at Urbana-Champaign, Illinois, kept 5 months, reared singly on pinto bean diet at constant 18.3–29.4 °C (Table 1). Threshold 10.4 °C (10.5, 10.4 and 10.4 to the fifth molt, pupation and emergence, 10.44 average; 10.7 from three other studies); rates almost linear from 18 to 30 °C (Fig. 1). Table 2, median (range) °C·d from oviposition: hatch 52 (30–107), molts 99, 134, 170 (150–275), 208, 261, 346 (the 7.1 % with a seventh instar, n = 24), pupation 405 (357–509), emergence 643 (585–745); larval period 353, pupa 238 | The egg: hatch 94 °F·d after it is laid (52 × 1.8). Versions 0.2–0.3 also took the fourth instar (third molt) 306 and pupation 729 (Table 2 × 1.8; confirmed against the paper), replaced in 0.4 by Kaster and Showers' outdoor times. The threshold, 10.4 °C, which Kaster and Showers counted on too |
| Story, Keaster, Showers and Shaw 1984 ([doi:10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)), read in full | Larval bait traps in 48, 57 and 22 cornfields in Missouri, Illinois and Iowa, 1979–1981; black cutworm in 54–69 % of fields (Table 1). Mean instar against Allen's sine at 10.4 °C from January 1 (Fig. 2): "several fields" had larvae "far ahead" of the earliest maturity Luckmann's times allow even from eggs laid before any degree days; 4th and 5th instars at under 125 °C·d (sine; 100 by the simple average) from January 1; larvae too small for the traps before 50–75. The authors question predicting larval maturity "on the basis of moth captures in pheromone traps, laboratory-generated developmental data, and ambient air temperatures", naming microclimate and diet | A limit (below) |
| Kaster and Showers 1984 ([doi:10.1093/ee/13.2.384](https://doi.org/10.1093/ee/13.2.384)), read in full | Ankeny, Iowa, 1981–1982: larvae from a colony at most three generations from the wild, reared from hatch on diet in standard weather shelters (spring, April 30 to June 30; summer; autumn), and in field plots on weeds and seedling corn. Table 1, °C·d above 10.4 from hatch for the median individual, spring and summer: 2nd instar 31 and 30, 3rd 62 and 56, 4th 106 and 106, 5th 135 and 141, 6th 172 and 184, pupa 288 and 332, adult 482 and 532 (no difference between spring and summer, so no effect of daylength). In the shelters the Illinois model (Luckmann's times) never ran ahead of the larvae and was usually behind; in the 1981 plots it ran behind (5th instars when it had 3rd), in 1982 ahead. Air and soil temperature (5–7.6 cm) gave much the same predictions | Version 0.4: the spring column, fourth instar 105.7 and pupation 288.3 °C·d after hatch (Table 1, p. 387; confirmed), after Luckmann's hatch (52): 284 and 613 °F·d after the egg is laid. Air temperature is a fair input |
| Krupke and Obermeyer 2023 (Purdue Pest&Crop) and Iowa State's black cutworm page | Base 50 °F after a significant capture (biofix): hatch 90; 1st–3rd instars 91–311, leaf feeding; 4th instar 312–364, cutting begins; 5th 365–430; 6th 431–640; pupa 641–989. Iowa State: a significant capture is 8 or more moths in a wing-style pheromone trap over two nights. Purdue's table is "modified from Luckmann et al., Journal of Economic Entomology, June 1976" (reread 2026-11-23); Iowa State's names no source | The method (50 °F, from the capture), the stage names, and checks |
| DATCP's black cutworm pheromone network, 2021–2023 and 2026 ([data](../data/datcp-blacklight-traps/README.md)) | Weekly catches at 30–102 sites a year from late March to early June; the threshold of 9 moths is ours, after UW Vegetable Entomology's nine or more a night on two nights in a black light trap (DATCP's trap page gives none) | The default capture date, May 1 |
| USPest.org's black cutworm model (`bcw`; VDIFN's spreadsheet) | Single sine 50/86 °F from peak trap capture | The 86 °F cutoff |
| VDIFN | (300, 700, 1,000) from May 15 | Replaced |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, the extension tables' base. Luckmann's threshold, 10.44 °C (50.8 °F), would count about 40 °F·d fewer over May and June: on the archive at Arlington and Rhinelander, 2016–2025, 50.8 puts the start of cutting 1.1–1.8 days later on average (at most 3) and the end 2.2–2.8 days later (at most 4). That is within the weekly trap dates' resolution, and 50.8 °F would need a running total of its own, so 50 is kept (measured on version 0.3's times; the shift is much the same on 0.4's). Luckmann's rates are linear from 18 to 30 °C, which supports a cutoff near 86 °F.
- **Biofix:** a significant moth capture, the grower's date; without one, May 1, fitted to DATCP's black cutworm pheromone traps, 2021–2023 and 2026 (below), so its check on those traps is in sample (Ben, 2026-11-23: kept, labelled as fitted). The flight is a migration on storm fronts, so its date doesn't follow local degree days.
- **Development times** (version 0.4; Ben, 2026-11-23): Kaster and Showers 1984's spring weather-shelter times (Table 1) in place of Luckmann et al. 1976's constant-temperature ones. Their larvae, at most three generations from the wild, were reared outdoors under Iowa's fluctuating temperatures, and Luckmann's times never ran ahead of them and were usually behind (their Fig. 2); Story et al. 1984 found field larvae ahead of Luckmann's times too. The spring column, because the spring larvae are the ones that cut corn (spring and summer didn't differ significantly). Kaster and Showers reared from hatch, so Luckmann's egg (52 °C·d) is kept: fourth instar (52 + 105.7) × 1.8 = 284 °F·d after the egg is laid (was 306), pupation (52 + 288.3) × 1.8 = 613 (was 729). Their field plots disagreed between years (the model's simulation behind the larvae in 1981, ahead in 1982), so the evidence is mixed, but the shelters, the cleanest comparison, all pointed one way.
- **Stages:** egg laying, a PERT curve (0, 50, 350) °F·d after the capture (10, 50 and 90 % at 23, 82 and 174), weight 0; leaf-feeding caterpillars from 94 to 284 after each egg, weight 0; cutting caterpillars from 284 to 613 after each egg (fourth instar to pupation), weight 1, the risk. Egg laying is spread because moths keep arriving after a significant capture: in DATCP's pheromone traps, after each site-year's first week with 9 or more moths, half the later moths were caught within 63 °F·d and 90 % within 239, while traps were still read (a median 209 after it, so the tail is cut off). Purdue's and Iowa State's table counts every egg from the capture day.
- **One generation:** the moths arriving in spring give the caterpillars that cut seedlings (Minnesota: usually only the first generation damages corn). UW Vegetable Entomology counts three generations a year in Wisconsin; later ones aren't modelled.
- **Action window** (version 0.3; part H, round 2): "Scout and treat while caterpillars can cut plants", from the first caterpillars big enough to cut (1 % of the generation in the cutting stages) until 90 % have pupated: 289 to 787 °F·d after the capture (311 to 903 on version 0.3's times). The engine's usual windows are fractions of a stage complete, which for a stage timed from another counts caterpillars that have left it, so they can't open when the first reach cutting size; a "present" window (`ActionWindow(when="present")`) opens when a share has entered the stage and closes when a share has left it. Version 0.2 had no window.
- **Against the table:** the first caterpillars hatch where the table says (99 against 90) and reach cutting size a day or so before it (289 against 312; Kaster and Showers' fourth instar, 284 after the egg). Each caterpillar pupates 613 after its egg, near the table's 641; with egg laying spread over the following weeks, half have pupated by 695 and 90 % by 788, inside the table's pupal span (641–989). Purdue says its table is modified from Luckmann et al. 1976, and its 640 matches Luckmann's larval period (353 °C·d, 635 °F·d) counted from the capture rather than from hatch. Its pupae also fit Kaster and Showers' spring times with Luckmann's hatch added, pupation 340 °C·d (613 °F·d) and moths 534 °C·d (962 °F·d) after the egg, against Luckmann's own moths at 643 °C·d (1,157 °F·d), far from 989. Version 0.3, on Luckmann's times, had half pupated by 811 and 90 % by 904.
- **Against VDIFN:** VDIFN's window started at 300 (as cutting does) but peaked at 700 and ran to 1,000 from a fixed May 15.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_black_cutworm.py`, run in CI:

- The development times are Kaster and Showers' spring Table 1 after Luckmann's egg: hatch 52 × 1.8 = 94, fourth instar (52 + 105.7) × 1.8 = 284, pupation (52 + 288.3) × 1.8 = 613, each sooner than Luckmann's own (306, 729).
- The first leaf-feeding caterpillars (1 % of the curve's peak) appear at 99 °F·d after the capture, against the table's hatch at 90; the first cutting caterpillars at 289, against 312.
- Half the eggs are laid by 82 °F·d, so half the caterpillars present can cut by about 366; nearly every caterpillar is in the cutting stages from about 575. Each caterpillar pupates 613 after its egg, near the table's pupae from 641; half have pupated by 695 and 90 % by 788, inside the table's pupal span to 989. Cutting activity ends before 900.
- One generation; risk 0 before cutting, 1 when every caterpillar is cutting.
- The window to scout and treat opens at 289 °F·d after the capture, with the first cutting caterpillars, and closes at 787, when 90 % have pupated.

Version 0.3 (Luckmann's times) had the first cutting caterpillars at 311, half cutting by 388, half pupated by 811 and 90 % by 904, and its window 311 to 903.

### The default capture date against Wisconsin's traps

`scripts/check_cutworms.py`, part 1; full table in [black-cutworm/traps.md](black-cutworm/traps.md); data in [../data/datcp-blacklight-traps/](../data/datcp-blacklight-traps/README.md) (`bcw-pheromone-weekly.csv`, tabulated for this check). Weekly counts can't show DATCP's two-night threshold, so each site-year's first week with 9 or more moths stands in for the significant capture (the earliest week it could have come), dated by its middle day.

- 129 trap-years reached 9 in a week (77 never did; 4 did in their first week read and are left out). The week's middle came at a median day 121 (May 1), 10th–90th percentile day 102–137, SD 13.0 days; at a median 142 DD50/86 from January 1 (10th–90th percentile 74–271, SD 96). Yearly medians: April 11 (2021, n = 19), May 5 (2022, n = 10), May 1 (2023, n = 30), April 26 (2026, n = 70).

<!-- prettier-ignore -->
| Default | Median error, days | Mean absolute error, days | Within 7 days | 10th–90th percentile |
| --- | --- | --- | --- | --- |
| A fixed date, May 1 (day 121) | 0 | 10.3 | 60 of 129 | −19 to +16 |
| A fixed total, 142 DD50/86 from January 1 | 0 | 11.3 | 45 of 129 | −20 to +16 |

- **In sample:** both defaults are the medians of these trap-years, so this shows the fit, not a test.
- The capture date doesn't depend on the development times, so version 0.4 leaves this check as it was (rerun 2026-11-23: the same table).
- Northern traps reached 9 later (pooled within years, about 6.5 days later per degree of latitude), but northern traps were also set later in 2026 (many first read April 29), so part of that is when they started; a single statewide date is kept.

### Normal dates

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 50/86 °F), counting from the default May 1, version 0.4, with version 0.3's date on Luckmann's times:

<!-- prettier-ignore -->
| Event (°F·d after the capture, 0.4; 0.3) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First caterpillars hatch (99; 99) | May 14 | May 16 | May 19 |
| First caterpillars can cut (289; 311) | May 31 (was June 2) | June 2 (was June 4) | June 7 (was June 8) |
| Half the caterpillars can cut (366; 388) | June 6 (was June 7) | June 8 (was June 9) | June 13 (was June 14) |
| Half have pupated (695; 811) | June 24 (was June 30) | June 27 (was July 3) | July 4 (was July 11) |
| 90 % have pupated (787; 903) | June 29 (was July 5) | July 2 (was July 8) | July 9 (was July 16) |
| Purdue's end of cutting (640) | June 22 | June 24 | June 30 |
| Window to scout and treat | May 31 to June 29 (was June 2 to July 5) | June 2 to July 2 (was June 4 to July 8) | June 7 to July 9 (was June 8 to July 16) |

The window opens a day or two sooner and closes six or seven days sooner.

Version 0.1 (VDIFN's window from May 15) reached 300 around June 8 and its peak, 700, around June 29 at Arlington. UW–Madison's field crops guide (A3646) has corn scouted from emergence for two to three weeks; corn planted in early to mid-May emerges in late May, so that scouting falls just before and into the model's start of cutting in southern Wisconsin.

## Limits and open questions

- **Laboratory or outdoor times.** Version 0.4 follows Kaster and Showers 1984's weather-shelter times rather than Luckmann et al. 1976's constant temperatures, as outdoor larvae ran ahead of the laboratory times in the shelters and in Story et al. 1984's fields ("far ahead" in several). The evidence is mixed: in Kaster and Showers' field plots the laboratory times ran behind the larvae in 1981 but ahead of them in 1982 (5th and 6th instars where the simulation had 6th and 7th or pupae), which they put down to soil moisture. Their shelter larvae were reared on diet, one per cup, in standard weather shelters, in 1981–1982 at one place. If the field larvae of 1982 are the rule, the model's window now closes a few days early; read it as when cutting is likely, and scout. Air temperature stays: Kaster and Showers found soil (5–7.6 cm) and air gave much the same predictions.
- **The egg is still Luckmann's** (52 °C·d from oviposition, constant temperatures); no outdoor egg time was measured. If eggs are as much faster outdoors as larvae, cutting would begin a little sooner still.
- Cutting hasn't been compared with field reports of cutting in Wisconsin (DATCP's bulletins report some; not tabulated).
- The default capture uses the first week with 9 or more moths, an earlier event than a two-night count of 9; DATCP's own biofix dates by site would be the better target (in its weekly bulletins and Field Notes; not tabulated).
- The egg-laying spread is set from male moths' catches in pheromone traps, cut off when traps stop in early June.
- 2024 and 2025's pheromone tables weren't found.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_black_cutworm.py
uv run python scripts/check_cutworms.py   # needs the archive in data/
# The normal dates: /api/v2/climate/normals?dd=sine_50_86 at each place (Arlington 43.30, −89.35; Hancock 44.12, −89.53;
# Rhinelander 45.64, −89.41) through Django's test client in `uv run app/manage.py shell`, read off at each total
```
