# Winter rye cover crop biomass (`rye-biomass`): validation

Model version 0.2, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/models/rye_biomass.py`; its page: `rye_biomass.md` beside it. Ported in Phase 3 (PLAN.md, Phase 3 step 6) from the Crop Risk Tool (`predict_rye_biomass`, `build_rye_biomass`; copy in `tmp/shiny/crop-risk-tool/`), which it replaces.

**In short:** an unpublished logistic fit on Wisconsin data, reproduced exactly from the Crop Risk Tool on a sweep of its inputs and over a fall at Eau Claire. We don't have the fit's data, its error or the range of planting dates and rain it covers, and it hasn't been compared with measured biomass.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| The Crop Risk Tool's `predict_rye_biomass` (an unpublished fit on Wisconsin data) | Biomass (lb/ac) = ((423.1 − 1.031 × planting day − 0.2878 × fall rain in mm) / (1 + exp(−0.003663 (GDD − 1049))))², GDD single sine 0/35 °C from planting, fall rain from planting through December 31 | The equation and its inputs |
| UW–Madison Extension, "Biomass thresholds for cereal rye cover crop goals" | Biomass needed for each goal: nitrate leaching, erosion and runoff phosphorus, weed suppression | The levels: Low below 2,000 lb/ac, Moderate from 2,000, High from 4,500 |
| Badger Crop Network, "How much cereal rye cover crop biomass is needed to suppress troublesome weeds in Wisconsin?" | Weed suppression by biomass | Background for the High level |

## Choices and differences

- **Degree days:** v2's single sine applies the 35 °C cutoff on every day; the tool's `gdd_sine` skips it when the minimum is above the base (D3's finding). This changes only days over 35 °C, which don't occur between fall planting and spring in the Upper Midwest.
- **A very wet fall after late planting (version 0.2):** where the fit's height term (423.1 − 1.031 × planting day − 0.2878 × fall rain) falls below 0, biomass is 0. The tool squares the negative term, so its biomass rises again with more rain. `test_rye_biomass.py::test_biomass_stays_0_after_a_very_wet_fall`: at 2,000 GDD and planting day 300, biomass falls as fall rain rises and is 0 at 800 mm.
- **Missing days:** a missing day adds nothing to the GDD or the fall rain; rain is never estimated (D45).
- **Region:** Wisconsin, Minnesota, Iowa, Illinois and Michigan; the fit was made on Wisconsin data.

## Checks

### Against the Crop Risk Tool

The tool is what this model replaces: a reference, not the truth (D54). Its outputs were recorded by `packages/agmodels/tests/fixtures/make_crt_fixtures.R`. Run in CI (`packages/agmodels/tests/test_southern_and_cover.py`):

- `test_rye_biomass_matches_the_tool`: the equation over 1,736 cases (planting day 250 to 320 by 10, fall rain 0 to 300 mm by 50, GDD 0 to 3,000 by 100) agrees within a relative 1e-12. None of these cases has a negative height term, so version 0.2's change doesn't touch them.
- `test_rye_season_from_a_fall_planting`: a planting on September 15, 2025, at an Eau Claire, Wisconsin grid cell, through December 31 (108 days): GDD totals and fall rain within 0.000001, biomass within a relative 1e-9.
- `test_rye_fall_precip_stops_at_new_year`: fall rain stops counting on December 31.

The season covers the fall only; spring, when the levels are read, is covered by the sweep's GDD range, not by a season.

## Limits and open questions

- The fit is unpublished: its data, error, and the planting dates, rain and GDD it covers aren't known to us. Planting days outside about 250–320 and fall rain over 300 mm are outside what's been checked against the tool.
- Biomass levels off at the square of the height term: about 12,500 lb/ac for a planting on day 274 (October 1) after 100 mm of fall rain. Whether the fit's data reached that high isn't known.
- Seeding rate, soil, nitrogen and termination aren't inputs.
- **Cheapest independent comparison:** spring biomass clipped in Wisconsin cereal rye fields with known planting dates, from UW–Madison's cover crop research or on-farm network (the work behind the Badger Crop Network's articles), on the archive at each field's cell.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_southern_and_cover.py packages/agmodels/tests/test_rye_biomass.py
Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R   # the tool's outputs (needs its copy in tmp/shiny/crop-risk-tool)
```
