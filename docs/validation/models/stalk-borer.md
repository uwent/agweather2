# Stalk borer (`stalk-borer`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H4). The model: `packages/agmodels/src/agmodels/insects/stalk_borer.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `stalk_borer.md` beside it. Version 0.1 was VDIFN's window (1,110, 1,400, 1,700 degree days, single sine 41/86 °F from January 1), labelled as moth flight and checked only against VDIFN; this report replaces that one.

**In short:** one stage, caterpillars moving from grassy areas into corn, timed by degree days above 41 °F from January 1: first movement at about 1,100, 10 % at about 1,400 and half at about 1,650, as Lasack and Pedigo 1986 measured in Iowa and Iowa State's and UW–Madison's guides give them. A window from about 1,300 to 1,700 covers the guides' scouting and spraying. It hasn't been compared with observations in Wisconsin (stalk borer isn't in DATCP's traps).

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Lasack and Pedigo 1986 ([doi:10.1093/jee/79.6.1697](https://doi.org/10.1093/jee/79.6.1697)), Iowa, as its abstract and Rice and Davis 2010 report it (the paper isn't in hand) | Pitfall traps between grassy areas and corn: moving larvae mostly 4th to 6th instars; first caught at about 600 °C·d and half at about 900 (base 5.1 °C from January 1), consistent between years; little movement after 1,100 °C·d | The curve's start, middle and end (1,080, 1,620 and 1,980 °F·d) |
| Rice and Davis 2010 ([doi:10.1603/IPM10006](https://doi.org/10.1603/IPM10006)) | Lasack and Pedigo's numbers as 1,110 and 1,650 FDD (base 41.2 °F); scout at 1,300–1,400, spray at 1,400–1,700 if needed; no upper threshold | The window |
| Iowa State, Stalk Borer (Table 2) | Base 41 °F from January 1: egg hatch 575–750; scouting from 1,300; 10 % larval movement 1,400; treatment decisions 1,400–1,700; 50 % (peak) 1,700. No upper threshold stated; no source given for the table | 10 % at 1,400 |
| UW–Madison, Pest Management in Wisconsin Field Crops (A3646, 2025), pp. 53–54 and 74 | Base 41 °F: scout border rows at 1,300–1,400; movement first at about 1,110 and peaking at about 1,650; treat between 1,400 and 1,700; check last year's weed patches from 900–1,000; thresholds by leaf stage (Table 2-8, adapted from Iowa State) | The window; checks |
| Levine 1983 ([doi:10.1093/aesa/76.5.892](https://doi.org/10.1093/aesa/76.5.892)), Illinois | Thresholds: egg 8.4 °C, larva 3.7, pupa 6.1, egg to adult 5.1 (41.2 °F); Allen's (1976) sine from January 1, no upper; one generation; 50 % egg hatch at 256.8 °C·d (462 °F·d) and 50 % moth catch at a Lanark, Illinois, black light at 1,946.7 °C·d predicted (September 12; observed September 19) | The method |
| VDIFN | 41/86 °F; (1,110, 1,400, 1,700) labelled "adult flight" | Replaced |

## Choices and differences

- **Degree days:** single sine above 41 °F, no upper threshold, from January 1 (Levine's 5.1 °C, as Lasack and Pedigo and the guides use it). None of the sources uses an upper threshold. VDIFN's 86 °F cutoff changes the normal total by July 15 by 1–3 degree days (Arlington 3.1, Hancock 2.8, Rhinelander 1.3). Allen's sine as Levine used it may be a double sine (his equation 7); not checked, and the difference over a spring is small.
- **One stage:** "Caterpillars moving into corn", a PERT curve (1,100, 1,670, 2,100), weight 1: 10, 50 and 99 % at 1,390, 1,652 and 2,018. The middle sits between Lasack and Pedigo's 1,620 (1,650 in A3646 and Rice and Davis) and Iowa State's 1,700. One generation a year; the moths fly from August to October, after the season this models.
- **Window:** "Scout corn borders and treat if needed" from 3 % moved to 60 %, 1,292 to 1,704 degree days: the guides' scouting from 1,300 and spray window 1,400–1,700. Sprays work only while caterpillars are moving, before they bore in.
- **Against VDIFN:** VDIFN's labels called these numbers moth flight; they are caterpillar movement. Its peak at 1,400 was the start of the spray window, not the peak of movement.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_stalk_borer.py`, run in CI:

- The curve starts at 1,100 (Lasack and Pedigo's first catch, 600 °C·d, 1,080 °F·d; A3646's 1,110).
- 10 % have moved at 1,390 degree days, against Iowa State's 1,400.
- Half at 1,652, against Lasack and Pedigo's 1,620 (1,650 in UW–Madison's guide and Rice and Davis) and Iowa State's 1,700.
- 99 % at 2,018, against little movement after 1,100 °C·d (1,980 °F·d).
- The window runs from 1,292 to 1,704 degree days, as the guides' 1,300 to 1,700.
- The model hasn't been compared with observations in Wisconsin: stalk borer isn't counted in DATCP's traps, and no Wisconsin records of movement are known to us.

### Normal dates

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 41 °F without an upper threshold, from January 1):

<!-- prettier-ignore -->
| Event (°F·d from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Window opens: scout border rows (1,292) | June 19 | June 23 | July 1 |
| 10 % moved (1,390) | June 22 | June 26 | July 5 |
| Half moved (1,652) | July 1 | July 6 | July 15 |
| Window closes (1,704) | July 3 | July 8 | July 17 |
| 90 % moved (1,895) | July 9 | July 14 | July 24 |

Version 0.1 (41/86 °F) reached 1,110, 1,400 and 1,700 around June 12, June 23 and July 3 at Arlington. A3646 gives no dates; the topic page puts 1,110 around June 12 at Arlington and 1,650 around July 1.

## Limits and open questions

- Lasack and Pedigo 1986 isn't in hand: its numbers come from its abstract and Rice and Davis 2010, and its study years (the training area's 1983–1985) are an estimate.
- Iowa State's 10 % at 1,400 has no stated source; it may be its own reading of the same data.
- Caterpillars from last year's weed patches inside a field start feeding on corn earlier (A3646: check those patches from 900–1,000); the model times movement from field edges.
- No Wisconsin observations.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_stalk_borer.py
# The normal dates: /api/v2/climate/normals?dd=sine_41 at each place (Arlington 43.30, −89.35; Hancock 44.12, −89.53;
# Rhinelander 45.64, −89.41) through Django's test client in `uv run app/manage.py shell`, read off at each total
```
