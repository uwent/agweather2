# Other weather-driven pest and crop services

What comparable services offer, where they fall short, and what v2 should match or do better (PLAN.md Phase 3).
Surveyed 2026-10-28 from their sites, documentation and extension articles. NEWA's and Enviroweather's model
pages render in JavaScript, so their structure and documentation were reviewed rather than every results screen;
fill gaps by using them in season.

## The services

| Service | Who | Weather basis | Models | Strengths | Weaknesses |
|---|---|---|---|---|---|
| [NEWA](https://newa.cornell.edu/) | Cornell IPM, NRCC | Station network (Northeast, Midwest partners) | ~40 IPM, crop and DD tools: apple scab and fire blight, grape diseases and berry moth, onion and cabbage maggot, late blight, beet Cercospora; DD calculator (average or Baskerville–Emin) | Per-model pages with "More info", references and acknowledgments; 2-, 14-, 21-day and season risk for Cercospora; profiles that store biofix dates and a dashboard; management messages tied to risk | Station-bound: results only where a station is, and only as good as it; a station-then-model flow; risk explained apart from the results; static models (extension notes RIMpro's population model does better for scab) |
| [Enviroweather](https://enviroweather.msu.edu/) | Michigan State | ~100 stations (Michigan, 10 in Wisconsin) | Insect DD models validated against MSU field timing (landscape and nursery pests, asparagus miner, seedcorn maggot), crop development, irrigation and ET, links to disease tools (TomCast) | DD and rainfall summary with a short forecast; DD maps for any date since 2008 (base 50 °F); pest timing tied to local field validation | Stations only; maps fixed to base 50; a long migration (new site since 2020, models still on the legacy site in 2025) |
| [USPest.org / DDRP](https://uspest.org/CAPS/dirindex.html) | Oregon State | PRISM daily gridded min/max; NDFD 7-day; CFSv2 and NMME seasonal; 1981–2010 normals | 145+ DD models, disease infection risk, phenology and climate-suitability maps for invasive insects ([DDRP](https://hopper.science.oregonstate.edu/CAPS/DDRP_DODMAPS_user_guide.pdf), open-source R) | Gridded across the US; forecast and seasonal projection through the season; custom DD maps with any thresholds and biofix since 2002 ([map maker](https://uspest.org/dd/maps)) | Dated interfaces and documentation (pages last updated 2018–2022); daily min/max only, so no hourly disease models; separate tools rather than one view |
| [USA-NPN Pheno Forecasts](https://usanpn.org/data/forecasts) | USA National Phenology Network (USGS) | Gridded AGDD (2.5 km per their info sheet) | 12 insects and 1 plant, binned AGDD into life-stage maps, 6 days ahead | Clean gridded stage maps; [validated](https://www.usgs.gov/publications/short-term-forecasts-insect-phenology-inform-pest-management) against citizen observations (≥ 93% for hemlock woolly adelgid) | Few species; maps only, no point detail or crop risk; a short horizon |
| [U2U Corn GDD](https://mygeohub.org/groups/u2u/aboutgdd) | Purdue and partners (Useful to Usable) | Gridded observations, a 30-day forecast, then 1991–2020 average accumulation | Corn GDD from planting with maturity, frost risk, a comparison year | The model for projecting to season's end: forecast first, then climatology, with a band for the 30-year spread; maturity against first freeze | Corn GDD only; 12 north-central states; an older interface |
| [Climate Smart Farming GDD](https://www.farmprogress.com/crops/tap-into-these-climate-smart-predictive-tools) | Cornell | Gridded, a 6-day forecast, 15- and 30-year normals | GDD from planting with any base, first and last freezes | Normals as comparison lines; maturity estimates | Northeast only; GDD only |
| AgWeather, VDIFN, Crop Risk Tool (ours) | UW–Madison | RTMA grid (old API); Open-Meteo (Crop Risk Tool) | 17 DD pairs, 5 vegetable diseases, ~30 insects (VDIFN); 16 crop models, 3 insects with weather, model output and risk shown together (Crop Risk Tool) | Gridded maps (VDIFN); hourly-native models and the weather → output → risk view (Crop Risk Tool) | Daily-only data in the old API; three separate apps; no projection to season's end; sites only in cookies |

## What v2 should offer (at least the best of each)

- **Anywhere, not just at stations.** Gridded in the box (2.5 km, like NPN and better than PRISM's 4 km), Open-Meteo for points outside it (the southern models, D10). Stations stay a reference layer and a validation source.
- **One view per model with all three layers**, as the Crop Risk Tool does now: the weather inputs the model depends on, the model's output (index, probability, degree days), and the risk score in words and colors, on one time axis. Each layer is selectable and downloadable.
- **Through the season, not just to today.** Observed, then the forecast (NBM, Phase 4), then a climate projection to the end of the year (U2U's approach: the average accumulation rate, with a band for the year-to-year spread; Phase 6 climatology). Every value carries its source, so charts mark forecast and projection.
- **Insects as life stages over time**: degree days, the stage they imply (NPN's binned stages, as a timeline at a point and as a map), and crop risk, through the forecast and the projection; adjustable biofix (NEWA keeps biofixes in profiles; v2 keeps them per site).
- **Custom degree days anywhere**, any base, upper, method and biofix, as maps and points (USPest's map maker, without its 2002 limit or dated interface).
- **Explained in place.** Disease and insect pages (what it is, which models predict it), model pages (the math, inputs, risk criteria, citations, validation, versions) with an interactive explorer to change inputs and watch the output (better than NEWA's separate tabs).
- **Validated and versioned in the open**: each model's validation and changelog on its page; API answers name the model version.
- **Alerts on model thresholds** (Phase 7), which none of the station services offer beyond dashboards.

## Weaknesses to avoid

- A station-or-model-first flow that hides results until a station and date are chosen: start from a place (search, map click, saved site) and show what's relevant there and then.
- Legal disclaimers ahead of results; risk legends kept away from the values they explain.
- Models frozen to one base temperature or one horizon.
- Rebuilt sites that leave models behind on the old one: v2 replaces all four apps at once (D12).
