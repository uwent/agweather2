# Late blight disease severity values (`late-blight-dsv`): validation

Model version 0.3, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/late_blight.py`, reading the daily features `hours_rh_over_90_from_6pm` and `temperature_mean_rh_over_90_from_6pm` (`agmodels.features`); its page: `late_blight.md` beside it. The notes this condenses are PLAN.md Phase 3 D (step 1, "Late blight DSV"), D50, D74 and Phase 5's Veg Path check.

**In short:** a port of the Crop Risk Tool's late blight model (Wallin's DSV table as BLITECAST uses it, with the tool's risk levels). From the tool's own inputs, v2 reproduces its daily DSVs, totals and risk exactly; v2's one intended change (humid hours and their temperature from the same day from 6 pm) moves 31 days of the tool's 2025 test year and not the date the 18-DSV threshold is reached. Against the old AgWeather API at UW Vegetable Pathology's 7 forecast locations, v2's season totals run higher, by design (gridded RH counted from 88 %, D50). The DSV table hasn't been checked in a test against Wallin's or Krause et al.'s own publications, and the model hasn't been compared with late blight outbreaks in Wisconsin.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Wallin 1962 (American Potato Journal 39) | Disease severity values (0–4) from hours of RH ≥ 90 % and their mean temperature, three temperature bands | The table, as the Crop Risk Tool and the old API carry it (not checked against the paper this round) |
| Krause, Massie and Hyre 1975 (BLITECAST, Plant Disease Reporter 59) | The computerized forecast built on Wallin's values, with spray recommendations from season and recent totals | The method's name and the season and recent totals |
| UC IPM's potato late blight page | Wallin's table in °F and °C | The table the old API's code cites |
| The Crop Risk Tool (`calc_late_blight_dsv`, `risk_for_late_blight`; `tmp/shiny/crop-risk-tool`) | The table in code, the 14-day and season totals, and five risk levels (18 season DSVs as the first-spray threshold) | The table, totals and risk levels; parity tests below |
| VDIFN (`../ag-vdifn/app/models/diseases/late_blight.rb`) | Its own risk levels (Medium from 3 DSVs in the selected window or 30 in the season; a freeze ends the season) | Compared only |
| Old AgWeather API (`../ag-weather/app/models/pest_models.rb`) | The same table over the calendar day; 0 for a day without data | Compared on the same places (below) |

## Choices and differences

- **Table:** 0 below 7.2 °C and above 26.6 °C; 7.2–11.6 °C: 1 DSV from 16 humid hours, 2 from 19, 3 from 22; to 15.0 °C: 1 from 13 hours up to 4 from 22; to 26.6 °C: 1 from 10 up to 4 from 19. The old API's bands are half-open (7.2 to under 11.6 °C, and so on), the tool's and ours closed at the top: they differ only at exactly 11.6, 15.0 and 26.6 °C.
- **The day:** humid hours and their mean temperature both from the day from 6 pm the evening before (readings 19:00–18:00 CST, D74), so an overnight wet period counts whole and each hour is paired with its own temperature, as Wallin pairs them. The tool counts humid hours over the calendar day and averages their temperature over the day from 8 pm; the old API used the calendar day for both.
- **Humidity threshold:** gridded RH ≥ 88 % is counted as a station's 90 % (D50: against 80 Wisconet stations, May–September 2025–2026, the archive's RH ≥ 88 % gives as many hours as the stations' RH ≥ 90 % and their leaf-wet hours; `docs/validation/weather/humidity.md`). On the archive at Eau Claire, May 15–September 30, 2025, this raised the season's DSVs from 100 to 133 (PLAN.md, Phase 4's humidity note). Hours from station data sent to the API count at 90 %.
- **Risk:** the tool's levels, from the biofix (crop emergence, from `potato-stages` when a planting date is given, else May 15, or the last fungicide spray): Very high with 21 or more DSVs in the last 14 days once the season total reaches 30; High with 14 or more once it reaches 18; Moderate at a season total of 18 (the usual first-spray threshold); Low with any DSV in the last 14 days. VDIFN's levels differ (High and Very high only after 30 season DSVs, Moderate from 3 recent DSVs) and drop to 0 after a freeze; v2 shows the model May 1 to September 30 and does not end the season at a freeze.
- **Missing data:** a day without its inputs has no DSV (the old API scored it 0); totals sum the days that have one.

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_late_blight.py`, run in CI, on the tool's fixtures (`packages/agmodels/tests/fixtures/crt_*.csv`, written by `make_crt_fixtures.R` from the tool's R code and its recorded 2025 weather at one grid cell near Eau Claire, Wisconsin, 44.815 °N 91.530 °W):

- **The table:** all 4,025 combinations of mean temperature (−2 to 30 °C by 0.2) and humid hours (0 to 24) give the tool's DSV exactly.
- **A season from the tool's inputs:** with the tool's own pairing of hours and temperature, the daily DSVs, the season and 14-day totals and the risk level match the tool's on all 365 days of 2025.
- **The pairing change, measured:** from the tool's hourly weather, with the threshold held at 90 % to isolate it, taking hours and temperature from the same day from 6 pm changes 31 daily values; May 15 to September 30 sums 55 DSVs against the tool's 47, and both reach the 18-DSV spray threshold on July 16 (the date from PLAN.md Phase 3 D; with the earlier day from 8 pm, 27 days differed and the sum was 53).
- Missing inputs give no DSV and no humid hours give 0; the risk starts at the biofix and skips missing days; grid-shaped inputs work.

The tool is the model v2 replaces: this shows the port is faithful where intended, not that the tool is right (D54).

### Against the old AgWeather service

`docs/validation/legacy/vegpath.md`, from `scripts/compare_vegpath.py --end 2026-09-30` (not in CI; needs the live old API, cached in `tmp/v1-cache`): the old API's `vegpath` query at UW Vegetable Pathology's 7 forecast locations (Spring Green, Arlington, Grand Marsh, Hancock, Plover, Antigo, Rhinelander), May 1 to September 30, 2026, against v2's model run at the same points. Totals count from May 1, as the old API's do.

| Place | Old API | v2 | v2 at 90 % |
| --- | --- | --- | --- |
| Spring Green | 88 | 121 | 99 |
| Arlington | 60 | 80 | 63 |
| Grand Marsh | 76 | 99 | 81 |
| Hancock | 59 | 85 | 65 |
| Plover | 55 | 80 | 66 |
| Antigo | 64 | 88 | 70 |
| Rhinelander | 53 | 73 | 63 |

- v2's season totals are 30 to 45 percent above the old API's (computed from the table); with the threshold back at 90 %, 5 to 20 percent above.
- Over 1,071 point-days with both: the same daily DSV on 78 % of days (83 % at 90 %); the mean difference +0.16 DSV a day (+0.05 at 90 %).
- The 88 % threshold accounts for about two thirds of the difference; the rest is the day from 6 pm (the old API: the calendar day) and the weather itself (v2's URMA against the old API's RTMA). PLAN.md's Phase 5 note gives 27–51 % and 3–19 % for the same comparison, from an earlier run; the table above is the current one.

The old API is a reference, not the truth (D54): this explains the difference Veg Path's readers will see, not which is more accurate.

## Limits and open questions

- **No field comparison:** the model hasn't been compared with late blight outbreaks or first-detection dates in Wisconsin, and its spray thresholds (18 season DSVs; the 14-day levels) come from the tool, not from a validation in this round.
- **The table against its sources:** Wallin 1962 and Krause et al. 1975 aren't in `tmp/references/`; the table matches the tool's and the old API's, but no test reads it from the papers.
- **RH ≥ 90 % as leaf wetness:** humid hours stand in for wet hours; the D50 shift was fitted on station RH and leaf wetness counts, not on disease. Irrigated fields stay wetter than the grid shows.
- **A single humid count a day:** Wallin's values come from continuous humid periods; v2 counts all humid hours in the day from 6 pm, so two short periods count as one long one (as the tool and old API do).
- **Cheapest independent comparison:** UW Vegetable Pathology's records of first late blight detections in Wisconsin (USAblight, which mapped confirmed reports by county, went offline by 2026; its successor is PlantAid, plant-aid.org) against the date each location's season total reached 18 DSVs and its risk level in the weeks before; then NEWA's late blight model, if it runs one on the same hours.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_late_blight.py
uv run python scripts/compare_vegpath.py --end 2026-09-30   # needs the archive in data/ and the old API (or tmp/v1-cache)
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's fixtures; needs tmp/shiny/crop-risk-tool
```
