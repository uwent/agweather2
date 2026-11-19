# Early blight P-days (`early-blight-pdays`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/early_blight.py`, reading the daily minimum and maximum air temperature; its page: `early_blight.md` beside it. The notes this condenses are PLAN.md Phase 3 D (step 1), Phase 5's Veg Path check and Phase 6's note on Veg Path's 2026 table.

**In short:** a port of the Crop Risk Tool's early blight model: potato physiological days (Sands, Hackett and Nix 1979) accumulated from emergence, with the tool's risk levels around Pscheidt and Stevenson's 300 P-day first-spray threshold. From the tool's own inputs, v2 reproduces its P-days and risk exactly when it weighs the last term as the tool does; v2's one intended change (the last term weighs the day's high, as Sands et al. write it) lowers the tool's 2025 test season by under 1 % and leaves the date 300 is reached unchanged. Whether Sands et al. weigh the high there is PLAN.md's reading; the paper isn't in `tmp/references/`, so this round didn't recheck it. Against the old AgWeather API at UW Vegetable Pathology's 7 forecast locations, v2's season totals are within 4 %. The model hasn't been compared with early blight onset in Wisconsin fields.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| Sands, Hackett and Nix 1979 (Field Crops Research 2) | Potato development rate P(T): 0 below 7 °C, 10 at 21 °C, 0 from 30 °C, two parabolas; a day's P-days from P at four temperatures between the low and the high, weighted 5, 8, 8 and 3 | The rate and the day's sum, with the last term at the high |
| Pscheidt and Stevenson 1986 (Plant Disease 70, 915–920) | Forecasting methods for early blight control compared in Wisconsin; first sprays at 300 P-days controlled the disease on cultivars of different maturity (as the 1988 paper summarizes it) | The first-spray threshold of 300 P-days |
| Pscheidt and Stevenson 1988 (American Potato Journal 65; in `tmp/references/diseases/`, read 2026-11-19) | The critical period for control on Russet Burbank, 1980–1984: it came after 400 P-days each year, with spores trapped and favorable weather; sprays could wait until 400 on that variety (about four fewer a year), and earlier varieties such as Superior need their own study | Background: why 400 isn't used for all varieties. UW Vegetable Pathology keeps 300 (its specialist, 2026-11-19, per Ben), and a student there is re-examining it |
| The Crop Risk Tool (`calc_pdays`, `risk_for_early_blight`) | The same P-days with P(Tmin) in the last term; risk from the total until 400, then from the 7-day mean | The risk levels; parity tests below |
| VDIFN (`../ag-vdifn/app/models/diseases/early_blight.rb`) | The same levels, with Very high above (not at) a 7-day mean of 9 | Compared only |
| Old AgWeather API (`../ag-weather/app/models/pest_models.rb`) | P-days with P(Tmin) in the last term; 0 for a day without data | Compared on the same places (below) |

## Choices and differences

- **The last term:** P-days = (5 P(Tmin) + 8 P((2 Tmin + Tmax)/3) + 8 P((Tmin + 2 Tmax)/3) + 3 P(Tmax)) / 24, as Sands et al. write it. The tool and the old API weigh P(Tmin) in the last term; `pdays(..., last_term="tmin")` reproduces them for the parity tests. Which is larger depends on the day: P(Tmax) is the smaller on hot days and the larger on mild ones.
- **Risk:** from the biofix (crop emergence, from `potato-stages` when a planting date is given, else May 15): until 400 P-days, Low from 200, Moderate from 250, High from 300 (the first-spray threshold) and Very high from 350; from 400, the last 7 days' mean: Low from 1 a day, Moderate from 3, High from 5, Very high from 9. Crossing 400 can drop the level from Very high to Low in a day, as in the tool and VDIFN.
- **Missing data:** a day without its low or high has no P-days (the old API scored it 0).
- **Days:** midnight to midnight CST (D74).

## Checks

### Against the Crop Risk Tool

`packages/agmodels/tests/test_vegetable_diseases.py`, run in CI, on the tool's fixtures (written by `make_crt_fixtures.R` from its R code and its recorded 2025 weather at one grid cell near Eau Claire, Wisconsin):

- **The formula:** all 4,131 pairs of low and high (−5 to 35 °C and −5 to 40 °C by 0.5, low not above high) give the tool's P-days to 1e-9 with the tool's last term.
- **A season from the tool's inputs:** the daily P-days (tool's last term) and the risk levels match the tool's on all 365 days of 2025.
- **The intended change:** P(Tmax) in the last term gives a different value from P(Tmin) on a day of 10 and 28 °C; P is 0 below 7 °C and above 30 °C and 10 at 21 °C, and a day held at 21 °C earns 10 P-days. On the tool's 2025 inputs, May 15 to September 30, v2 sums 1,098 P-days against the tool's 1,107, and both reach 300 on June 27 (PLAN.md Phase 3 D).

The tool is the model v2 replaces: this shows the port is faithful where intended, not that the tool is right (D54).

### Against the old AgWeather service

`docs/validation/legacy/vegpath.md`, from `scripts/compare_vegpath.py --end 2026-09-30` (not in CI): the old API's `vegpath` query at UW Vegetable Pathology's 7 forecast locations, May 1 to September 30, 2026, against v2's model at the same points, both counted from May 1.

| Place | Old API | v2 |
| --- | --- | --- |
| Spring Green | 1189 | 1156 |
| Arlington | 1189 | 1173 |
| Grand Marsh | 1143 | 1136 |
| Hancock | 1139 | 1132 |
| Plover | 1128 | 1124 |
| Antigo | 1065 | 1092 |
| Rhinelander | 1008 | 1044 |

- v2's season totals are within 4 percent of the old API's: 0.4 to 2.8 % below in the south and center, 2.5 % and 3.6 % above at Antigo and Rhinelander (computed from the table).
- The daily weather behind them: v2's minimum averages 0.46 °F below the old API's and its maximum 0.02 °F above, over 1,071 point-days. PLAN.md attributes the difference to the last term and URMA's cooler minimums. The last term can go either way: P(Tmax) is below P(Tmin) on hot days (a high near 29 °C earns little) and above it on mild ones, which may be why the northern locations, with cooler highs, come out above the old API; this hasn't been separated.
- From Veg Path's 2026 newsletter emergence dates at Spring Green, Hancock and Antigo, v2's P-days ran 0–6 % below the old API's (PLAN.md Phase 5, "Veg Path's 2026 table"; not a script in the repository).

The old API is a reference, not the truth (D54).

## Limits and open questions

- **No field comparison:** the 300 P-day threshold and the levels around it haven't been compared with early blight onset in Wisconsin in this round; Pscheidt and Stevenson 1988's own numbers aren't checked in a test.
- **The rate curve:** P(T)'s 7, 21 and 30 °C points are Sands et al.'s for potato development in Australia; they aren't refitted to Wisconsin cultivars.
- **Emergence sets the start:** a default emergence (May 15, or `potato-stages`' from a planting date) can be off by days; a grower's emergence date is better.
- **Cheapest independent comparison:** UW Vegetable Pathology's early blight trials or scouting at Hancock (first symptoms and the emergence date of the field) against the date P-days from that emergence reached 300; P-days on Wisconet's station temperatures against the archive's at the same places would check the weather side.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_vegetable_diseases.py -k "pdays or early_blight"
uv run python scripts/compare_vegpath.py --end 2026-09-30   # needs the archive in data/ and the old API (or tmp/v1-cache)
```
