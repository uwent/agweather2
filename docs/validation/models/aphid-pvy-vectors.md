# Aphid PVY vectors (`aphid-pvy-vectors`): validation

Model version 0.1, written 2026-11-18 (D98). The model: `packages/agmodels/src/agmodels/insects/aphid_pvy_vectors.py`, run by the insect engine (`agmodels.phenology`, VDIFN's generations); its page: `aphid_pvy_vectors.md` beside it. Ported from VDIFN in Phase 3 (PLAN.md Phase 3 D step 3); its sources are listed for review in `docs/insect-models.md`.

**In short:** One curve of the risk that aphids spread potato virus Y (PVY), fitted by UW–Madison's Vegetable Entomology lab (Bradford and Groves, unpublished) to suction-trap catches of six aphid species, 2016–2023, each weighted by its abundance in Wisconsin and how well it transmits the virus. v2 reproduces VDIFN's version exactly. The fit hasn't been published or checked on years it wasn't fitted to.

## Sources and what we took from each

| Source | What it gives | What we took |
| --- | --- | --- |
| VDIFN's entry (`../ag-vdifn/db/seeds.rb`, `pvy-vectors`) | Thresholds 39.2/86 °F, biofix January 1, one risk window (1838, 2515, 3228); its text: species models from the Upper Midwest Aphid Suction Trap Network (run since 2005 from the University of Illinois), weighted by published transmission efficiencies, summed and refitted as one degree-day model on 2016–2023 data | All of it, unchanged |
| Bradford and Groves, Vegetable Entomology Lab, UW–Madison, unpublished analysis (cited in the spec) | The fit behind VDIFN's numbers | Cited; the analysis itself isn't in the repository |
| Mondal et al. 2016 ([doi:10.1093/ee/nvw131](https://doi.org/10.1093/ee/nvw131)); Yoho et al. 2026 ([doi:10.1093/jee/toag257](https://doi.org/10.1093/jee/toag257)) | Candidates for comparison (`docs/insect-models.md`) | Nothing yet: not read for this report |

## Choices and differences

- **Degree days:** single sine, 39.2/86 °F, from January 1, as VDIFN computed them. Whether that is the method its source's numbers were made with isn't checked (D37; part H).
- **Severity:** VDIFN's rule: in each window (start, peak, end) (1838, 2515, 3228), a level from 0 to 4 rising along a half sine from start to peak and falling from peak to end, rounded up; 0 outside.
- **Freeze:** after day 250 (early September) severity is lowered by the number of days in the last 14 with a minimum at or below −2 °C, the Crop Risk Tool's rule, used for every insect; VDIFN subtracted freezing days only from November (PLAN.md Phase 3 D step 3).
- **Days:** midnight to midnight CST (D74); VDIFN's came from the old API's local days.
- **Method, against the fit:** VDIFN's text says the fit itself used single sine 39.2/86 °F from January 1, so for this model the method matches its source as far as the text goes.
- **The window's end:** the description (the page's summary, VDIFN's text) says risk "remains elevated through vine kill", but the severity falls to 0 at 3,228 degree days, as VDIFN's did. The text and the curve disagree after the peak.

## Checks

### Against VDIFN

VDIFN is the tool this model replaces: a reference, not the truth (D54). These tests show the port reproduces it, not that its timings are right. Run in CI:

- `test_insects.py::test_the_sine_ramp_by_its_steps_matches_the_sine`: v2's severity ramp equals VDIFN's `Insect#sev_ramp` (a half sine from start to peak and back to end, times 4, rounded up; `_sine_ramp_reference` is its Ruby term for term) on this model's generation, (1838, 2515, 3228), exactly, at every 0.01 °F·d from start to end and at 2,000 random totals in each.
- `test_insects.py::test_vdifn_generations_match_its_severity`: VDIFN's own `Insect#total_to_severity`, run in Ruby (`fixtures/make_vdifn_fixtures.rb`), at 701 totals from 0 to 3,500 by 5 on four generation tables; v2's severity (0 to 4) is identical at every one. None of the four is this model's table.
- `test_degree_days.py::test_matches_the_old_api`: v2's single-sine degree days at 39.2/86 °F match the old AgWeather API's calculator, which VDIFN read its totals from, to within 0.000001 °F·d at 231 pairs of daily minimum and maximum.
- The thresholds, biofix and generation are VDIFN's entry in `../ag-vdifn/db/seeds.rb`, unchanged.

Not compared: v2 and VDIFN on the same days' weather (VDIFN's maps against v2's), or the freeze reduction (different by design, above).

## Limits and open questions

- The fit is unpublished: its data, the species weights and how well the curve fits the catches aren't in the repository. Ben is an author and can supply them.
- One curve for six species whose flights differ; a field's risk also depends on its crop oil and insecticide sprays, which the model doesn't see.
- Moving to D36's life-stage curves with the source's own degree-day method is part H's review (`docs/insect-models.md`); this report describes the model as ported (version 0.1).
- **Cheapest independent comparison:** The suction trap network's Wisconsin catches for 2024 onward, weighted as the fit was, against the curve: held-out years of the same data. The data and the weights are the lab's own, so this needs no outside party.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_insects.py packages/agmodels/tests/test_degree_days.py
ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb       # VDIFN's severities (needs ../ag-vdifn)
ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb   # the old API's degree days (needs ../ag-weather)
```
