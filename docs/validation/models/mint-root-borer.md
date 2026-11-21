# Mint root borer (`mint-root-borer`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H5). The model: `packages/agmodels/src/agmodels/insects/mint_root_borer.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `mint_root_borer.md` beside it. Version 0.1 was VDIFN's window (430, 1,280, 2,150 degree days, single sine 50 °F from April 1); this version keeps the same source, USPest's model, and draws its events as curves.

**In short:** Oregon State's mint root borer model (USPest `mrb`; Berry, Takeyasu and Morris 1997) as D36 curves: single sine above 50 °F from April 1, the moth flight through its first catch (430), peak (910) and 90 % catch (1,350), and the larvae in roots timed from it until each has made its winter chamber (half by 2,150). The moths carry no risk; the larvae do. The model was developed in the Pacific Northwest and is listed as partly validated; on California trap catches (Tollerup et al. 2013) it ran two weeks to a month late by the end of the flight. Nothing in Wisconsin has been compared.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| USPest's mint root borer model ([uspest.org, `mrb`](https://uspest.org/cgi-bin/ddmodel2.pl?spp=mrb), read 2026-11-21; Berry, Takeyasu and Morris 1997, Oregon State's Integrated Plant Protection Center, not online) | Single sine, 50 °F, upper threshold 130 °F (the program's default), from April 1; "partly validated", Pacific Northwest. Events: first moth catch 430, peak moth catch 910, peak egg laying 1,130, peak egg hatch 1,280, 90 % moth catch 1,350, 5 % form hibernacula 1,850, 50 % form hibernacula 2,150 | The method and every event |
| Tollerup, Marcum, Wilson and Godfrey 2013 ([doi:10.1603/IPM13004](https://doi.org/10.1603/IPM13004), J. Integr. Pest Manag. 4(3): A1–A4, open access) | The same model in °C·d (biofix April 1, 50 and 129 °F): 239, 506, 628, 710, 749, 1,028 and 1,194. Pheromone traps in peppermint, Shasta and Siskiyou counties, California, 2010–2011: one generation; flight about 60 days; the model "poorly predicted" emergence, peak and 90 % flight there (Table 1) | The flight's length (a check) and the California comparison |
| Pacific Northwest Insect Management Handbook, mint root borer (2026) | Life cycle: moths May through July; larvae in rhizomes and roots late July through September, into early October; sampling after harvest, late August to mid-September; 2–4 larvae per square foot | The window's purpose; the page's advice |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's window, three of USPest's events as (start, peak, end) | Replaced |

## Choices and differences

- **Degree days:** single sine, 50 °F, no upper threshold, from April 1 (USPest; its 129–130 °F upper never binds). The stored 50 °F total, from April 1.
- **Moth flight** (weight 0): PERT (279, 910, 1,817), its mode at the peak catch (910), through 2 % at 430 (the first catch) and 90 % at 1,350. Half the moths have flown at 945 and 99 % at 1,598. Moths don't feed, so they carry no risk (as western bean cutworm's moths).
- **Larvae in roots** (a `DerivedStage`, weight 1): from 370 degree days after each moth (USPest's peak catch 910 to its peak hatch 1,280; the peak egg laying, 1,130, lies between), for 835 degree days: half have hatched at 1,315 (945 + 370) and half have formed their winter chambers at 2,150, USPest's 50 % hibernacula. Each larva feeds until it has made its chamber, so the stage ends with the last larva, not at half; version 0.1 ended at half. Because the chambers' timing is the moths' spread moved later, 5 % have chambers at 1,705, before USPest's 1,850: USPest's hibernacula come closer together than its moths.
- **Action window:** "Trap or sweep for moths", from 2 % to 90 % of the flight (431 to 1,349, USPest's two flight events). The decision to treat comes from larvae dug after harvest (the handbook); the larval stage's peak, about 1,730, falls in that sampling season in southern Wisconsin (below).
- **Training area:** USPest's model is from Pacific Northwest peppermint (Oregon, Washington, Idaho); Berry, Takeyasu and Morris's years aren't in hand, so 1990–1997 is an estimate.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_specialty_insects.py`, run in CI:

- The moth flight passes 2 % at 430 degree days, peaks at 910 and reaches 90 % at 1,350, as the model's first catch, peak catch and 90 % catch (test: within 3).
- Half the larvae have hatched at 1,315 (the model's peak hatch 1,280; test: within 40) and half have formed their winter chambers at 2,150, as in the model (test: within 3); the first 5 % have at 1,705, earlier than its 1,850.
- From 2 % to 99 % the flight spans about 1,170 degree days (430 to 1,598), 50 to 60 days in a Wisconsin June and July, as the 60 days Tollerup et al. saw.

### Against trap catches in California

Tollerup et al. 2013 (Table 1), the same model run on California weather against pheromone trap catches in peppermint, 2010–2011; positive is the model later than the traps:

- First catch: observed 7 and 11 days before the model's date in 2010, 6 and 4 days after it in 2011; so moths were caught 4 to 11 days before or after its first catch.
- Peak flight: the model 10 to 25 days late in three of four county-years (Shasta 2010 about a day early).
- 90 % flight: the model 15 to 17 days late in Shasta and about a month late (29–30 days) in Siskiyou.

The authors found it a poor predictor there and doubted it carries across growing regions. The same model, run on California weather, was late. It hasn't been compared with catches in Wisconsin, and none are known to us.

### On the normals

`scripts/specialty_insect_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (single sine 50 °F, from April 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD50 from April 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First moths, 2 % (430) | June 4 | June 7 | June 13 |
| Moth flight peak (910) | June 30 | July 4 | July 13 |
| Moths 90 % (1,350) | July 21 | July 26 | August 7 |
| Half the larvae hatched (1,315) | July 20 | July 25 | August 5 |
| Most larvae in roots, the stage's peak (1,727) | August 8 | August 15 | September 1 |
| 5 % in winter chambers (1,705) | August 7 | August 13 | August 30 |
| Half in winter chambers (2,150) | August 29 | September 10 | not reached |
| Normal total on October 15 | 2,684 | 2,459 | 2,083 |

The handbook's moths fly May through July in the Pacific Northwest; here the model's flight runs from early June to late July in the south and to early August in the north. Its larvae fill the roots from late July into September, the handbook's season; at Rhinelander half the larvae haven't made their chambers by mid-October in an average year, and fall freezes end the season. UW–Madison has no mint root borer timing of its own (Commercial Vegetable Production in Wisconsin doesn't cover it).

## Limits and open questions

- **Developed in the Pacific Northwest** and listed as partly validated; in California it ran two weeks to a month late by the end of the flight. Wisconsin moth or larval counts would decide whether it runs late here too; none are known.
- **Berry, Takeyasu and Morris 1997** isn't online; the events are USPest's as published, without their data.
- **Hibernacula's spread:** the larvae's exit follows the moths' spread, so the first chambers come about 145 degree days before USPest's 5 %.
- **Moths carry no risk:** the risk rises with the larvae, after the moths have flown; the moth window is for traps and planning.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_specialty_insects.py
uv run app/manage.py shell < scripts/specialty_insect_normals.py  # the dates on the normals
```
