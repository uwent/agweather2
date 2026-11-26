# Potato aphid (`potato-aphid`): validation

Model version 0.1, written 2026-11-21 (D98, D101). The model: `packages/agmodels/src/agmodels/insects/potato_aphid.py`, a fitted stage (D36, `agmodels.phenology.FittedStage`) reading `potato_aphid_fit.csv` (degree days, the default) and `potato_aphid_fit_calendar.csv` (day of year) beside it; its page: `potato_aphid.md`.

**In short:** the model reads the typical count of potato aphids per 25 sweeps in central Wisconsin's potato fields off curves fitted to a decade of scouting counts (Bradford and Groves, unpublished). Counts pass 10 % of their highest at about 2,520 degree days (August 1) and half at about 3,360 (August 30), and are still near their highest when scouting ends in mid-September. With each year left out, degree days described a held-out year's counts better than the calendar (a warm year's aphids build earlier by date), while the calendar timed the season's rise as well or better.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Pest Pros' field scouting records, 2014–2025, as loaded by Ben (`tmp/R/cpb/1_load_pest_pros.R`) | Potato aphids per 25 sweeps, where the scout recorded a count | 9,085 counts (46 % zeros) at 1,619 fields of 68 farms, days 128–257 (May 8 to September 14). A blank is taken as not checked (Ben, 2026-11-21: some scouts leave a zero blank, depending on the scout and the form), so only recorded counts are used |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison), 2026-11-19: `tmp/R/cpb/cv/20_aphids.R`, findings `tmp/R/cpb/report-cv-aphids.md`, outputs `tmp/R/cpb/cv/out/aphids/` | Tweedie GAMs (`bam`, fREML) of the count on degree days at bases 32–52 °F (upper 86 °F, single sine, from January 1, at each field's cell; AgWeather's archive, gridMET fitted to it before 2016) and on the day of year, with each year's own curve, farm and farm-year effects; each fitted with each year and each of 10 groups of farms left out | The typical year's curves (random effects at zero) on the log scale, at 39.2 °F (420–4,060 degree days) and by day of year (128–257), exported by `tmp/R/cpb/cv/31_aphid_models.py` |

## Choices and differences

- **Degree days by default (D101):** they described a held-out year's counts better than the calendar (below), and they're the clock that can follow the season to other places. The calendar is an option; it timed the season's rise as well or better.
- **Base 39.2 °F (4 °C):** the PVY vector model's; leaving years out, 32 °F did slightly better on counts (−10,916 against −8,013 against the calendar), within each other's intervals.
- **Reading the curves:** linear between the values; 0 before the data (420 degree days or May 8; the curves are about 0.1 % of their highest there or less); held after (4,060 or September 14) until fall freezes end the season. Scouting ends before the counts decline, so the held value is the season's highest or near it.
- **Count:** the typical year's fitted mean for a typical farm, 7.9 potato aphids per 25 sweeps at the degree-day curve's highest (3,760), 12.5 at the calendar curve's last day.
- **Risk:** the count over its highest, with the D36 thresholds.
- **Training area (D101):** the scouting service's counties in central Wisconsin (the 12 with 10 or more scouted fields for the Colorado potato beetle; 11 of them have 10 or more fields with potato aphid counts).
- **Season (D128):** its season opens at each place on the day early-planted potatoes emerge in a typical year (the crop model's degree days on the area's 30-year normal, from the early planting), averaged over about 50 km: May 9 at Madison, May 15 at Hancock, May 27 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) May 6. Where we don't have the normals it opens on June 15. It ends after September 30 whatever the weather.

## Checks

### Against the fit

`packages/agmodels/tests/test_aphids_on_potato.py`, run in CI, against the fit's events (`tmp/R/cpb/cv/out/aphids/aphid_events.csv`), within a day or 10 degree days:

| Event | Degree days (39.2/86 °F) | Calendar |
| --- | --- | --- |
| First activity (10 % of the highest) | 2,520 | Day 213 (August 1) |
| Rise (half the highest) | 3,360 | Day 242 (August 30) |
| Highest | 3,760 (the curve ends at 88 % of it) | Day 257 (the last day scouted) |

With each year left out, first activity moved between 2,400 and 2,630 degree days (days 207 to 221) and the rise between 3,300 and 3,440 (days 236 to 247).

### Leaving years and farms out

Held-out Tweedie deviance at 39.2 °F against the calendar (negative: degree days better; 95 % bootstrap interval): leaving each year out (12 years), −8,013 (−18,247 to −231), degree days better in 10 of the 12 years; at 32 °F −10,916. Leaving each of 10 groups of farms out, +658 (−364 to +1,613): no difference. Degree days carry a warm year's counts further up the curve by a given date, which the calendar can't.

Timing a held-out season (the day its counts passed 10 %, 50 % and 90 % of the season's total), root mean square error over 12 seasons: by degree days 14.9, 11.3 and 8.5 days; by the calendar 13.8, 9.6 and 5.4 days.

## Limits and open questions

- **Managed fields:** fields are treated with a systemic insecticide at planting and sprayed for aphids when counts reach a threshold (Ben, 2026-11-21); the curves show typical pressure in such fields, not untreated populations. Which fields were sprayed, and when, isn't in the data.
- **Recording changed:** potato aphid counts were recorded at 7–13 % of visits in 2014–2021 and 29–52 % in 2022–2025; a blank can't be told from a zero, so earlier years rest on the visits where scouts wrote a number.
- **No decline:** scouting ends in mid-September, with counts near their highest.
- **Central Wisconsin only:** northern seed potato fields, sprayed for aphids more consistently, aren't in the data. The suction traps' potato aphid catches were too sparse to check the field curve (94 trap-weeks with the species in 11 years).
- **Cheapest independent comparison:** the 2026 season's scouting counts against the curve.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_aphids_on_potato.py
cd tmp/R/cpb && OPENBLAS_NUM_THREADS=1 Rscript cv/20_aphids.R && Rscript cv/21_aphid_export.R && cd ../../.. && uv run python tmp/R/cpb/cv/31_aphid_models.py
```
