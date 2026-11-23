# Corn earworm (`corn-earworm`): validation

Model version 0.2, written 2026-11-21 (D98). The model: `packages/agmodels/src/agmodels/insects/corn_earworm.py`, run by the insect engine (`agmodels.phenology`, D36, D37); its page: `corn_earworm.md` beside it. Rebuilt in part H, batch H2 (`docs/models-plan.md`); the research notes this condenses are in the project's working notes (part H sources, "Corn earworm").

**In short:** rebuilt on Hartstack et al. 1976's development times as USPest.org runs them: single sine 55/92 °F from egg laying, larvae in the ears from 73 to 437 degree days after each egg. The eggs are spread as DATCP's pheromone traps show the main flight after its first week of 35 or more moths, and the default biofix moves from August 1 to August 15: in 2021–2026 that week came a median 15 days after August 1 and 1 day after August 15. Both are fitted to the same traps they're checked on. A migrant's arrival follows the weather to the south, so any fixed date is off by about 10 days in a typical year and by weeks in some (2025's large early-July flight); a grower's own date is better.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| USPest.org's corn earworm model (Oregon State; `ddmodel2.pl?spp=cew`, read 2026-11-21) | Hartstack et al. 1976; single sine, 55 and 92 °F; biofix first silk (default date August 1); events after egg laying (near first silk): 73 egg hatch begins, 220 3rd instar, 329 5th instar, 437 larvae exit ears to pupate, 760 adults begin to emerge, 873 adults begin to lay eggs; "partly validated", Pacific Northwest | The method, the biofix event, larvae 73–437, the generation (873) |
| Hartstack et al. 1976 (MOTHZV-2, a USDA simulation of _Heliothis_ population dynamics) | The development rates behind USPest's and UC IPM's events; from Texas (College Station) | Through USPest and UC IPM; not read (not online) |
| UC IPM, corn earworm model 1 (12.6/33.3 °C, single sine, intermediate cutoff) | In °F·d: egg 72.9, small larva 147.1, large larva 217.1, pupa 323.1, pre-oviposition 112.7; egg to adult 760.1; adult to adult 872.8 | A check: USPest's events are these sums |
| Coop, Croft and Drapek 1993 ([doi:10.1093/jee/86.3.906](https://doi.org/10.1093/jee/86.3.906)) | UC IPM's model 2: 12.5 °C, larva 360 | Compared only (larval period within 4 degree days of Hartstack's 364) |
| DATCP corn earworm pheromone traps, 2021–2026 (tabulated for this rebuild: [cew-pheromone-weekly.csv](../data/datcp-blacklight-traps/cew-pheromone-weekly.csv)) | Weekly moths at 12–16 sites, Hartstack traps set about July 1 and read to mid or late September | The default biofix and the egg-laying spread |
| DATCP black light traps, 2020–2026 | Corn earworm moths, 39–108 a year over the network | Background (below) |
| UW Vegetable Entomology; UW–Madison Horticulture; UMN VegEdge | Eggs first found on silks around August 1; a small June flight; larger flights from late July, the most damaging from mid-August to early September; thresholds 5–10 moths a night in pheromone traps, 3–5 in black light traps, three nights running | The significant-flight definition (35 a week, the low end of 5 a night); the page's guidance |

NEWA runs no corn earworm model, so D95 doesn't apply.

## Choices and differences

- **Degree days:** single sine, 55/92 °F (USPest's method; both thresholds stored on the grid), counted from the biofix.
- **Biofix:** egg laying: eggs first found on silks, or the first week of a significant moth flight in the grower's area. Default **August 15** (was August 1, VDIFN's and USPest's default). August 15 is where DATCP's traps put the main flight's first week of 35 or more moths (median 1 day after it; August 20 fits as well, mean absolute error 5.9 against 6.0 days): an earlier default errs toward protecting silks sooner, and is a round date for the page. A date, not degree days: the main flight's week varies by 10.7 days (SD) by date and by 159 degree days from January 1, 10.6 days at late August's rate, so degree days place a migrant no better than the calendar.
- **Egg laying:** PERT (0, 45, 920) after the biofix, weight 0, fitted to the main flight's catches after its first week (quartiles 81, 141 and 266 degree days; the curve's 73, 152 and 263). Its tail is longer than the traps show past 75 % (90 % at 383 against 505): traps come down in September, and catches are male moths, a proxy for females laying.
- **Larvae in ears:** from 73 to 437 degree days after each egg is laid (`DerivedStage`, lag 73, duration 364), weight 1: the crop's damage. Activity is at least 0.75 (Very high) from 291 to 519 degree days after the biofix.
- **One generation:** a generation is 873 (adult to adult), more than the 484–776 degree days DATCP's sites reached between August 15 and October 15 in 2021–2026 (median 652). The eggs' own moths rarely emerge, and pupae don't survive Wisconsin winters.
- **No action window:** silks must be protected before eggs hatch, which depends on silking and trap catches the model can't see; the page points to the trap thresholds instead.
- **VDIFN's ramp** (70, 275, 440, a single egg-laying day with the severity peak at 275) is replaced: its numbers were USPest's 73 and 437 rounded, with a peak of its own.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_corn_earworm.py`, run in CI:

- Single sine 55/92 °F, biofix August 15.
- Larvae enter the ears 73 degree days after each egg is laid and leave them 437 degree days after, as in the source; larvae carry the risk.
- The egg-laying curve's quartiles within 15 degree days of the traps' 81, 141 and 266.
- One generation.

### Against Wisconsin's pheromone traps

`scripts/check_corn_earworm.py`; full table in [corn-earworm/traps.md](corn-earworm/traps.md). Site-years with 50 or more moths (63 with a main flight). The main flight's week: the first week with 35 or more moths (5 a night) from July 25. Days off: 0 inside the week (the 7 days ending on its date), else days before (−) or after (+) it.

<!-- prettier-ignore -->
| Default date | Inside the week | Within a week | Median, days | Mean absolute, days |
| --- | --- | --- | --- | --- |
| August 1 (VDIFN's, USPest's) | 0 | 21 | −15 | 14.9 |
| August 8 | 16 | 25 | −8 | 9.2 |
| August 15 (the model's) | 9 | 42 | −1 | 6.0 |
| August 20 | 17 | 46 | 0 | 5.9 |

- **In sample:** August 15 was chosen from these site-years, so this table shows the fit, not a test.
- Counting any week of 35 or more (not only from July 25), August 15 is a median 1 day early, within a week in 34 of 63: in 2025 moths arrived in numbers in early July (Clinton 276 in the week ending July 3; Sun Prairie, Watertown, Mayville 123–252 in July's first weeks), a flight a fixed date can't follow.
- By year, the main flight's first week of 35 or more (median across sites): 2021 August 25, 2022 September 1, 2023 August 24, 2024 August 22, 2025 August 14, 2026 August 12. Half the season's moths were caught by August 21 to September 9.
- The northern sites (Wausau, Marshfield) caught 0–18 moths a season: the flights that matter are in the south and center.
- DATCP's black light traps catch few earworm moths (39–108 a year); their first catches, median by year, came from late June (2024) to August 24 (2023), mostly in late July.

### Typical dates on the normals

`uv run app/manage.py shell < scripts/corn_moth_normals.py`: the day each event's degree days (single sine 55/92 °F) from the biofix are reached on AgWeather's 1996–2025 normals. A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event | DD | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- | --- |
| From August 15: first larvae in ears | 73 | Aug 20 | Aug 20 | Aug 22 |
| From August 15: the most larvae in ears; first leave | 437 | Sep 19 | Sep 27 | after Oct 15 |
| From August 15: normal total by October 15 |  | 574 | 505 | 406 |
| From August 1: first larvae in ears | 73 | Aug 5 | Aug 5 | Aug 6 |
| From August 1: the most larvae in ears; first leave | 437 | Aug 30 | Sep 3 | Sep 13 |

From the new default, larvae fill the ears from late August through September in southern and central Wisconsin, matching UW–Madison's "mid-August to early September" moths as the damaging ones. At Rhinelander September's cool weather slows them, and the first larvae haven't left the ears by mid-October on the normals.

## Limits and open questions

- **Hartstack et al. 1976 hasn't been read** (not online); the events are USPest's and UC IPM's, which agree with each other. The development rates are from Texas; USPest calls the model "partly validated" in the Pacific Northwest. No Wisconsin data on egg hatch or larval timing.
- **The June flight:** a small flight usually reaches Wisconsin in June and threatens very early sweet corn (UW–Madison Horticulture; UMN). DATCP's pheromone traps go up about July 1, so they don't see it, and the default can't follow it. A grower's date (first eggs on early silks) can.
- **One egg-laying event per biofix:** moths keep arriving after the main flight's first week; the egg-laying curve spreads the eggs over the flight as the traps show, but a second wave weeks later (2025's July flight, then August's) needs a second biofix the model doesn't offer.
- **The default is fitted in sample**, to six years of one network; DATCP's 2027 tables, when posted, are a test. Ben (2026-11-23) kept August 15 as the default, labelled on the page, the topic page and here as fitted to DATCP's 2021–2026 traps.
- **Black light and pheromone traps differ** in what they catch; the significant-flight definition (35 a week) is ours, from the low end of UW's nightly threshold, not DATCP's.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_corn_earworm.py
uv run python scripts/check_corn_earworm.py    # needs the archive in data/
uv run app/manage.py shell < scripts/corn_moth_normals.py
```
