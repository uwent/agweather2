# Fire blight (`fire-blight`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/fire_blight.py`, with its daily features in `agmodels.features.fire_blight_features` (Cougarblight's hourly values summed, degree hours above 65 °F, hours estimated wet; D96); its page: `fire_blight.md` beside it. The research notes this condenses are in the project's working notes, `docs/plans/models.md` part B3 (its notes, "Sources read" rounds 1–3, round 2's answers 2 and 3) and B5 (NEWA's logic reproduced, Jones 1992).

**In short:** MaryBlyt's infection potential reproduces the published program's own worked examples exactly; NEWA's fire blight page is reproduced to the unit on four page exports, and on the hours of 34 Wisconsin orchard stations our Cougarblight level agrees with NEWA's on 95 % of bloom days and our MaryBlyt infection days match NEWA's within a day on 130 of 146. On the archive's weather at the same places the level agrees on 89 % of days, with Cougarblight's totals running well above the stations' at a quarter of the station-seasons (an open finding). Neither model has been tested against fire blight in Wisconsin orchards: the only field evaluation near Wisconsin is of an early MaryBlyt in Michigan.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Smith and Pusey 2011, Acta Horticulturae 896:331–336 ([doi:10.17660/ActaHortic.2011.896.45](https://doi.org/10.17660/ActaHortic.2011.896.45)) | Cougarblight 2010: hourly temperature risk values from the growth of *E. amylovora* on crab apple stigmas, from just above 10 °C (50 °F) to 0 from 35.5 °C, no negatives; the total over the last four days (a blossom's susceptible life); three orchard-history scenarios at five levels (High from 500, 200 and 100); wetting of two hours or more as the infection event. Thresholds "derived empirically" from outbreaks, mostly in the Pacific Northwest, with Utah, California, Michigan, New York and Canada; no quantitative validation | The hourly values from 51 °F and the four-day total; wetting of two hours as its own output |
| WSU's Cougarblight spreadsheets (2019 hourly version 8, 2010 EZ) and the Decision Aid System ([WSU Tree Fruit](https://treefruit.wsu.edu/crop-protection/disease-management/fire-blight/cougar-blight-model/)) | The hourly table in °F: 0.05 at 51 °F, 4 at 70, 30 at 80, 52 at 88–89, 10 at 95, 0 at 96–100, negative from 101; DAS's three levels (High from 400, 150 or 80; Extreme from 800, 350 or 200); wetting as two hours of RH above 80 % or wet, or 0.01 in of rain | The °F table, which is NEWA's too (`COUGARBLIGHT_F`), without the negative values above 100 °F (the paper has none) |
| Steiner 1990, Acta Horticulturae 273:139–148 ([doi:10.17660/ActaHortic.1990.273.18](https://doi.org/10.17660/ActaHortic.1990.273.18)) | MaryBlyt's four conditions (open blossoms; 110 degree hours above 18.3 °C, which is 198 °F·h; rain of 0.25 mm, dew, or 2.5 mm the day before; a mean of 15.6 °C); the cool-day cuts; symptoms 50 DD°C above 12.7 °C after infection (simple average); daily data only, degree hours estimated from the high and low | The index (EIP = 100 at 198 °F·h) and its conditions, as the current program runs them |
| Turechek and Biggs 2015, Plant Health Progress 16:16–22 ([doi:10.1094/PHP-RS-14-0046](https://doi.org/10.1094/PHP-RS-14-0046)) | MaryBlyt 7.1: daily degree hours = 24 × the day's single-sine degree days above 65 °F; the 80 DD40 blossom window (sine, 90 °F cutoff); cuts of a third, a half and all after one, two and three cool days while the total is under 400 °F·h; a freeze clears the total; at or below 24 °F the window restarts; symptoms 103 DD55 by the sine after infection; Table 1's three demonstration seasons | The current rules, with degree hours summed from the hours themselves; Table 1 as a test |
| Biggs and Turechek 2018, MaryBlyt 7.1.1 user manual ([PDF](https://grapepathology.org/wp-content/uploads/2018/12/Maryblyt-7.1.1-Manual-12142018.pdf)) | The conditions in order, the cuts and their 400 °F·h stop, the risk table (Low with blossoms alone, Moderate, High, Infection with all four), symptoms after 103 DD55 | The risk count and its labels |
| Jones 1992, Plant Disease 76:344–347 ([doi:10.1094/PD-76-0344](https://doi.org/10.1094/PD-76-0344)) | MaryBlyt 3.0 in 11 Michigan orchard-years, 1983–1991 | Evidence of the model's limits (below) |
| NEWA's fire blight model ([newa.cornell.edu](https://newa.cornell.edu/fire-blight)) | First blossom at 230 DD43 (single sine from January 1) and petal fall at 578 or June 15, or the grower's dates; Cougarblight from the 2010 °F table, counting no hour below 60 °F; three history levels (High from 300, 150 or 80; Extreme from 800, 350 or 200; default "in the neighborhood last year"), no wetting condition; MaryBlyt's EIP from hourly degree hours over an 80 DD40 window (simple average); wetting as rain, a wet leaf wetness hour, a dew point within 3 °F, or over 0.1 in the day before | The bloom window, Cougarblight's thresholds, labels and default (D95); compared on the same weather (below) |
| Enviroweather (MSU) ([fire blight](https://enviroweather.msu.edu/crops/apple/fireblight)) | MaryBlyt only, from its pink to first cover stages; EIP = degree hours / 1.95; wetting by rain or the user's dew, fog or spray entry; symptoms after 103 DD55 | Compared only: its divisor is 195 °F·h, not the 198 of Steiner's 110 °C·h |

## Choices and differences

- **Bloom:** NEWA's, from first blossom at 230 DD43 (single sine from January 1) to petal fall at 578 DD43 or June 15, whichever comes first; given a grower's first blossom date, petal fall is 348 DD43 later or June 15. Steiner's full pink comes at roughly 250–260 DD43 in Maryland (by our conversion of his timing from green tip), so NEWA's start is a few days earlier, which costs little since early cool days are cut. Both models show values only in bloom; NEWA computes Cougarblight's total all season and EIP from the day after first blossom to October, and hides them outside bloom.
- **Cougarblight's floor:** hours from 51 °F count (0.05 at 51 to 0.44 at 59), as the 2010 paper's values do; NEWA counts no hour below 60 °F, the pre-2010 model's floor (D95 lets the newer published source win; Ben, 2026-11-17). On the same hours this puts our four-day totals a median of 8 above NEWA's (below), which changes the level only on days near a threshold.
- **Cougarblight's thresholds:** NEWA's three levels and its default history (Low; High from 150; Extreme from 350, with blight in the neighborhood last year), so Wisconsin growers see NEWA's levels. Where High starts with no blight nearby differs between sources: 300 at NEWA, 400 in WSU's Decision Aid System, 500 in the paper (whose five levels put "Caution" from 150).
- **Wetting:** rain of 0.01 in or more in the day, or two or more hours estimated wet (RH at or above 90 % or rain), Smith and Pusey's two hours with the estimate apple scab uses (chosen against NEWA's leaf wetness sensors: [../weather/leaf-wetness.md](../weather/leaf-wetness.md)). Cougarblight's "infection possible" (wet while High or Extreme) is a separate output, not a condition on the level; NEWA has neither. MaryBlyt's wetting also counts 0.10 in of rain the day before. NEWA's MaryBlyt wetting counts any hour its leaf wetness sensor reads wet or the dew point within 3 °F, which no gridded data can give.
- **MaryBlyt's rules:** version 7.1's, where NEWA differs: the window's degree days above 40 °F by the sine with a 90 °F cutoff (NEWA: the simple average); a cool day is a high under 65 °F (NEWA: at or under 65); freezes at or below 32 °F and 24 °F (NEWA: under 33 and under 24); EIP at or above 100 (NEWA: over 100); 0.10 in or more the day before (NEWA: over 0.1). Degree hours are summed hour by hour, as NEWA does; the program estimates them from the day's high and low (24 × the sine's degree days above 65 °F), and Steiner 1990 from 6 hours at the low, 6 at the high and 12 at the mean.
- **Symptoms:** expected 103 DD55 by the sine with a 90 °F cutoff after a MaryBlyt Infection day, the program's interval since version 4.2. Steiner 1990's 50 DD°C above 12.7 °C (90 DD°F) belongs with the simple average method; NEWA uses 90 with the sine, which mixes the two.
- **Degree days:** the exact single sine. NEWA's sine runs 1–2 DD43 from it by mid-May at Gays Mills in 2025, enough to move first blossom by a day.
- **Days:** midnight to midnight CST (D74); NEWA's on the local clock, an hour later in daylight time.
- **Not modelled:** trauma blight (hail, a storm), canker and shoot blight, and sprays (NEWA's and MaryBlyt's streptomycin restart).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_fire_blight.py`, run in CI:

- **MaryBlyt 7.1's worked examples:** Turechek and Biggs 2015's Table 1 gives the program's cumulative degree hours above 65 °F day by day in three demonstration seasons (9, 12 and 17 days, with cool days, freezes and the window sliding). Fed the program's daily degree hours (24 × the whole sine degree days above 65 °F), our EIP reproduces all 38 totals exactly (within 1 °F·h): the CI test compares the 37 that fall before petal fall by NEWA's 348 DD43 from the first day, and the 38th, the third season's last day, matches too with the window held open. The same rules match all 10 window starts of the paper's Table 2 (`tmp/references/apple/notes/maryblyt-check/`, not in the repository).
- Cougarblight's hourly values at 50, 51, 60, 70, 80, 88.6, 95, 96 and 101 °F against the table, and its levels at each threshold for the three histories.
- Bloom from 230 DD43 to petal fall at 578 or June 15; Cougarblight's four days and "infection possible"; a MaryBlyt Infection day and the symptom degree days after it, on made-up seasons.

### Against NEWA on the same weather

**NEWA's rules reproduced.** `scripts/newa_reference.py` recomputes NEWA's fire blight page from its published rules on NEWA's own station hours. Ben exported the page's Results and Wetness Events tables for Gays Mills 2025, Brighton 2025, Eau Claire 2024 and Baileys Harbor 2025 (`newa_reference.py check`): all 1,209 daily rows of each table match with no difference, including first blossom (Gays Mills and Brighton April 22, Eau Claire April 23, Baileys Harbor May 16), Cougarblight's four-day total and MaryBlyt's EIP to the unit. The reference then stands in for NEWA at every station-season we have hours for. NEWA's results are published here with credit, as factual results on public station data; NEWA's code and the raw station hours stay out of the repository.

**Ours against NEWA.** `scripts/check_fire_blight.py`; full table in [fire-blight/newa.md](fire-blight/newa.md). The hours of 34 Wisconsin NEWA orchard stations, 2024 and 2025 (67 station-seasons), compared on NEWA's bloom days. Ours run on the station's own hours (the method) and on the archive's hours at the station's cell (the map). The totals leave out 4 station-seasons whose rain gauge caught under 40 % of the archive's April–June rain.

| On NEWA's bloom days | Station hours | Archive at the station's cell |
| --- | --- | --- |
| Cougarblight on NEWA's level (blight nearby last year) | 1,625 of 1,708 days (95 %) | 1,448 of 1,636 days (89 %) |
| Cougarblight's four-day total, ours − NEWA's: median of the seasons' medians (10th–90th percentile) | +8 (+7 to +10) | +16 (−10 to +48) |
| EIP, median absolute difference | 0 | 5 |
| NEWA's 146 MaryBlyt Infection days matched by ours within a day | 130 | 118 |
| Our Infection days not in NEWA's | 4 | 14 |
| First blossom, ours − NEWA's (67 seasons) | 55 the same day, 10 the next, 2 two days later | 28 the same day, 57 within 2 days, −5 to +5 |

- On the station's hours, Cougarblight's totals run 5 to 13 above NEWA's in every season: our hours from 51 to 59 °F, which NEWA doesn't count. EIP's median difference is 0. First blossom is NEWA's day or a day later; the two seasons two days later (Malone 2025, Mequon 2024) are ones where NEWA reached 230 DD43 by less than a degree day before days that added 0–5.
- Infection days on the station's hours differ by the wetting rule (NEWA counts a wet hour on its leaf wetness sensor or a dew point within 3 °F; ours two hours estimated from RH) and MaryBlyt 7.1's boundaries (above); the 16 unmatched days haven't been sorted by cause.
- On the archive's hours the level still agrees on 89 % of days, but Cougarblight's totals run at least 30 above the stations' in 17 of the 67 seasons (the largest +86 at Gays Mills in 2025) and at least 20 below in 5 (the lowest −61 at Plymouth in 2024). Cougarblight's hourly values climb about 2.6 for each °F between 70 and 80 °F, so a degree or two in the afternoon hours moves a four-day total by tens (see the open finding below).

### Field evidence from Michigan

Jones 1992 (Plant Disease 76:344–347) is the only field evaluation of MaryBlyt near Wisconsin in our sources, and we found none of Cougarblight in the Midwest; neither model has been tested against fire blight in Wisconsin orchards. It tested MaryBlyt version 3.0 on daily weather from sensors in each orchard, in 11 Michigan orchard-years (1983, 1984, 1990 and 1991), against epiphytic bacteria on the blossoms and blight strikes after petal fall. Version 3.0 predates the 80 DD40 window, the hourly degree hours and the 103 DD55 symptom rule, so this is evidence for the method, not a test of our version.

- Jones reports blight appearing 1 to 2 days after the predicted symptom dates, in 1984, 1990 (trauma blight) and both 1991 orchards: "more accurate in predicting the appearance of symptoms than in predicting infection periods".
- Infection predictions were less accurate: by our count of Jones's Table 1, 3 hits (one light), 2 false alarms, 3 orchards with trace blight and no warning, 2 correct negatives, and a trauma blight event explained. Jones gives no hit rate, and 11 orchard-years are too few for one.
- In 1983 bacteria were found on blossoms in every orchard with EIP at 12 to 59, so an EIP under 100 doesn't mean no bacteria are present.
- The worst epidemic (southwest Michigan, May 1991) came on days above 26.6 °C with morning fog and no rain; the model caught it only when fog was entered as rain. Our wetting estimate counts humid hours as wet, which is meant to catch such mornings, but a fog morning may still be missed.
- Severe blight followed late blossoms at petal fall in 1991, and Jones recommended keeping blossoms at risk past petal fall.

## Limits and open questions

- **No Wisconsin validation of infections.** Neither model has been checked against fire blight observed in Wisconsin orchards; the agreement above is with NEWA, which runs the same models. Cougarblight's thresholds come from outbreaks studied mostly in the Pacific Northwest and MaryBlyt's from Maryland and West Virginia; Smith and Pusey give no validation counts, and MaryBlyt 7.1's only test is against its own earlier version.
- **The archive's Cougarblight totals at some stations** run 30–50 above the stations' (more at Gays Mills, Richland Center, Galesville and Trempealeau in 2025; below them at Plymouth and Belmont). The likely cause is the archive's spring afternoon temperatures differing from the orchards' sensors; this hasn't been checked hour by hour yet (the comparison `docs/validation/weather/humidity.md` made for RH, done for temperature at those cells). Until then a map's Cougarblight level can read a level higher than a nearby orchard station on warm days.
- **Late bloom:** the window ends at petal fall (578 DD43 or June 15); late and straggling blossoms stay at risk after it, as Jones found. The model page says so; a grower's own first blossom date moves the window at a point.
- **Wetting is estimated,** not measured: the estimate agrees with orchards' leaf wetness sensors on about two in three scab infection events, and on fire blight wetting days less well (κ 0.58 in spring; [../weather/leaf-wetness.md](../weather/leaf-wetness.md)). Wetting is shown so a grower can judge a fog or dew morning.
- **Not modelled:** trauma blight after hail or storms, canker and shoot blight, and sprays.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_fire_blight.py
uv run python scripts/fetch_newa.py                 # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/newa_reference.py check       # NEWA's rules against Ben's page exports in tmp/newa/fire-blight/ (not in the repository)
uv run python scripts/check_fire_blight.py          # needs the archive in data/ and the station hours
```
