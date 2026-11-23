# Apple bud and bloom stages (`apple-stages`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/apple_stages.py`; its page: `apple_stages.md` beside it (not yet written). The research notes this condenses are in the project's working notes, `docs/plans/models.md` part B1 and B5 and its "Sources read".

**In short:** the stages begin at NEWA's degree-day thresholds, which all sit inside the ranges Cornell's Scaffolds Fruit Journal gives for McIntosh at Geneva, New York; on the same weather the stages fall on NEWA's day in 95–102 of 103 station-seasons and never more than 2 days off; against 57 stages observed at six Wisconsin sites in 2023–2026, the model was in the observed stage on 41 and within 3 days on 46, with no bias overall. Early cultivars (Zestar, Paula Red) run a few days ahead of it, as a McIntosh-timed table predicts.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| NEWA (Cornell), apple stage table in its insect pages' management guides (`"phenologicalStagesBaseFormula": "base43BE"`), read from its site 2026-11-17 | Stages by degree days base 43 °F, Baskerville–Emin, from January 1: dormant to 74, silver tip 75, green tip 101, half-inch green 165, tight cluster 199, pink 290, bloom 346, petal fall 454, post petal fall 580. Its scab model starts at green tip 101; its fire blight model takes first blossom at 230 and petal fall at 578 or June 15 | The thresholds (D95: NEWA wins where sources conflict), with post petal fall named fruit set |
| Agnello (ed.), Scaffolds Fruit Journal 24 (2015), "Upcoming pest events" ([5-4MD.pdf](http://web.archive.org/web/2015id_/http://www.scaffolds.entomology.cornell.edu/2015/5-4MD.pdf) and the April 13 to May 18 issues) | McIntosh at Geneva, New York: each stage's normal ± one standard deviation in DD43 from January 1, over about 26 years: silver tip 61–109, green tip 97–145, half-inch green 136–221, tight cluster 176–282, pink 271–317, bloom 345–417, petal fall 448–524, fruit set 510–598 | The check on NEWA's thresholds (below), the stages' names, and `MARGIN_DAYS` (3): the standard deviations, 24–38 DD, are 2–3 days of April and May warmth in Wisconsin |
| Rosenberger, Cornell Hudson Valley Lab blog, [2016-03-10](https://blogs.cornell.edu/plantpathhvl/2016/03/10/follow-up-on-scab-development/) | Scaffolds' ranges are Baskerville–Emin from January 1, 26 years of Geneva observations (green tip mean 121, SD 24) | The method and start date behind Scaffolds' numbers |
| Baskerville and Emin 1969, Ecology 50, 514–517 ([10.2307/1933912](https://doi.org/10.2307/1933912)) | The single sine from daily max and min | The degree-day method, as published |
| Enviroweather (MSU), `ApplePhenologyStrategy.php` (inventory: `docs/enviroweather-models.md`) | DD base 42 °F, Baskerville–Emin, no upper, from January 1 by the code's comment: first green 127, tight cluster 242, pink 367, king bloom 395, full bloom 422, petal fall 511, then first to ninth cover (749 to 3545); McIntosh green tip 110; bloom for fire blight from pink (367) to first cover (749). No source cited | Compared only (NEWA's base 43 table wins, D95); the cover sprays and harvest maturity are left out |
| Hoogenboom et al. 2015, WTFRC report AP-12-104156 ([PDF](https://treefruitresearch.org/wp-content/uploads/2019/11/Report-723.-Hoogenboom_Final_Report_Apple_2015.pdf)) | Gala, Red Delicious and Cripps Pink stages by GDD base 43 °F in central Washington, 2011–2013 | Nothing: the start date and method aren't stated, and its numbers run well below Geneva's |
| UW Fruit Program, [Unseasonably warm weather effect on fruit crops](https://fruit.wisc.edu/2024/03/01/unseasonably-warm-weather-effect-on-fruit-crops/) (March 1, 2024) | "GDD is not a good predictor of bud break" | A limit stated on the model page; UW's scouting reports ask growers to record their own green tip and petal fall dates for NEWA's models |
| Wisconsin stage observations, 2023–2026 ([data](../data/wi-apple-stages/README.md)) | Dated stages at WMARS, PARS and four orchards | The check below |

No published Wisconsin or Michigan DD43 stage table was found.

## Choices and differences

- **Degree days:** base 43 °F, single sine by Baskerville and Emin's method, no upper threshold, from January 1 (the shared running total `dd_sine_43`). NEWA's own single sine has `sin` where the method has `asin`, and π as 3.14; we use the method as published, which moves a stage's first day by at most 2 days from NEWA's on the same weather, and usually not at all (below).
- **Thresholds:** NEWA's eight, each the degree days at which a stage begins. NEWA's "post petal fall" (580) is named fruit set, Scaffolds' name for the stage that range covers. NEWA's thresholds sit below Scaffolds' midpoints for every stage but fruit set (green tip 101 against 121, bloom 346 against 381, petal fall 454 against 486), as a stage's beginning should; bloom is at the bottom of its range (345).
- **Days:** the grid's days, midnight to midnight CST (D74); NEWA's pages use the station's local clock.
- **Against Enviroweather:** a different base (42 °F) and table; its bloom window for fire blight runs from pink to first cover, about 240 DD past petal fall. `fire-blight` takes its window from these stages or the grower's dates instead (its own report).
- **Against NEWA's other models:** NEWA's scab model starts at 101 (our green tip, so the same day); its fire blight model takes first blossom at 230, inside tight cluster by its own stage table, not at bloom's 346. That choice belongs to `fire-blight`.
- **Not modelled:** harvest maturity (MSU's McIntosh, Jonathan and Red Delicious formulas: out of scope, and one of the three McIntosh formulas has its temperature sign reversed in MSU's code), the cover-spray intervals after fruit set, and an offset by cultivar (no source gives one in DD43; a possible later option if the scouting reports keep giving stages by cultivar).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_crops.py`, run in CI:

- Every threshold inside Scaffolds' range for its stage (McIntosh, Geneva, normal ± 1 SD, DD43 from January 1): silver tip 75 in 61–109, green tip 101 in 97–145, half-inch green 165 in 136–221, tight cluster 199 in 176–282, pink 290 in 271–317, bloom 346 in 345–417, petal fall 454 in 448–524, fruit set 580 in 510–598.
- Stages against degree-day totals (none before 75; green tip at 101; bloom at 400).
- Each stage's first day within a day of NEWA's sine on six recorded field seasons at Lincoln, Nebraska (1999–2002, 2004, 2005); missing days add nothing; the same code on a grid.

### Against NEWA on the same weather

`scripts/check_apple_stages.py`, part 1; full table in [apple-stages/newa-and-observations.md](apple-stages/newa-and-observations.md). NEWA's stages are recomputed from its published thresholds and its degree-day formula (`scripts/newa_reference.py`, which reproduces NEWA's apple scab and fire blight pages exactly on their exports, its degree days included) on the hours of 36 Wisconsin NEWA orchard stations, 103 station-seasons in 2024–2026. Ours run on the same daily max and min, so only the sine differs.

| Stage | 2 days early | 1 day early | Same day | 1 day late | 2 days late |
| --- | --- | --- | --- | --- | --- |
| Silver tip | 0 | 0 | 95 | 6 | 2 |
| Green tip | 0 | 0 | 97 | 6 | 0 |
| Half-inch green | 1 | 0 | 100 | 2 | 0 |
| Tight cluster | 0 | 0 | 102 | 0 | 1 |
| Pink | 1 | 2 | 99 | 1 | 0 |
| Bloom | 0 | 1 | 102 | 0 | 0 |
| Petal fall | 0 | 1 | 100 | 2 | 0 |
| Fruit set | 0 | 4 | 99 | 0 | 0 |

Ours against NEWA's first day of each stage: the same day in 95 to 102 of the 103 station-seasons, never more than 2 days apart. Silver tip and green tip differ most: early in spring a day adds few degree days, so a small difference in the formula can move the date.

### Against stages observed in Wisconsin

`scripts/check_apple_stages.py`, part 2; full table in [apple-stages/newa-and-observations.md](apple-stages/newa-and-observations.md); data in [../data/wi-apple-stages/](../data/wi-apple-stages/README.md). 68 dated statements gathered from UW–Madison's fruit program (phenology updates, scouting reports, grower chats), the Peninsular Agricultural Research Station's weekly updates, Sunrise Orchards' bloom posts and DATCP's field notes, 2023–2026; 57 at six located sites (WMARS 21, PARS 21, Sunrise Orchards 10, two orchards with 2 each and one with 1) that name a stage on NEWA's list are used. The model runs on the archive's days at each site's cell; "inside" means the model's stage on that date is one the observation allows (a range like "tight cluster to pink" allows both), and a miss counts the days to the nearest day the model was in an allowed stage.

| Observations | Inside the model's stage | Within 3 days | Model late | Model early | Mean, days |
| --- | --- | --- | --- | --- | --- |
| All | 41 of 57 | 46 | 8 | 8 | +0.0 |
| Early cultivars (Zestar, Paula Red, PARS's and WMARS's "early cultivars") | 5 of 12 | 7 | 7 | 0 | +2.8 |
| The rest | 36 of 45 | 39 | 1 | 8 | −0.8 |

- **Early cultivars run ahead of the model** (7 of its 8 late misses): Zestar and Paula Red at pink on April 24, 2023 at WMARS, 11 days before the model's pink (217 DD); Zestar 3–5 days ahead at tight cluster, pink, king bloom and fruit set in 2024–2026 at WMARS and PARS. The model's stages are McIntosh's.
- **Later cultivars and some growers' dates run behind it:** WMARS's "later cultivars at silver tip" on April 10, 2025, when the model had passed it 14 days before (137 DD); Fuji at popcorn (the end of pink) 4 days after the model's pink ended, on May 7, 2025; green tip at Gwenyn Hill Farm (Delafield) on April 21, 2025, 6 days after the model left it; petal fall at Warm Belly Farm (Fort Atkinson) on May 18, 2026, 7 days after the model's petal fall ended.
- The 47 observations first used (before rows by cultivar and fruit sizes were added from the same pages) gave 33 inside and 38 within 3 days, also with no mean bias.

## Limits and open questions

- **McIntosh timing.** The thresholds are for McIntosh (Scaffolds) or general (NEWA); early cultivars run about 3 days ahead on average here (up to 11), later ones behind. A grower's own green tip and first bloom dates are the better guide, and the scab and fire blight models take them at a location.
- **Bud break is poorly predicted by degree days** (UW Fruit Program, 2024): after a warm late winter, silver tip and green tip by degree days can come weeks before buds move (NEWA's 101 DD green tip came on March 14 at Eau Claire in 2024). Chilling and forcing models (our `chill` module covers dormancy) aren't used.
- **Few early-stage observations:** most of the 57 are pink, bloom and petal fall; only 9 name silver tip, green tip or half-inch green, so the early thresholds are checked mainly against Scaffolds and NEWA, not Wisconsin.
- **Sites:** "southern Wisconsin" in UW's reports is placed at WMARS by our reading; PARS's updates describe Door County's orchards in general. No observations from Bayfield, Eau Claire or southeastern Wisconsin.
- **In sample:** the thresholds were not fitted to these observations, so this is a test, but a small one (six sites, four years).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_crops.py -k apple
uv run python scripts/fetch_newa.py          # NEWA station hours into tmp/newa/hours/ (once)
uv run python scripts/check_apple_stages.py  # needs the archive in data/ and the station hours
```
