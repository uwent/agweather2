# Codling moth (`codling-moth`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/codling_moth.py`, run by the insect engine (`agmodels.phenology`, D36, D97); its page: `codling_moth.md` beside it. The research notes this condenses (page and table for every number) are in the project's working notes, `docs/plans/models.md` part B4.

**In short:** the curves reproduce their source, Washington State University's codling moth table, within a few percentage points; given the same first catch, egg hatch opens on NEWA's first-spray day or the next; the default first catch is set from Wisconsin's trap network and matches it within a week in most orchard-years. Egg hatch itself hasn't been checked against Wisconsin observations.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| WSU Apple IPM Transition Project, degree-day development table (archived 2012) | Cumulative % moth flight and egg hatch every 20 DD°F (50/88 °F, single sine) after first catch, both generations | The curves: fitted as D36 PERT curves (test fixture `packages/agmodels/tests/fixtures/codling_moth_wsu_table.tsv`) |
| Jones, Doerr and Brunner 2008 | WSU's model (PETE) run from January 1 in Washington; first catch 96 DD°C (SD 14.4, n = 34); events as accurate without a trapped biofix | That the curves can run from an estimated first catch |
| Jones and Wiman 2012 | The same model's adult flights as Johnson SB curves (DD°C, first catch at 96) | A check on the table: within ~20 DD°F of it in all three flights |
| Jones et al. 2013 | Mean first catch from January 1 by latitude below 400 m: 1923.387 − 73.806·lat + 0.745·lat² DD°C (R² 0.974; 346 location-years, 29 sites, none in Wisconsin, Minnesota or Iowa) | The default first catch's latitude trend |
| Riedl, Croft and Howitt 1976 (Michigan) | Biofix = first sustained catch, 281 ± 15 DD°F from January 1; first hatch 253 ± 5 DD°F after it (8 orchard-years); observed first hatch 474–634 from January 1, mean 552 | Checks on first hatch |
| Riedl and Croft 1978 | Half the larvae diapause at a day length of 10.242 + 0.1226·lat hours (about August 4 at 43–46 °N); degree days from January 1 on that date set the second generation's size (classes at 900, 1440, 1640, 1900) | The second generation's size output |
| Rock et al. 1993 | Codling moth's generation in Pennsylvania: 1030 DD°F start to start, 1174 peak to peak | A check on the generation time |
| NEWA's codling moth model (newa.cornell.edu) | DD50 without an upper from January 1; first catch at 404 unless given; first hatch 220 and first spray 250 after it; second generation's first catch 1501 after it | Compared on the same weather (below) |
| Enviroweather (MSU) | DD50 without an upper from March 1; biofix estimate 200; generation 2 counted from March 1 | Compared only; its generation 2 numbers match Riedl's counted from the biofix, so the March 1 start looks like a slip |

## Choices and differences

- **Degree days:** single sine, 50 °F, cutoff 86 °F (the sources use 88 °F; on the archive the difference is at most 9 DD by August 4 and 16 by October 31 at Gays Mills, 0.1 at Bayfield; Ben, 2026-11-18). NEWA and Enviroweather use no upper.
- **Curves:** adult flight PERT (0, 170, 964), egg hatch PERT (246, 405, 1189) in DD°F after first catch; the second generation 1084 later with D36's spread. Risk is egg hatch only (flight weight 0). Two generations, no third.
- **First catch:** the first moth caught (WSU's and Jones's definition), not the first sustained catch (Riedl's, NEWA's). Default: Jones et al. 2013's curve plus 120 DD°F (`WISCONSIN_SHIFT_F`), from the trap network below: 349 DD at 43 °N, 309 at 46 °N.
- **Hatch window:** 1 % to 95 % of each generation's hatch, about 262 to 809 DD after first catch.
- **Against NEWA:** a later default biofix in NEWA (404, which matches DATCP's first week with 5 or more moths), and its second-generation biofix at 1501 after the first, which is Riedl et al. 1976's summer peak catch (1486 ± 74) rather than the second flight's start (NEWA's own guide has second-generation moths from 771).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_codling_moth.py`, run in CI:

- Flight and egg hatch against WSU's table, both generations: within 3.5 percentage points everywhere and an RMSE of at most 1.2 (fit: flight 1.0 and 0.6, hatch 0.7 and 0.6 by generation).
- The window opens 262 DD after first catch, against Riedl et al. 1976's first hatch at 253 ± 5 and WSU's first cover spray at 250; it closes at 809, against the table's 95 % at 800.
- Jones et al. 2013's quadratic within 15 DD°C of its own site means at Allegan MI, Geneva and Highland NY, Burlington VT, Hood River OR and Biglerville PA.
- A trap date gives the same curves as the estimate shifted; two generations and no third; the size class on made-up seasons, in leap years, and from a trap date.

### Against NEWA on the same weather

`scripts/check_codling_moth.py`; full tables in [codling-moth/newa-and-wisconsin.md](codling-moth/newa-and-wisconsin.md). NEWA's results are recomputed from its model's published rules (`scripts/newa_reference.py`, which reproduces NEWA's apple scab and fire blight pages exactly, row for row, on the page exports Ben made for four station-seasons) on the hours of 34 Wisconsin NEWA orchard stations, 2024 and 2025 (67 station-seasons). Ours run on the same daily max and min, and on the archive at each station's cell.

| Ours − NEWA's, days | Median | 10th–90th percentile |
| --- | --- | --- |
| Hatch window opens, given NEWA's first catch as the trap date, against NEWA's first spray | +1 | 0 to +1 |
| First catch, ours estimated (station days) | −6 | −11 to −3 |
| First catch, ours estimated (archive) | −6 | −11 to −2 |
| Hatch window opens, ours estimated (station days) | −3 | −4 to −1 |
| Hatch window opens, ours estimated (archive) | −3 | −5 to 0 |
| Second generation's hatch, the same first catch | −17 | −24 to −16 |

Given the same first catch the two agree to a day; the remaining differences are NEWA's later default first catch and its later second-generation biofix (above).

### First catch against Wisconsin's traps

`scripts/check_codling_moth_traps.py`; full table in [codling-moth/traps.md](codling-moth/traps.md); data in [../data/datcp-apple-traps/](../data/datcp-apple-traps/README.md). DATCP's apple pest trap network, 2020–2025: 71 orchard-years without mating disruption whose first catch came after the first week read. A first catch is dated by its week, so "inside" means within the 7 days ending on the reported date.

| Default first catch | Inside the first week with a catch | Within a week of it | Median, days | 10th–90th percentile |
| --- | --- | --- | --- | --- |
| Ours | 27 | 50 | 0 | −11 to +9 |
| NEWA's (404 DD50) | 19 | 47 | +3 | −2 to +12 |

- Degree days (50/86 °F) from January 1 at the middle of the first week with a catch: mean 337, median 326, SD 129, no trend by latitude inside Wisconsin. Jones et al. 2013's curve alone gave 197–228 at the same sites, a median 8 days early: their sites were research orchards checked every day or two, DATCP's are commercial orchards checked weekly, where the first moth is caught later. Hence the 120 DD°F shift.
- **In sample:** the shift was fitted to these orchard-years, so this table shows the fit, not a test. A test needs years it wasn't fitted on: DATCP's 2026 tables when posted, or other Wisconsin trap records.
- Against the first week with 5 or more moths (DATCP's biofix threshold, 65 orchard-years), NEWA's default is on time (median 0, 20 inside) and ours a median 0 with more early (32 early, 12 late).

### Across Wisconsin

On the archive, 2016–2025, estimated first catch ([codling-moth/newa-and-wisconsin.md](codling-moth/newa-and-wisconsin.md), part 3): first catch in late May in the south, about June 9 at Sturgeon Bay and June 21 at Bayfield; the second generation class 4 (more than two thirds) nearly every year in the south and 2 in Door County and Bayfield, as Riedl and Croft 1978's maps show at the same latitudes in Michigan. First catch falls about 15–19 days after `apple-stages`' bloom, so NEWA's rule of thumb (first catch at 'Red Delicious' bloom) doesn't hold in Wisconsin's traps.

## Limits and open questions

- Egg hatch hasn't been checked against Wisconsin observations (fruit injury, hatch sampling). With the shifted first catch, first hatch comes near 610 DD from January 1, against Riedl et al. 1976's observed 552 in Michigan in 1973–74.
- The curves were fitted in Washington; Jones et al. 2013 asks for local validation of later events.
- The second flight's spread doesn't shrink with diapause in the north (D37's equal generations); Riedl and Croft 1978's year-specific summer curve is the option if trap data show the tail wrong.
- First catch varies by about 130 DD (SD) between orchards and years; a grower's trap date is better than any default.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_codling_moth.py
uv run python scripts/fetch_newa.py                 # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_codling_moth.py         # needs the archive in data/ and the station hours
uv run python scripts/check_codling_moth_traps.py   # needs the archive in data/
```
