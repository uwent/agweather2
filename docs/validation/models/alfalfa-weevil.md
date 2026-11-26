# Alfalfa weevil (`alfalfa-weevil`): validation

Model version 0.2, written 2026-11-21 (D98; part H4 of `docs/plans/models.md`). The model: `packages/agmodels/src/agmodels/insects/alfalfa_weevil.py`, run by the insect engine (`agmodels.phenology`, D36, D37); its page: `alfalfa_weevil.md` beside it. Version 0.1 was the Crop Risk Tool's step table (single sine 48.2/86 °F from January 1: 300, 370, 440, 505, 595, 815, 1000), reported in this file's history.

**In short:** rebuilt on NEWA's model (D95): the simple average above 48 °F from January 1, and NEWA's degree days for each stage, which are Harcourt 1981's (°C·d × 1.8). The curves pass half of egg hatch, cocooning and adult emergence at NEWA's 280, 600 and 815, and on the Wisconsin NEWA stations' own weather they reach them on NEWA's days in every station-year. On Open-Meteo's historical weather for Harcourt's Ontario study area, NEWA's rule reaches his 36 dated peaks a median 3 days late, a day later than Harcourt's own method. Nothing has been compared with weevil counts in Wisconsin; on the normals the model puts larval feeding's peak (early June at Arlington) before UW–Madison's "heaviest feeding at 600–800 degree days".

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA's alfalfa weevil model (newa.cornell.edu/alfalfa-weevil, read 2026-11-21; methods and constants only) | Simple average, base 48 °F, no upper, from January 1, no reset. "Degree days for peak (50%) occurrence" (credited to R. I. Carruthers, uncited): egg hatch 280, instar 1 315, instar 2 395, instar 3 470, instar 4 550, cocooning 600, pupa 725, adult emergence 815. Guide: 280–314 eggs hatching; 315–599 larvae present, scout; 600–725 cocooning and pupating, feeding stopped. Cites Harcourt 1981 | The method, and the 50 % points of egg hatch (280), cocooning (600) and adult emergence (815) |
| Harcourt 1981 ([doi:10.4039/Ent113601-7](https://doi.org/10.4039/Ent113601-7); Bay of Quinte and Guelph, Ontario; development 1973–1976, validation 1977–1980; read in full, every number here confirmed against the paper 2026-11-23) | Single sine (Baskerville and Emin 1969) above 9 °C from April 1, on air temperatures at Smithfield Experimental Farm and Guelph; stage requirements averaged from Guppy and Mukerji 1974's logistic curves over 9–21 °C; peaks hatch 155, instar 1 176, instar 2 218, instar 3 260, instar 4 306, cocooning 335, pupa 403, adult emergence 454 °C·d (Table II); stage durations instar 1 42, instar 2 42, instar 3 46, instar 4 58, prepupa 39, pupa 80 °C·d; probit of % hatch = −1.3371 + 0.0086 × °C·d (Fig. 1, n = 30, r² 0.77); observed peak dates of the eight stages in 1977–1980 (Table II) and of hatch at both sites (Table I); "most of the feeding damage occurs between 260 and 335 °C·d after April 1" | The stage durations (cocoon 39 + 80 = 119 °C·d = 214 °F·d); the hatch spread's scale; the dated peaks as a check |
| Litsinger and Apple 1973 ([doi:10.1093/jee/66.2.309](https://doi.org/10.1093/jee/66.2.309); Arlington, Wisconsin, 1971; read in full, numbers confirmed 2026-11-23) | Base 50 °F for eggs, 48 °F for larvae; eggs need 176 and 205 thermal units above 50 °F to first and 50 % hatch at six constant temperatures, 168 and 189 outdoors at Arlington (counted from laying, not January 1); thermal units above 48 °F (Arnold's max–min method) from eclosion to 50 % of instars 2, 3, 4 and the prepupa: 70.6, 140.6, 207.0, 297.9 (Table 3); the 4th stadium is the longest (90.9) and does the most damage | A check on the larval period (298 against NEWA's 320) |
| The Crop Risk Tool (version 0.1's source) | The step table above | Compared only (the old table on the normals and NEWA's stations) |
| UW–Madison (Bick 2025; Jensen 2018; A3646 2025) | DD48 from January 1: egg hatch and tip feeding begin at about 300, heaviest feeding 600–800; peak larval feeding mid-May to early June, dropping off by mid-June; scouting and thresholds | Compared; the page's scouting advice |
| Enviroweather (MSU) | Single sine base 48 °F, no upper, from January 1: light feeding 300, major feeding 439, pupation 596, end of pupation and feeding 820; an observed date resets the later stages | Not used (D95) |

## Choices and differences

- **Method (D37, D95):** NEWA's simple average, base 48 °F, no upper threshold, from January 1 (a stored total, `average_48`). Harcourt's numbers are single sine above 9 °C counted from April 1; NEWA runs them on its own method from January 1, and we follow NEWA. The difference on Harcourt's own dates is about a day (below). Litsinger and Apple's eggs develop above 50 °F; like NEWA, one base for every stage.
- **Egg hatch:** a PERT (0, 280, 560), symmetric about NEWA's 280, weight 0 (hatch isn't damage). Its spread is our choice: the widest symmetric curve that starts no earlier than January 1 (10 and 90 % at 138 and 421; SD 106 °F·d). Harcourt's pooled probit implies an SD of 116 °C·d (209 °F·d), twice that, with its lower tail before April 1; it pools sites and years and so overstates the spread within one field. No source gives the within-field spread.
- **Larval feeding (the risk, weight 1):** a derived stage from each egg's hatch for 320 °F·d, NEWA's hatch (280) to cocooning (600). Harcourt's four instars sum to 188 °C·d (338 °F·d) and Litsinger and Apple's to 297.9 TU; NEWA's 320 is between. The most larvae are present at 439 °F·d, between NEWA's instar 2 (395) and instar 3 (470) peaks; feeding by weight is heaviest in the 4th instar (Litsinger and Apple), so damage peaks somewhat after the risk curve does.
- **Pupae in cocoons** (weight 0): derived, from 320 for 215 °F·d (NEWA's 600 to 815; Harcourt's prepupa and pupa, 214 °F·d). **New adults** (weight 0): derived, from 535 for 185 °F·d (the Crop Risk Tool's adult diapause at 1,000; no published source for when summer adults leave the field).
- **Scouting window:** "Scout stem tips for larval feeding", egg hatch between 50 % and 99.9 % complete: 280 to 532 °F·d. Harcourt starts the warning system at peak hatch; NEWA's guide scouts from 315 (instar 1's peak) to 599 (cocooning). Ours opens about 2 days before NEWA's and closes about 4 days before it (at Arlington's normal rate in early June, about 17 °F·d a day). One window can follow only one stage, and a window on the larvae themselves would open only once the first had finished feeding.
- **One generation;** the end-of-season freeze rule never matters (the weevil is gone by August).
- **Against the Crop Risk Tool (0.1):** its sine 48.2/86 counts more in spring, so its steps (300, 595, 815) came 3–5 days before NEWA's 280, 600 and 815 on the NEWA stations (below).
- **Training area:** Harcourt's data, eastern Ontario 1973–1980, set as New York (`trained`), where NEWA runs the same numbers; a Wisconsin point gets the training-area warning. Litsinger and Apple's Wisconsin larvae are only a check on one duration.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 34, the first egg hatch (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 3 at Madison, April 8 at Hancock, April 21 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) March 30. Where we don't have the normals it opens on April 1. It ends after July 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_alfalfa_weevil.py`, run in CI:

- NEWA's table is Harcourt's peaks × 1.8 within 4 °F·d for all eight events (Harcourt's 155, 176, 218, 260, 306, 335, 403, 454 °C·d are 279, 317, 392, 468, 551, 603, 725, 817 °F·d).
- The curves pass half of egg hatch at 280, half of the larvae finished at 600 and half the adults out at 815, within 1 °F·d (NEWA's 280, 600, 815).
- The larval period (320) lies between Litsinger and Apple's 297.9 and Harcourt's 338; the cocoon period (215) is Harcourt's 214 within 2.
- Egg hatch 10 and 90 % at 138 and 421; its SD is half Harcourt's probit's.
- The most larvae are present between NEWA's instar 2 and instar 3 peaks (at 439); the window opens at 280 and closes at 532.
- The degree days are the simple average with no cap (a 70/100 °F day counts 37).

### Against Harcourt's dated peaks in Ontario

`scripts/check_alfalfa_weevil.py`, part 1; full table in [alfalfa-weevil/weather.md](alfalfa-weevil/weather.md). Harcourt's Table II gives the observed peak dates of eight stages in four years at the Bay of Quinte (32 dates) and Table I peak hatch at Guelph (4 more), 36 dated peaks in all. We ran both methods on Open-Meteo's historical daily max and min (ERA5) at the Smithfield farm and Guelph; Harcourt used station records, on which his own predictions fell within 2 days.

| Method                                                                | Median, days | Mean | Mean absolute | Range    |
| --------------------------------------------------------------------- | ------------ | ---- | ------------- | -------- |
| Harcourt's (single sine above 9 °C from April 1, his °C·d)            | +2           | +1.3 | 1.7           | −4 to +4 |
| NEWA's (simple average above 48 °F from January 1, NEWA's °F·d): ours | +3           | +2.9 | 3.0           | −2 to +8 |

- Both run a little late on this weather (ERA5 may run cool there in spring, which would delay both alike); NEWA's rule runs about a day and a half later than Harcourt's own on the same days, because the simple average counts less than the sine on cool spring days. That is the cost of following NEWA's method rather than the source's, and it is small next to the year-to-year spread.
- These are the dates the model's numbers were built to fit, in Ontario; they test the method change, not the numbers in Wisconsin.

### Against NEWA on the same weather

`scripts/check_alfalfa_weevil.py`, part 2; full table in [alfalfa-weevil/weather.md](alfalfa-weevil/weather.md). NEWA's rule (simple average above 48 °F from January 1 on the station's daily max and min, unrounded, a day without hours adding nothing; as read from its page, `tmp/references/insects/notes/newa-insects.md`) on the hours of Wisconsin's NEWA stations, 2024 and 2025 (67 station-years; 66 reaching adult emergence), against ours on the same days and on the archive at each station's cell.

| Ours − NEWA's, days                                 | Egg hatch (280)        | Cocooning (600)        | Adults (815)           |
| --------------------------------------------------- | ---------------------- | ---------------------- | ---------------------- |
| Ours, station days                                  | 0 in all 67            | 0 in all 67            | 0 in all 66            |
| Ours, archive: median (10th–90th percentile; range) | 0 (−2 to +2; −7 to +7) | 0 (−3 to +2; −5 to +5) | 0 (−3 to +2; −5 to +4) |
| The Crop Risk Tool's old table, station days        | −4 (−6 to −2)          | −5 (−6 to −3)          | −3 (−4 to −2)          |

On the same days ours is NEWA's (same method, same totals). The archive's differences are the grid's weather against the station's, not the model.

### Typical dates in Wisconsin

`scripts/check_alfalfa_weevil.py`, part 3: the day the 1996–2025 normal running total (each year's own from January 1, averaged; the same as `/api/v2/climate/normals?dd=average_48`, checked at Arlington) reaches each event.

| Event                                   | Degree days | Arlington | Hancock   | Rhinelander  |
| --------------------------------------- | ----------- | --------- | --------- | ------------ |
| 10 % of eggs hatched                    | 138         | May 6     | May 11    | May 19       |
| Half the eggs hatched; the window opens | 280         | May 22    | May 26    | Jun 2        |
| Most larvae feeding (the risk's peak)   | 439         | Jun 2     | Jun 6     | Jun 14       |
| The window closes                       | 532         | Jun 8     | Jun 12    | Jun 20       |
| Half the larvae cocooned                | 600         | Jun 11    | Jun 16    | Jun 24       |
| Half the adults out                     | 815         | Jun 22    | Jun 26    | Jul 5        |
| UW–Madison's heaviest feeding           | 600–800     | Jun 11–21 | Jun 16–25 | Jun 24–Jul 4 |
| Old table: egg hatch (sine 48.2/86)     | 300         | May 18    | May 22    | May 29       |

UW–Madison's own descriptions disagree with each other here: peak larval feeding "between mid-May and early June", dropping off by mid-June (A3646, Jensen 2018), and the heaviest feeding at 600–800 DD48, which is June 11–21 at Arlington on our method (a few days earlier on the sine method UW may mean). Our risk peak (June 2 at Arlington) fits the first; NEWA's numbers put 600–800 after feeding has largely stopped. Recent springs ran earlier than the normals: NEWA's egg hatch fell on May 12 and May 15 at Verona in 2024 and 2025.

## Limits and open questions

- **No Wisconsin field check.** No dated alfalfa weevil larval counts or tip-feeding records from Wisconsin were found; UW–Madison's 600–800 for the heaviest feeding doesn't fit NEWA's table (above), and which is right for Wisconsin needs field data. Wisconsin counts (UW, DATCP surveys, consultants) are the next step.
- **Hatch spread** is a choice (above); a wider or narrower spread moves the window's opening and the risk curve's width, not its middle.
- **The new adults' duration** (to 1,000) has no published source.
- **Uncited table:** NEWA credits R. I. Carruthers; its numbers are Harcourt's × 1.8. The training area is therefore Harcourt's (eastern Ontario), set as New York.
- **Western strain:** Minnesota reports a western strain developing 1–2 weeks later (Hanson and Potter 2023); degree-day models are for the eastern strain.
- **No observed reset:** Enviroweather lets a grower's observed date reset later stages; ours runs from January 1 only.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_alfalfa_weevil.py
uv run python scripts/fetch_newa.py              # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_alfalfa_weevil.py    # needs the archive in data/, the station hours, and Open-Meteo once
```
