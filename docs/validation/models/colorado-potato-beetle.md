# Colorado potato beetle (`colorado-potato-beetle`): validation

Model version 0.3, written 2026-11-21 (D98, D101). The model: `packages/agmodels/src/agmodels/insects/colorado_potato_beetle.py`, four fitted stages (D36) run by the insect engine (`agmodels.phenology.FittedStage`), reading `colorado_potato_beetle_fit.csv` (degree days) and `colorado_potato_beetle_fit_calendar.csv` (day of year) beside it; its page: `colorado_potato_beetle.md`. Version 0.1 (2026-10-28 to 2026-11-18) was the Crop Risk Tool's step table, 0.2 (2026-11-18 to 2026-11-21) Ben's fits on gridMET's degree days; their reports are in git history. The separate `colorado-potato-beetle-adults` and `-larvae` models (VDIFN's) are retired in favor of this one's outputs.

**In short:** the model reads adults, egg masses and larvae, and adults and larvae together, off GAM curves fitted to a decade of scouting counts in central Wisconsin's potato fields (Bradford and Groves, unpublished), by degree days 52/86 °F or, as an option, by calendar date. Refitted with each year or each farm left out, the curves describe a held-out season's counts better than no curve (about 20 % less error) and their events move little (±20 degree days, ±2 days). But in these fields the calendar timed a held-out year's events as well as degree days did: the beetle's dates varied little between years, and the fields are too close together to test how timing shifts with latitude, which is the reason to prefer degree days elsewhere. The model says so, and warns outside the counties the data came from.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Pest Pros' field scouting records, 2014–2025, as loaded by Ben (`tmp/R/cpb/1_load_pest_pros.R`) | Adults and larvae per 25 sweeps of a standard net in the canopy, egg masses per plant, at 1,937 fields of 69 farms; each cell a main count, with the scout's counts at the field's edges (`edges=`) and in hot spots (`patches=`) where recorded | Every visit from March on (13 rows dated January–February dropped as entry errors, Ben, 2026-11-21) |
| Bradford and Groves, unpublished analysis (Vegetable Entomology Lab, UW–Madison): `tmp/R/cpb/3_cpb_phenology.R`, 0.2's curves | GAMs (`y ~ s(x, bs = "cs")`, k = 13; egg masses k = 11) of log(count + 1) on degree days 52/86 °F from January 1, with filters for early outliers and the top 0.1 % of counts | The model's form, filters and stages |
| The refit (`tmp/R/cpb/cv/10_cpb_cv.R` with `COUNT_RULE=mean`, exported by `cv/30_export.py`; the cross-validation's first run is `tmp/R/cpb/report-cv-aphids.md`) | The same GAMs on AgWeather's archive, with each visit's count the mean of its main, edge and patch counts; every year and every farm left out in turn; the same fits on the day of year | The curves (below) |
| The Crop Risk Tool (`tmp/R/crop-risk-tool/src/models.R`, `cpb`) | A rounded step table of the first analysis on 50/86 °F | Compared only (below) |

## Choices and differences

- **Each visit's count (Ben, 2026-11-21):** the mean of the main count and the edge and patch counts recorded with it, a blank main count taken as 0. Edges or patches were recorded at 74,138 and 46,929 of 101,725 stage counts; where recorded they were about twice the main count (adults 6.2 at edges against 3.2 in the field). 0.2 used the main count alone for every stage, so it never saw an edge or patch count, and it dropped the 1,681 counts with only an edge or patch value (the loader's rule for them, the edge count halved or the patch count quartered, was a placeholder, Ben). Taking the main count alone (a blank as 0) moves the events 3 to 30 degree days later than the mean does and lowers the counts; how the clocks compare is the same under either rule.
- **Degree days:** single sine, 52 °F, cutoff 86 °F, from January 1, from AgWeather's archive at each field's cell for 2016–2025 and gridMET fitted to it (D84) for 2014–2015. 0.2 used gridMET's own, which ran 31 degree days above the archive at the scouting visits (0 to 74 by year), so its events came 1 to 3 days late on the archive's weather.
- **The calendar curves (D101):** the same GAMs on the day of year. They're the typical season where the data came from; outside central Wisconsin they don't move with the latitude or the year, so the model warns there.
- **Reading the curves:** linear between the values every 10 degree days (or every day); each stage over its rows' 0.1–99.9 % range (adults 163–2,180 degree days, days 139–252): 0 before, held after until fall freezes end the season (the shared D36 freeze factor). The larval spline started above 0 and dipped before rising (0.13 at 180 degree days, −0.08 at 300), which would read as larvae before eggs; before each curve's first rise it's held at its low (`cv/30_export.py`).
- **Counts:** exp(fit) − 1, a typical count in the data's units: a geometric-type mean, below fields' average counts.
- **Risk:** adults and larvae together, its count over its curve's peak (11.37 per 25 sweeps at 1,330 degree days), with the D36 thresholds. The other three curves are outputs with weight 0.
- **"Egg hatch" is gone:** 0.2's 374 degree days was a 0.003 dip in a flat curve, not a feature of the data. The larval rise, where the larval curve passes 0.1 (about 0.1 larvae per 25 sweeps), replaces it: 402 degree days.
- **The partial second generation** (0.2's 1,983) sits at the end of the data, past the adults' 99.9 % range, and isn't read.

## Checks

### Against the refit's own events

`packages/agmodels/tests/test_colorado_potato_beetle.py`, run in CI: the events found on the curves the model reads, against the refit's own (`cv/out/cpb-mean/full-fit-events.csv`): every degree-day event within 10 degree days, every calendar event within a day.

| Curve | Event | Degree days | Calendar | Typical date |
| --- | --- | --- | --- | --- |
| Adults | Colonization | 203 | 142 | May 22 |
| Adults | Overwintered adults' peak | 558 | 169 | June 18 |
| Adults | Low between generations | 907 | 189 | July 8 |
| Adults | First-generation adults' peak | 1,451 | 217 | August 5 |
| Egg masses | First eggs | 217 | 146 | May 26 |
| Egg masses | Peak | 530 | 168 | June 17 |
| Larvae | Rise (passes 0.1) | 402 | 158 | June 7 |
| Larvae | Peak | 734 | 183 | July 2 |
| Adults and larvae | Colonization | 205 | 143 | May 23 |
| Adults and larvae | First peak | 734 | 183 | July 2 |
| Adults and larvae | Low | 975 | 195 | July 14 |
| Adults and larvae | Second peak | 1,326 | 209 | July 28 |

The curves also have smaller features the tests hold: a larval shoulder at 940, and a second rise of egg masses from 1,860 (day 204), the first-generation adults' eggs.

### Leaving each year out

Each stage's GAM refitted with each of the 12 years left out, and with each of the 69 farms left out, on the archive's degree days at bases 32 to 58 °F, gridMET's 52 °F and the calendar (`cv/out/cpb-mean/`).

How far the events move (12 fits without a year; without a farm they move less): colonization 196–220 degree days and days 142–144; the overwintered adults' peak 542–570 and days 168–169; the larval peak 722–743 and days 181–184; the first-generation adults' peak 1,428–1,474 and days 216–218.

Counts out of sample, the root mean square error of log(count + 1) for a held-out year (no curve, the training mean: adults and larvae 1.01): adults and larvae 0.816 on 52 °F, 0.814 on the calendar, 0.796 on 32 °F; adults 0.692, 0.688 and 0.677; larvae 0.886, 0.887 and 0.868; egg masses 0.621 on each. Most of what's left is field to field.

Timing a held-out year's events, the root mean square error in days of each clock's date for the event against the year's own (11 or 12 years): on 52 °F, 3.6 to 10.2 days across the twelve events; on the calendar, 3.2 to 8.0 days. The calendar was ahead on colonization (4.2 against 7.2 days), first eggs (4.2 against 6.6) and the first-generation adults' peak (4.3 against 6.8), and level on the rest. Each field's own first adult, first egg mass and first larva, by the same clocks: 13.4, 11.8 and 9.8 days on 52 °F against 11.2, 10.1 and 9.3 on the calendar.

Why: the beetle's dates moved little between years here (colonization within about a week), while degree days would move them about 5 days either way; and the fields are close together (they reach colonization's total within a day or two of each other in a year), so the data can't show the north–south shift that degree days are for. A base of 32 °F did slightly better than 52 °F on counts (up to 2.5 %) and timing; not enough, on these data, to change the base the beetle's development is known to have.

### Against the Crop Risk Tool on the same weather

The same test file, on the tool's 2025 weather for Eau Claire, Wisconsin (`crt_daily_eau_claire_2025.csv`). The tool's step dates (its rounded numbers from the first analysis, on 50/86 °F) against the date our total (52/86 °F) reaches the refit's event:

| Event | The tool | Ours | Days later |
| --- | --- | --- | --- |
| Colonization | May 12 | May 15 | 3 |
| Larval rise (the tool's "egg hatch") | May 30 | June 8 | 9 |
| Overwintered adults' peak (the tool's "first-generation adult peak") | June 17 | June 20 | 3 |
| Larval peak | June 24 | June 28 | 4 |
| First-generation adults' peak (the tool's "second-generation") | July 25 | August 2 | 8 |

The tool is the system this model replaces, a reference rather than the truth (D54). At Eau Claire in 2025 the risk was Very high on 47 days, June 22 to August 7, by degree days (54 days by the calendar): adults and larvae stay near their peak from the first-generation larvae through the first-generation adults (the low between them is 87 % of the peak).

## Limits and open questions

- **Central Wisconsin's commercial fields only** (the training area: the 12 counties with 10 or more scouted fields). These fields are treated with a neonicotinoid at planting and sprayed for the beetle, so the counts are of managed fields, not untreated populations (Ben, 2026-11-21). Elsewhere, and in tomato and eggplant, the model runs with a warning.
- **Latitude untested:** degree days should carry the timing north and south better than the calendar, but these data can't show it. A check needs counts from other regions (northern Wisconsin's seed potatoes, Minnesota, Michigan).
- **Years differ in size, not much in timing:** fits by year show the same shape each year, with the earliest years' counts well below later years'.
- **The count rule** averages hot-spot and edge counts with the field's, which is what the scouts saw across the field but not an area-weighted mean.
- Degree days from January 1 for every field, whatever its planting date.
- **Cheapest independent comparison:** the 2026 season's scouting counts against the curves.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_colorado_potato_beetle.py
# the refit (anonymized working data from cv/00_prepare.R; weather from cv/wx_dd.py):
cd tmp/R/cpb && COUNT_RULE=mean OPENBLAS_NUM_THREADS=1 Rscript cv/10_cpb_cv.R && cd ../../.. && uv run python tmp/R/cpb/cv/30_export.py
```
