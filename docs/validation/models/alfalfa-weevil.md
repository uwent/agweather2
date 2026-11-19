# Alfalfa weevil (`alfalfa-weevil`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/alfalfa_weevil.py`, a stage table run by the insect engine (`agmodels.phenology`, `InsectModel`); its page: `alfalfa_weevil.md` beside it. Ported from the Crop Risk Tool on 2026-10-28 (PLAN.md Phase 3 D3; the tool's `insect_models$afw` in `tmp/shiny/crop-risk-tool/src/models.R`). It hasn't been rebuilt on life-stage curves (D36) yet: that waits for the insect review (`docs/insect-models.md`, `docs/models-plan.md` part H).

**In short:** the model reproduces the Crop Risk Tool on the same weather: the level agrees on every day of 2025 at Eau Claire. The tool cites no source for its stage table, but its larval stages after egg hatch are Litsinger and Apple 1973's Wisconsin development times within 3 degree days, its adult emergence is Harcourt 1981's within 2, and its heaviest-risk span (440–595) lies close to Harcourt's main feeding period (468–603). Egg hatch at 300 degree days from January 1 has no source we could check, and nothing in the model has been compared with alfalfa weevil counts in Wisconsin fields.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool (`src/models.R`, `afw`; doc page `docs/insects/alfalfa-weevil.md`) | Single sine 9/30 °C from January 1, in °F·d; a stage table: egg hatch 300, 2nd instar 370, 3rd instar 440, 4th instar 505, pupal stage 595, adult emergence 815, adult diapause 1000, with severities 1, 2, 3, 4, 2, 1, 0; the end-of-season freeze rule. Its doc page links UMN's VegEdge and Wikipedia and cites no study | All of it: the model |
| Litsinger and Apple 1973 (Arlington, Wisconsin, 1971; `tmp/references/insects/`) | Base 50 °F for eggs and 48 °F (8.9 °C) for larvae; thermal units above 48 °F from eclosion to 50 % of the 2nd, 3rd and 4th stadia and the prepupa: 70.6, 140.6, 207.0 and 297.9 (Table 3; to first appearance 64.3, 127.8, 198.8, 288.3, Table 2), by Arnold's max–min method; the 4th stadium is the longest and does most of the damage | Not cited by the model; compared below |
| Harcourt 1981 (southern Ontario, 1973–1980; `tmp/references/insects/`) | Single sine above 9 °C from April 1; peaks in °C·d: hatch 155, instar 1 176, instar 2 218, instar 3 260, instar 4 306, cocooning 335, pupa 403, adult emergence 454; most feeding damage between 260 and 335; predicted peak dates within 1 or 2 days of those observed in 1977–1980 (Table II) | Not cited by the model; compared below |
| Enviroweather (MSU), AlfalfaWeevil (`docs/enviroweather-models.md`) | Single sine base 48 °F, no upper, from January 1: light feeding 300, major feeding 439, pupation 596, end of pupation and feeding 820; an observed date resets the stages after it; no source cited | Compared only |

## Choices and differences

- **Degree days:** single sine, 48.2 °F (9 °C), cutoff 86 °F (30 °C), from January 1: the tool's thresholds. Harcourt's base is the same 9 °C, single sine, but counted from April 1; Litsinger and Apple's is 48 °F by a max–min method, counted from each larva's eclosion; Enviroweather's is 48 °F with no upper. At Eau Claire in 2025 the tool's total had reached 42 degree days by March 31 (`crt_insect_afw_eau_claire_2025.csv`), so counting from January 1 puts events a little earlier than counting from April 1 would.
- **One intended difference from the tool:** its `gdd_sine` skips the upper cutoff on days whose minimum is above the base; v2 keeps the Baskerville–Emin formula (PLAN.md Phase 3 D3).
- **Risk:** the stage table's step severities, less the shared end-of-season freeze reduction (after day 250, the number of days in the last 14 at or below −2 °C; the tool's rule, adopted for every legacy insect, PLAN.md Phase 3 D3). The weevil is in diapause (severity 0) long before day 250, so the reduction never matters here.
- **No observed biofix:** Enviroweather lets a grower's observed dates reset the later stages; ours runs from January 1 only.
- **Not on curves:** the table is steps, with no spread between individuals; D36's curves wait for the insect review.

## Checks

### Against the Crop Risk Tool on the same weather

`packages/agmodels/tests/test_insects.py::test_crop_risk_tool_insects_match_over_a_year[afw-alfalfa-weevil]`, run in CI, on fixtures made by the tool's own R code (`make_crt_fixtures.R`) for one cell at Eau Claire, Wisconsin, through 2025 (365 days: `crt_daily_eau_claire_2025.csv`, `crt_insect_afw_eau_claire_2025.csv`):

- Each day's degree days equal the tool's (to 1e-9) on all but 14 days. On those 14 the minimum is above the base and the maximum above 86 °F; the tool's value is (min + max) / 2 − base, without the cutoff, and ours is lower, as the test asserts.
- Given the tool's own running totals, our severity, freeze reduction and stage label equal the tool's on all 365 days.
- End to end (computed from the same two fixtures; the test asserts the parts above, not this): the tool's season total runs ahead of ours by 4.3 degree days by June 30 and 7.7 by August 31, and stays 7.7 ahead to December 31. Every stage begins on the same day in both, so the level agrees on all 365 days.

The tool is the system v2 replaces, a reference rather than the truth (D54): this shows the port is faithful, not that the model is right.

### Against its sources' numbers

Not a test: a comparison of the stage table's thresholds with the two published studies its numbers appear to follow. The tool cites neither; the match below is our reading.

<!-- prettier-ignore -->
| Stage in the table | Ours, °F·d from January 1 | Ours, after egg hatch | Litsinger and Apple 1973, from eclosion to 50 % | Harcourt 1981, peak, °F·d from April 1 |
| --- | --- | --- | --- | --- |
| Egg hatch | 300 | 0 | | 279 (peak hatch) |
| 2nd instar | 370 | 70 | 70.6 | 392 |
| 3rd instar | 440 | 140 | 140.6 | 468 |
| 4th instar | 505 | 205 | 207.0 | 551 |
| Pupal stage | 595 | 295 | 297.9 (prepupa) | 603 (cocooning), 725 (pupa) |
| Adult emergence | 815 | 515 | | 817 |
| Adult diapause | 1000 | 700 | | |

Harcourt's °C·d are converted at × 1.8 and rounded (155, 218, 260, 306, 335, 403 and 454 °C·d).

- The larval stages begin, after the table's egg hatch, within 3 degree days of Litsinger and Apple's times from eclosion to 50 % of each stadium (the 4th instar at 300 + 205 against 300 + 207.0). Those are times from each larva's own hatch, so adding them to the season's first hatch treats all eggs as hatching at 300.
- Adult emergence at 815 is within 2 of Harcourt's peak adult emergence (454 °C·d, 817 °F·d), though Harcourt counts from April 1.
- The heaviest risk (severity 3 and 4, from 440 to 595) lies close to Harcourt's "most of the feeding damage occurs between 260 and 335 °C·d after April 1" (468–603 °F·d), and covers Litsinger and Apple's 4th stadium, which does most of the damage.
- Egg hatch at 300 ("begin scouting") is near Harcourt's peak hatch (279 from April 1, so about 300 from January 1 if 20 or so degree days come before April). Enviroweather uses 300 for "light feeding starts". We found no study giving 300 for first hatch.
- Enviroweather's 439, 596 and 820 follow the same pattern (300 + 139, about Litsinger and Apple's 140.6; 300 + 296, about their 297.9; Harcourt's 817), which suggests both tools drew on these studies.

Harcourt's own model, from April 1 and his peak hatch, predicted the peak dates of 8 stages within 1 or 2 days of those observed in 4 validation years in Ontario (Table II). That is a validation of his model, not of this table.

## Limits and open questions

- **No field check:** the model hasn't been compared with alfalfa weevil larval counts or tip feeding in Wisconsin.
- **Uncited:** the model's citation is the Crop Risk Tool alone. Litsinger and Apple 1973 (doi 10.1093/jee/66.2.309) and Harcourt 1981 (doi 10.4039/Ent113601-7) are the likely sources and should be cited if the review confirms them.
- **Two methods mixed:** the table combines Litsinger and Apple's max–min thermal units counted from eclosion with Harcourt's sine degree days counted from April 1, on one sine total from January 1. Eggs develop above 50 °F (Litsinger and Apple), not 48.2; and some eggs are laid in fall (the tool's doc page), so first hatch depends on when eggs were laid as well as on spring heat.
- **Steps, not curves:** the table jumps at each threshold and has no spread between individuals; the D36 rebuild should take its curves from Harcourt's stage durations (instar 1 42, instar 2 42, instar 3 46, instar 4 58, prepupa 39, pupa 80 °C·d).
- **Cheapest independent comparison:** Harcourt 1981's Table II: observed peak dates of 8 stages in 4 years (32 dates) in the Bay of Quinte area, Ontario, run on weather for that area (outside our grid: Open-Meteo's historical data), counting from both January 1 and April 1. Then Wisconsin: dated alfalfa weevil larval counts from UW–Madison or DATCP field surveys, if such records exist (not checked).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py -k crop_risk_tool   # the parity test
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # rebuild the fixtures from the tool (PLAN.md Phase 3 F)
```

The end-to-end figures: run `model("alfalfa-weevil").outputs()` on `crt_daily_eau_claire_2025.csv`'s minimum and maximum (with the day of year) and compare `dd_total` and `risk()` with `crt_insect_afw_eau_claire_2025.csv`'s `cum_gdd` and `severity`.
