# Black cutworm (`black-cutworm`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H2). The model: `packages/agmodels/src/agmodels/insects/black_cutworm.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `black_cutworm.md` beside it. Version 0.1 was VDIFN's window (300, 700, 1,000 degree days, single sine 50/86 °F from May 15), checked only against VDIFN; this report replaces that one.

**In short:** the stages follow Luckmann et al. 1976's laboratory development times, counted from a significant moth capture; the first caterpillars hatch and reach cutting size where Purdue's and Iowa State's table says, but cutting ends later than the table has it (the table's 641 is short of Luckmann's pupation). Without a grower's date the capture is May 1, the median first week with 9 or more moths in DATCP's pheromone traps. Cutting itself hasn't been compared with field reports.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Luckmann, Shaw, Sherrod and Ruesink 1976 ([doi:10.1093/jee/69.3.386](https://doi.org/10.1093/jee/69.3.386)), Illinois colony | Threshold 10.4 °C (10.44 average; 10.7 from three other studies); Table 2, median °C·d from oviposition: hatch 52, molts 99, 134, 170, 208, 261, 346 (7-instar subset), pupation 405, emergence 643; larval period 353, pupa 238; rates linear from 18 to 30 °C | Hatch 94, fourth instar (the third molt) 306 and pupation 729 °F·d after the egg is laid |
| Story, Keaster, Showers and Shaw 1984 ([doi:10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)), Missouri, Illinois and Iowa, 1979–1981 | Allen's sine at 10.4 °C from January 1; field larvae in corn often "far ahead" of Luckmann's predictions; 4th and 5th instars at under 125 °C·d from January 1; the authors question predicting larval maturity from moth captures and laboratory rates | A limit (below) |
| Krupke and Obermeyer 2023 (Purdue Pest&Crop) and Iowa State's black cutworm page | Base 50 °F after a significant capture (biofix): hatch 90; 1st–3rd instars 91–311, leaf feeding; 4th instar 312–364, cutting begins; 5th 365–430; 6th 431–640; pupa 641–989. Iowa State: a significant capture is 8 or more moths in a pheromone trap over two nights | The method (50 °F, from the capture), the stage names, and checks |
| DATCP's black cutworm pheromone network, 2021–2023 and 2026 ([data](../data/datcp-blacklight-traps/README.md)) | Weekly catches at 30–102 sites a year from late March to early June; DATCP's significant capture is 9 or more moths in two nights | The default capture date, May 1 |
| USPest.org's black cutworm model (`bcw`; VDIFN's spreadsheet) | Single sine 50/86 °F from peak trap capture | The 86 °F cutoff |
| VDIFN | (300, 700, 1,000) from May 15 | Replaced |

## Choices and differences

- **Degree days:** single sine, 50/86 °F, the extension tables' base. Luckmann's threshold, 10.44 °C (50.8 °F), would count about 40 °F·d fewer over May and June: on the archive at Arlington and Rhinelander, 2016–2025, 50.8 puts the start of cutting 1.1–1.8 days later on average (at most 3) and the end 2.2–2.8 days later (at most 4). That is within the weekly trap dates' resolution, and 50.8 °F would need a running total of its own, so 50 is kept. Luckmann's rates are linear from 18 to 30 °C, which supports a cutoff near 86 °F.
- **Biofix:** a significant moth capture, the grower's date; without one, May 1 (below). The flight is a migration on storm fronts, so its date doesn't follow local degree days.
- **Stages:** egg laying, a PERT curve (0, 50, 350) °F·d after the capture (10, 50 and 90 % at 23, 82 and 174), weight 0; leaf-feeding caterpillars from 94 to 306 after each egg, weight 0; cutting caterpillars from 306 to 729 after each egg (fourth instar to pupation), weight 1, the risk. Egg laying is spread because moths keep arriving after a significant capture: in DATCP's pheromone traps, after each site-year's first week with 9 or more moths, half the later moths were caught within 63 °F·d and 90 % within 239, while traps were still read (a median 209 after it, so the tail is cut off). Purdue's and Iowa State's table counts every egg from the capture day.
- **One generation:** the moths arriving in spring give the caterpillars that cut seedlings (Minnesota: usually only the first generation damages corn). UW Vegetable Entomology counts three generations a year in Wisconsin; later ones aren't modelled.
- **No action window:** the engine's windows are fractions of a stage complete, and for a stage timed from another (here the cutting caterpillars, from egg laying) that fraction is of caterpillars that have left the stage, so a window can't open when the first reach cutting size. The cutting caterpillars' activity is the window to read instead.
- **Against the table:** cutting begins in the same place (first caterpillars at 311, the table's 312). It ends later: Purdue's 640 matches Luckmann's larval period (353 °C·d, 635 °F·d) counted from the capture rather than from hatch; Luckmann's own pupation is 405 °C·d (729 °F·d) after the egg. With egg laying spread over the following weeks, half the caterpillars have pupated by 811 and 90 % by 904.
- **Against VDIFN:** VDIFN's window started at 300 (as cutting does) but peaked at 700 and ran to 1,000 from a fixed May 15.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_black_cutworm.py`, run in CI:

- The development times are Luckmann's Table 2 × 1.8: hatch 94, fourth instar 306, pupation 729; pupation less hatch is their larval period, 353 °C·d.
- The first leaf-feeding caterpillars (1 % of the curve's peak) appear at 99 °F·d after the capture, against the table's hatch at 90; the first cutting caterpillars at 311, against 312.
- Half the eggs are laid by 82 °F·d, so half the caterpillars present can cut by about 388; nearly every caterpillar is in the cutting stages from about 597, and half have pupated by 811 and 90 % by 904, against the table's pupae from 641. Cutting activity ends before 1,000.
- One generation; risk 0 before cutting, 1 when every caterpillar is cutting.

### The default capture date against Wisconsin's traps

`scripts/check_cutworms.py`, part 1; full table in [black-cutworm/traps.md](black-cutworm/traps.md); data in [../data/datcp-blacklight-traps/](../data/datcp-blacklight-traps/README.md) (`bcw-pheromone-weekly.csv`, tabulated for this check). Weekly counts can't show DATCP's two-night threshold, so each site-year's first week with 9 or more moths stands in for the significant capture (the earliest week it could have come), dated by its middle day.

- 129 trap-years reached 9 in a week (77 never did; 4 did in their first week read and are left out). The week's middle came at a median day 121 (May 1), 10th–90th percentile day 102–137, SD 13.0 days; at a median 142 DD50/86 from January 1 (10th–90th percentile 74–271, SD 96). Yearly medians: April 11 (2021, n = 19), May 5 (2022, n = 10), May 1 (2023, n = 30), April 26 (2026, n = 70).

<!-- prettier-ignore -->
| Default | Median error, days | Mean absolute error, days | Within 7 days | 10th–90th percentile |
| --- | --- | --- | --- | --- |
| A fixed date, May 1 (day 121) | 0 | 10.3 | 60 of 129 | −19 to +16 |
| A fixed total, 142 DD50/86 from January 1 | 0 | 11.3 | 45 of 129 | −20 to +16 |

- **In sample:** both defaults are the medians of these trap-years, so this shows the fit, not a test.
- Northern traps reached 9 later (pooled within years, about 6.5 days later per degree of latitude), but northern traps were also set later in 2026 (many first read April 29), so part of that is when they started; a single statewide date is kept.

### Normal dates

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 50/86 °F), counting from the default May 1:

<!-- prettier-ignore -->
| Event (°F·d after the capture) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First caterpillars hatch (99) | May 14 | May 16 | May 19 |
| First caterpillars can cut (311) | June 2 | June 4 | June 8 |
| Half the caterpillars can cut (388) | June 7 | June 9 | June 14 |
| Half have pupated (811) | June 30 | July 3 | July 11 |
| 90 % have pupated (904) | July 5 | July 8 | July 16 |
| Purdue's end of cutting (640) | June 22 | June 24 | June 30 |

Version 0.1 (VDIFN's window from May 15) reached 300 around June 8 and its peak, 700, around June 29 at Arlington. UW–Madison's field crops guide (A3646) has corn scouted from emergence for two to three weeks; corn planted in early to mid-May emerges in late May, so that scouting falls just before and into the model's start of cutting in southern Wisconsin.

## Limits and open questions

- **Field larvae can run ahead of these times.** Story et al. 1984 found black cutworms in Midwest corn "far ahead" of Luckmann's predictions from January 1 and questioned predicting larval maturity from moth captures and laboratory rates; soil-surface temperatures and diet may differ from air temperatures and the lab's. Read the model as when cutting is likely to start, and scout.
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
