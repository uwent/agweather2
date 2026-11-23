# Apple scab (`apple-scab`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/apple_scab.py`, with its daily features from the 120 hours to each day's end in `agmodels.features.scab_features` (D96); green tip comes from `apple-stages`. The research notes this condenses (page and table for every number) are in the project's working notes, `docs/plans/models.md` part B2 and B5.

**In short:** the model is NEWA's apple scab model (D95) with the published ascospore maturity curve, run on wet hours estimated from humidity and rain, since the grid has no leaf wetness sensor. Its curves and tables reproduce their sources. We reproduced NEWA's own results exactly on four of its station pages, and on the hours of 63 Wisconsin orchard station-seasons our model finds 85 % of NEWA's infection periods from the station's weather and 82 % from the archive's, with some extra periods of its own. The wetness estimate finds about three in four of the infection events that orchard leaf wetness sensors give, and adds others: it errs toward more events. Infections haven't been checked against scab lesions in Wisconsin orchards.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Gadoury and MacHardy 1982 (doi:10.1094/Phyto-72-901) | Ascospore maturity: probit = 2.51 + 0.01 × degree days (base 0 °C, daily mean), R² 0.93, from the first mature ascospores (New Hampshire) | The maturity curve, unchanged |
| Stensvand, Eikemo, Gadoury and Seem 2005 (doi:10.1094/PD-89-0198) | The same curve started at green tip; degree days stop after 7 days in a row without rain (under 0.2 mm) and resume with the next rain; 50, 95 and 99 % mature at 250, 420 and 490 DD°C; 95 % released once a day rain over 2.5 mm above 10 °C follows 95 % maturity; 16 Norwegian site-years, 95 % release at 393–1,305 DD°C | The start, the dry-spell rule (without its dew-or-fog clause, as NEWA), the season's end, and the backstop at 1,300 DD°C |
| MacHardy and Gadoury 1989 (doi:10.1094/Phyto-79-304) | The Revised Mills criteria: ascospores infect about 3 hours sooner than Mills's table; one level (no light, moderate or heavy); rain that starts at night counted from 7 a.m. | The table, as NEWA tabulates it in °F |
| Gadoury et al. 2004 (doi:10.1094/PDIS.2004.88.8.869) | In 14 New York and New Hampshire site-years, more than 98 % of ascospores were released by 600 DD°C after green tip, and the maturity curve tracked trapped release (r² 0.82) | Support for reading modelled maturity as the supply of ascospores, and for dropping MSU's discharge curve |
| Stensvand et al. 1997 (doi:10.1094/PHYTO.1997.87.10.1046) | Wet hours for infection at 1–26 °C, including below 34 °F | Read only; NEWA's table stops at 34 °F and so does ours |
| NEWA's apple scab model (newa.cornell.edu) | Green tip at 101 DD43; maturity by Stensvand et al. 2005 with a logistic in place of the probit; daily release fractions; infection events from leaf wetness and rain, merged within 24 hours, judged by its Revised Mills table | The release fractions (no published source found; credited to NEWA), the infection rules, the table and the season's end; compared on the same weather (below) |
| Enviroweather (MSU) | The same maturity probit from green tip (110 DD42), forced to 100 % at 950 DD°F; RH ≥ 90 % or rain as wet without a sensor; a discharge curve credited to "Jones" | Compared only. The discharge curve has no source we could find and reaches 98 % only at about 934 DD°C, far later than Gadoury et al. 2004's traps: left out |
| Gleason et al. 1994 (doi:10.1094/PD-78-1011), Kim et al. 2002 (doi:10.1094/PDIS.2002.86.2.179), Sentelhas et al. 2008 (doi:10.1016/j.agrformet.2007.09.011), Gillespie et al. 1993 (doi:10.1175/1520-0450(1993)032<0567:UOWDTS>2.0.CO;2) | Leaf wetness estimated from weather: CART/SLD, dew point depression, an RH threshold | The candidates compared with Wisconsin's sensors ([../weather/leaf-wetness.md](../weather/leaf-wetness.md)); RH ≥ 90 % or rain won |

## Choices and differences

- **Green tip:** `apple-stages`' green tip (101 DD43, single sine from January 1, NEWA's threshold; NEWA's own sine differs slightly, so ours falls on its date or a day later), or the grower's date at a point. On the map each cell starts at its own green tip.
- **Maturity:** Gadoury and MacHardy's probit (NEWA uses a logistic within 2.3 percentage points of it), from green tip (NEWA starts a day before). A day's degree days count unless it ends 8 dry days in a row; the rain day that ends a dry spell counts, as Stensvand et al. 2005 have it (NEWA counts it from the next day). Dry means under 0.2 mm (the paper's; NEWA any rain, on gauges reading 0.01 in). The paper's clause that a day with 12 hours or more of dew or fog isn't dry is left out, as NEWA leaves it out.
- **Release:** NEWA's daily fractions: rain in the night (8 p.m. to 6 a.m.) releases 5 % of the mature ascospores not yet released, then rain in the day (7 a.m. to 7 p.m.) 90 % if it's at least 0.1 in and its rainy hours average at least 50 °F, 50 % if one holds, 25 % if neither. An hour is rainy at 0.01 in or more (NEWA: any amount).
- **The season's end:** Stensvand et al.'s and NEWA's rule (95 % mature, then a day rain over 0.1 in with its rainy hours above 50 °F). Ours marks the season over from the next day. As a backstop it ends at 1,300 DD°C after green tip (unadjusted), about the latest 95 % release in Stensvand et al.'s 16 site-years, so a cell with a dry or failed gauge can't stay open all summer: at Gays Mills in 2025, whose gauge recorded 0.26 in from April through June against the archive's 14, NEWA's season stayed open through October.
- **Infection periods:** NEWA's rules on estimated wetness: a period starts at an hour with rain, continues while hours stay wet (RH ≥ 90 % or rain ≥ 0.01 in) or rainy, and periods less than 24 hours apart join (their wet hours added, the gap not counted); an infection occurs when the wet hours reach the Revised Mills table at the period's mean temperature (34–79 °F). NEWA reads wetness from the station's sensor. Ours judges the period at each hour on its exact mean temperature so far; NEWA judges it once at its end on a mean of rounded values.
- **The infection's day:** the day the hours reach the table, when infection happens. NEWA labels the days the period starts and ends. Days are midnight to midnight CST (D74); NEWA's follow the local clock.
- **Only the primary season:** risk is shown from green tip until the season's end. NEWA's events run all season (16 at Baileys Harbor through August 2025); infections by conidia in summer aren't modelled.
- **The 120-hour window (D96):** each day's infection features come from the 120 hours to its end, so a period that began more than four days before is cut short and flagged. Wet spells that long are rare in spring.
- **Not modelled:** MacHardy and Gadoury's rule that counts rain starting at night from 7 a.m. (NEWA doesn't apply it either), Stensvand et al. 1997's hours below 34 °F, light, moderate and heavy infection (no source grades them except Mills's), and MSU's discharge curve.
- **Missing data:** a missing hour leaves that day's infection features missing; the model then counts the day as no infection and flags it as estimated, as it does for rain.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_apple_scab.py`, run in CI:

- Maturity at 250, 420 and 490 degree days (base 0 °C, DD°C) is 50, 95.6 and 99.2 % (tested within 0.5 percentage points), Gadoury and MacHardy's curve, which Stensvand et al. 2005 quote rounded as 50, 95 and 99 %. The curve also gives Gadoury and MacHardy 1982's own printed 69.5 % at 300 DD°C and 98.9 % at 477.
- The Revised Mills table as NEWA tabulates it: 41 wet hours at 34 °F, 8 at 55 °F, 6 at 70 °F, 11 at 79 °F, none outside 34–79 °F, the mean rounded half up as NEWA rounds it.
- The dry-spell rule (degree days stop on the 8th dry day and resume on the rain day), the season's end on a warm day rain after 95 % and the backstop at 1,300 DD°C, NEWA's release fractions, periods joining within 24 hours and not at 24, an infection put on the day it happens, rain needed to start a period, and a missing hour leaving the day missing, on hand-made seasons.

### NEWA's rules reproduced

`scripts/newa_reference.py check`. To compare with NEWA on many stations we recomputed NEWA's results from its model's published rules. Checked against Ben's exports of NEWA's apple scab page (its Infection Event Summary, Wet and Dry Log and Ascospore Maturity Summary) for Gays Mills 2025, Brighton 2025, Eau Claire 2024 and Baileys Harbor 2025, run on the same station hours: 1,173 daily infection rows, 387 wet and dry periods and 354 daily maturity rows, with 0 differences. Green tip, every infection event, maturity and release match NEWA's pages to the reported digit (rerun 2026-11-18). The same check covers NEWA's fire blight page.

### Against NEWA on the same weather

`scripts/check_apple_scab.py`; full table in [apple-scab/newa.md](apple-scab/newa.md). NEWA's results come from its rules on each station's own hours and leaf wetness sensor (above), at Wisconsin's NEWA orchard stations in 2024 and 2025. Ours run twice as a point run: on the station's own temperature, dew point and rain, with wetness estimated (so the difference is the method), and on the archive's hours at the station's cell (what the map shows). Compared from green tip through June 30; a NEWA infection period is matched when one of our infection days falls within it, a day either side. 67 station-seasons had a green tip and NEWA results; 4 are left out for failed rain gauges (below), so the totals are over 63.

| Inputs | NEWA's infection periods matched | Ours not in NEWA's | Green tip, ours − NEWA's |
| --- | --- | --- | --- |
| The station's hours | 669 of 786 (85 %) | 62 | mean +0.4 days, range +0 to +16 |
| The archive at the station's cell | 648 of 786 (82 %) | 96 | mean +0.4 days, range -20 to +21 |

- On the station's hours green tip falls on NEWA's day or the next (the two sines), except Spring Valley 2024 (+16 days, a cold spell as the total neared 101). On the archive it differs where the cell's degree days and the station's part early in a warm March (Waupaca 2024, Spring Valley 2024).
- The 95 % maturity date agrees within a day or two on the station's hours in most station-seasons; on the archive's hours it spreads more. Our season ends the day after NEWA's release day.
- The rest of the difference is the wetness estimate's (below): NEWA reads the station's sensor, we estimate wetness from humidity and rain.

**Failed gauges:** a station-season is left out of the totals when its gauge caught under 40 % of the archive's April–June rain at its cell, since NEWA's periods need the station's rain to start: Fort Atkinson 2024 (26 %), Gays Mills 2024 (10 %) and 2025 (2 %), and Genoa City 2025 (1 %, no NEWA infection all spring). A failed tipping bucket reads zero with an "observed" flag, so nothing in the data marks it. Wabasha 2024's gauge also looks partial (NEWA reaches 95 % maturity only on June 21), but it passed the test and is counted.

### The wetness estimate against orchard sensors

`scripts/compare_leaf_wetness.py`; full tables in [../weather/leaf-wetness.md](../weather/leaf-wetness.md). The sensors at NEWA's Wisconsin orchard stations, 2024–2026, observed hours only (an hour wet when the sensor read wet for 30 minutes or more), against 60 candidate estimates run on the station's hours and on the archive's at its cell. Scored by apple scab infection events by NEWA's rules on the estimate and on the sensor, as Cohen's kappa over station-days, since events are what the model reports. 86 station-seasons; Gays Mills 2024 and 2025 left out for failed gauges. This comparison tests the gauge over the station's observed hours only: Genoa City 2025 has no observed leaf wetness readings, so it isn't in it, and Fort Atkinson 2024 has only 464 observed hours, with too little rain in them to judge its gauge, so it stays in.

On the archive's hours, April–June, RH ≥ 90 % or rain ≥ 0.01 in (the rule the model uses):

| Measure | Value |
| --- | --- |
| Scab infection events, kappa | 0.656 |
| Events on both / the sensor only / the estimate only | 560 / 190 / 299 |
| Hours right | 0.852 |
| Wet hours a day, bias (estimate − sensor) | +0.46 |
| Wet hours a day, mean absolute error | 3.06 |

- Of the 750 events the sensors gave, the estimate found 560 (75 %); of its 859 events, 299 (35 %) had no event on the sensor. So the estimate errs toward more events.
- RH ≥ 91–94 % with rain scored within 0.01 of it; CART × 0.415 with rain 0.647 (+1.72 wet hours a day); dew point depression 2.0/3.8 with rain 0.597 (+2.60). Counting rain as wet always helped. On the stations' own hours the best thresholds run higher (92–95 %), since the archive's RH is a little drier than the stations' ([../weather/humidity.md](../weather/humidity.md)).
- July–September is wetter by the estimate than by the sensors: +2.71 wet hours a day on the archive. Primary scab is over by then.

## Limits and open questions

- **Green tip by degree days in a warm March:** 101 DD43 came in mid-March in 2024 across southern Wisconsin (Eau Claire March 14), weeks before buds moved in many orchards, so the season and its early infections can open too soon. A grower's green tip date fixes it at a point; the map can't.
- **Failed rain gauges:** a station's gauge that reads zero hides its infection periods and keeps NEWA's season open; the archive's rain (radar and gauge analysis) doesn't fail that way but can miss a local shower.
- **The wetness estimate** finds three in four of the sensors' infection events and adds others: it errs toward more events, and toward more wet hours in July–September. An open sensor stands for the wettest, upper canopy (Batzer et al. 2008, doi:10.1094/PDIS-92-1-0164), so neither side is the leaf inside a tree.
- **No lesion data:** infections are checked against NEWA and against sensors, not against scab that appeared in Wisconsin orchards. MacHardy and Gadoury's table was fitted in New Hampshire, the maturity curve in New Hampshire and Norway.
- **Release** by NEWA's daily fractions has no published source.
- One infection level; growers used to light, moderate and heavy from other tools won't find them.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_apple_scab.py
uv run python scripts/fetch_newa.py                                  # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/newa_reference.py check                        # NEWA's rules against exports of its pages in tmp/newa/apple-scab/
uv run python scripts/check_apple_scab.py                            # needs the archive in data/ and the station hours
uv run python scripts/compare_leaf_wetness.py --years 2024 2025 2026 # about 7 minutes
```

NEWA's code and the station hours stay out of the repository; the page exports are Ben's, kept locally.
