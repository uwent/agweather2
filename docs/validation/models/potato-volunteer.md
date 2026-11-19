# Potato volunteer survival (`potato-volunteer`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/potato_volunteer.py`, a seasonal product (D68); its page: `potato_volunteer.md` beside it. Ported in Phase 3 (PLAN.md, Phase 3 step 5) from the Wisconsin potato volunteer tool (an R Shiny app on Wisconet's stations; copy in `tmp/R/potato-volunteer-risk/`), which it replaces; version 0.2 (2026-11-05) took MSU's window.

**In short:** the rule is Michigan State University's (Kirk and Wharton): count the hours with soil below 27 °F over the winter, and 120 or more at a depth kills the tubers there; the Wisconsin tool's levels add 8 in to MSU's 2 and 4 in. The rule is ported as the tool applied it. What drives it, the hours below 27 °F, has been compared with Wisconet's soil sensors: the archive counts more of them than the stations, at 8 in about twice as many, which leans the risk low. The rule itself hasn't been checked against tubers' survival in Wisconsin.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Kirk and Wharton, "Potential survival of potato volunteers in Michigan" (MSU Extension) | Hours with soil below 27 °F at 2 and 4 in over the winter (November through March); more than 120 at both depths makes survival unlikely, at neither likely | The threshold, the depths and the window |
| The Wisconsin potato volunteer tool (`tmp/R/potato-volunteer-risk/global.R`, `calc_vol_risk`) | Wisconet's hourly soil at 2, 4 and 8 in; a depth with at least 120 hours below 27 °F lowers the risk a level, Very high (none) to Low (all three); a season from October 1 | The 8 in depth, the four levels and "at least 120" |
| UW Vegetable Pathology (2025), "Deep frost this winter limits risk of potato volunteers" | The tool's results for the 2024–25 winter | Background |

## Choices and differences

- **Window:** November 1 through March 31, MSU's, shown from January 1 (version 0.2). The tool counted a year from October 1, so it kept counting April's cold; soil doesn't fall below 27 °F in a Wisconsin October, so the start doesn't change Wisconsin's counts.
- **Threshold:** at least 120 hours, the tool's; MSU says more than 120.
- **Soil:** the archive's, not stations'. 2 and 4 in are ERA5-Land's 4 and 10 cm levels (IFS's for the newest days, provisional until ERA5-Land replaces them, D52); 8 in (20.3 cm) is interpolated between 10 and 30 cm. HRRR's soil was dropped for this model's sake: under its own snow its shallow soil swung with the air (D52, `docs/validation/weather/soil.md`).
- **Missing hours:** a day missing an hour adds nothing to the count (D25), which leans the risk high where data are short. The tool counted each missing hour as not killing, which leans the same way.

## Checks

### Hours below 27 °F against Wisconet's sensors

`scripts/compare_soil_wisconet.py`, in `docs/validation/weather/soil.md` (generated 2026-11-01): the archive at 80 Wisconet stations' cells against each station's sensors at 5, 10 and 20 cm, set against the 2, 4 and 8 in the model reads. Over the November–March days from January 2025 through March 2026 on which the station and every source have every hour, the hours below 27 °F per station-day (and the share of days with any):

| Depth | Station | Archive | Station-days |
| --- | --- | --- | --- |
| 2 in | 2.27 (14 %) | 3.15 (18 %) | 16,438 |
| 4 in | 1.75 (10 %) | 2.81 (15 %) | 16,121 |
| 8 in | 1.02 (6 %) | 2.18 (11 %) | 16,056 |

The archive counts about 40 % more hours than the stations at 2 in, 60 % more at 4 in and twice as many at 8 in. Over a winter that brings a depth to 120 hours sooner, so the archive's risk leans low against the stations'. Stations' soil under snow is insulated, and a field the wind has scoured of snow is colder, so a count above the stations isn't necessarily wrong for an open field. The archive's soil temperatures themselves are within about 1 °C of the stations on average in December–February (bias −0.86 to −0.94 °C by depth, same report).

The rule itself is the tool's (`test_potato_volunteer.py`, run in CI: the levels by depths reaching 120 hours, the window, a missing day, and the hour counts from hourly soil and the 8 in interpolation). It hasn't been run against the tool's own station-based results.

## Limits and open questions

- The 120-hour threshold and the depths come from Michigan's guidance; no Wisconsin observations of tuber survival have checked them.
- The archive's cold bias in winter soil (above) and the cell's average snow cover set the counts, not a particular field's.
- **Cheapest independent comparison:** the tool's own station-winters (the Wisconet hourly soil cached in `tmp/R/potato-volunteer-risk/data/`, winters 2023–24 to 2025–26): the risk level at each station from its sensors against v2's from the archive at its cell. A test of the rule itself needs volunteer counts in fields the following summer, from UW Vegetable Pathology or growers.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_potato_volunteer.py
uv run python scripts/compare_soil_wisconet.py   # needs the archive in data/ and Wisconet's API
```
