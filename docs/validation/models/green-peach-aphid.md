# Green peach aphid (`green-peach-aphid`): validation

Model version 0.1, written 2026-11-21 (D98, D101). The model: `packages/agmodels/src/agmodels/insects/green_peach_aphid.py`, a fitted stage (D36, `agmodels.phenology.FittedStage`) reading `green_peach_aphid_fit_calendar.csv` (day of year, the default) and `green_peach_aphid_fit.csv` (degree days) beside it; its page: `green_peach_aphid.md`.

**In short:** the model reads the typical week's catch of winged green peach aphids in Wisconsin's suction traps off curves fitted to the traps' records for 2010 and 2014–2023 (Bradford and Groves, unpublished). In a typical season the flight passes 10 % of its peak on August 8, half on August 21, peaks on September 1 and falls to half on September 13. With each year or trap left out, the calendar described the held-out catches better than degree days at every base tried, so the model reads the calendar by default; degree days are an option. Neither clock times a single trap's season well (errors of about a month), so the model shows typical pressure, not a forecast.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Suction trap aphid records (EDDMapS, submitted by Doris Lagos-Kutz, University of Illinois Urbana-Champaign), `tmp/R/pvy-model/data/` | Weekly catches by species at Wisconsin's suction traps | *Myzus persicae*: 213 of 1,345 sampled trap-weeks at 9 traps had the species (1,304 aphids) in 2010 and 2014–2023; a sampled trap-week without it counted as 0; 2011–2013 left out (no usable weather) |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison), 2026-11-19: `tmp/R/cpb/cv/20_aphids.R`, findings `tmp/R/cpb/report-cv-aphids.md`, outputs `tmp/R/cpb/cv/out/aphids/` | Tweedie GAMs (`bam`, fREML) of each catch at the midpoint of its week on the day of year, and on degree days at bases 32–52 °F (upper 86 °F, single sine, from January 1; AgWeather's archive, gridMET fitted to it before 2016), with year, trap and trap-season effects; each fitted with each year and each trap left out | The typical year's curves (random effects at zero) on the log scale, by day of year (123–312) and at 39.2 °F (280–5,680 degree days), exported by `tmp/R/cpb/cv/31_aphid_models.py` |

## Choices and differences

- **The calendar by default (D101):** it described the catches better out of sample (below) and in sample (deviance explained 72 % against 67 % at 39.2 °F). The green peach aphid's late-summer flight is of winged forms produced as host plants mature and days shorten, and migrants on southerly winds; local warmth doesn't drive either.
- **Degree days as an option:** 39.2 °F (4 °C), the base of the PVY vector model; no base did better (they differ little).
- **Reading the curves:** linear between the values; 0 before the data (May 3 or 280 degree days; the curves are under 1 % of the peak there); held after (November 8 or 5,680) until fall freezes end the season.
- **Count:** the typical year's fitted mean for a typical trap (the median across years and traps on the log scale), 1.47 green peach aphids per trap-week at the calendar peak, 0.91 at the degree-day peak.
- **Risk:** the catch over its peak, with the D36 thresholds (Low from 0.05, Moderate 0.25, High 0.5, Very high 0.75).
- **Training area (D101):** Wisconsin (traps from Grant and Walworth counties in the south to Oneida County in the north); elsewhere the model runs with a warning.
- **Season (D128):** a migrant, so its season opens on the calendar, July 15, everywhere, and ends after October 31.

## Checks

### Against the fit

`packages/agmodels/tests/test_aphids_on_potato.py`, run in CI, against the fit's events (`tmp/R/cpb/cv/out/aphids/aphid_events.csv`), within a day or 10 degree days:

| Event | Calendar | Degree days (39.2/86 °F) |
| --- | --- | --- |
| First activity (10 % of peak) | Day 220 (August 8) | 2,380 |
| Rise (half the peak) | Day 233 (August 21) | 2,900 |
| Peak | Day 244 (September 1) | 3,410 |
| Decline (half the peak) | Day 256 (September 13) | 3,940 |

With each year left out the calendar events moved by at most 5 days (first activity between days 215 and 221, the peak between 243 and 245), and the degree-day events by up to 230 (the rise between 2,860 and 3,130); with each trap left out, the calendar events moved about as much and the degree-day peak fell between 3,160 and 3,580.

### Leaving years and traps out

Held-out Tweedie deviance, each degree-day base against the calendar (positive: the calendar better; 95 % bootstrap interval): leaving each year out (11 years), at 39.2 °F +678 (+114 to +1,673), and the calendar better in 10 of the 11 years; at every base from 32 to 52 °F the interval excluded 0. Leaving each trap out (9 traps), at 39.2 °F +1,010 (+112 to +2,167), the calendar better at 7 of the 9 traps.

Timing a held-out trap-season (the day its catch passed 10 %, 50 % and 90 % of the season's total), root mean square error: by degree days 32.4, 30.8 and 30.8 days; by the calendar 35.3, 31.6 and 30.0 days (52 to 66 trap-seasons). A single trap's weekly catches are too sparse to time its season: these errors say how far one trap's season can stray from the typical one, not how good either curve is.

## Limits and open questions

- **Flight, not colonies:** the traps catch aphids in flight. Field scouting counts of green peach aphids per leaf (1,553 records, 69 % zeros, mostly 2018–2020) were too thin for a curve: their first activity moved between 1,750 and 3,550 degree days across folds. In central Wisconsin's scouting counts they were rarely found on leaves before mid-August.
- **Presence records:** weeks with no aphids of any kind aren't in the EDDMapS export, so a trap-week counted as sampled had some record; weeks with nothing at all are missing rather than zero.
- **Wisconsin only:** the calendar curve is Wisconsin's season; elsewhere its dates don't apply, and the degree-day curve assumes the flight follows the same pattern by heat.
- **Cheapest independent comparison:** the traps' 2024–2026 seasons against the curve.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_aphids_on_potato.py
# the fit (weather from cv/wx_dd.py), then the export:
cd tmp/R/cpb && OPENBLAS_NUM_THREADS=1 Rscript cv/20_aphids.R && Rscript cv/21_aphid_export.R && cd ../../.. && uv run python tmp/R/cpb/cv/31_aphid_models.py
```
