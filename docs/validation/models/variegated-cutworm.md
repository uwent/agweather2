# Variegated cutworm (`variegated-cutworm`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H2). The model: `packages/agmodels/src/agmodels/insects/variegated_cutworm.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `variegated_cutworm.md` beside it. Version 0.1 was VDIFN's window (900, 1,450, 2,100 degree days, single sine 45/80.1 °F from May 1), checked only against VDIFN; this report replaces that one.

**In short:** rebuilt on Simonet et al. 1981, the source VDIFN credited for its thresholds: 45 °F with no upper threshold from January 1, two moth flights peaking at 900 and 2,160 degree days as in 15 years of Ohio light-trap catches, and caterpillars timed from each flight by the paper's development times. In Wisconsin's black light traps the first flight's moths came somewhat later than the model's and the second's somewhat earlier, but the traps caught only 273 moths in seven years.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Simonet, Clement, Rubink and Rings 1981 ([doi:10.4039/Ent113891-10](https://doi.org/10.4039/Ent113891-10)), Wooster, Ohio | Laboratory thresholds and °C·d: egg 89.2 above 5.6 °C, larva 386.6 above 6.2, pupa 210 above 8.5, total 676.2 above 7.2 (p. 895); instars I–III 131.4, IV–VI 255.0 above 6.2; pre-oviposition 127.5 above 3.5 (p. 895). Black light catches 1965–1979 summed above 7.2 °C from January 1: flight peaks at about 500 and 1,200 °C·d (900 and 2,160 °F·d), 733 ± 67 °C·d (mean ± SD, range 625–925) between peaks; the laboratory's 775 °C·d from egg to egg laying (pp. 896–897). No upper threshold; 26.7 °C (80.1 °F) is one of the rearing temperatures. Scouting for eggs and young larvae should begin at peak moth capture (p. 897) | The method, the flight peaks, the generation time and its SD, the larval timing, the scouting window |
| MSU Enviroweather's variegated cutworm model (`docs/enviroweather-models.md`) | Single sine 45 °F, no upper, from March 1: first flight 900, egg laying 1,070, hatch 1,202, second flight 2,160, egg laying 2,330, hatch 2,500; no source cited | Compared: its hatch, 302 after first flight |
| USPest.org's `vcw` model (Coop and Berry 1987, peppermint, Oregon), via VDIFN's spreadsheet | Single sine 41/88 °F; events 900, 1,450, 2,100 | Not used (Ben hasn't chosen between the two sources; Simonet is part H's lead option) |
| DATCP's black light trap network, 2020–2026 ([data](../data/datcp-blacklight-traps/README.md)) | Weekly variegated cutworm moths at 6–13 sites | The first flight's spread; a check |
| VDIFN | 45/80.1 °F from May 1; (900, 1,450, 2,100) | Replaced |

## Choices and differences

- **Degree days:** single sine above 45 °F (7.2 °C, Simonet's threshold for total development) with no upper threshold, from January 1. Simonet et al. don't say how they computed daily degree days; single sine is assumed. VDIFN's 80.1 °F cap has no source, and its May 1 start isn't Simonet's (from January 1 it moves the first peak about 9 days earlier at Arlington: June 14 against June 23 in the normals).
- **Adult flight:** a PERT curve (200, 900, 1,500), weight 0. The peak is Simonet's; the paper gives no spread (its Fig. 3 isn't legible in our copy), so start and end are set roughly from DATCP's Wisconsin catches (their first flight's 10th and 90th percentiles, 488 and 1,157; the curve's are 551 and 1,209). A least-squares fit with the peak held at 900 would start at 20 degree days, implausibly early, so the start is kept at 200.
- **Generations:** two, 1,260 degree days apart (Simonet's peaks, 900 to 2,160), with their SD between peaks, 67 °C·d (120 °F·d). Simonet calls them the overwintering generation and the first; a third would peak near 3,400, past the end of most Wisconsin seasons (Arlington's normal total at 45 °F is 3,708 by December 31).
- **Larvae:** timed from each moth's emergence, 320 °F·d later (pre-oviposition and egg) for 645 °F·d (the larval stage), weight 1, the risk. Simonet's stage thresholds differ (3.5, 5.6, 6.2 °C), so each stage's °C·d was carried to the 7.2 °C base at a 20 °C day (× 0.78, 0.89 and 0.93: 99, 79 and 359 °C·d). Enviroweather puts hatch 302 after first flight.
- **Scouting window:** "Scout for eggs and young caterpillars" from each flight's peak (50 %) to 95 % of it: 887 to 1,279 and 2,146 to 2,586 degree days.
- **Against Coop and Berry:** their peppermint model (41/88 °F) is the other candidate. Its events (900, 1,450, 2,100) were VDIFN's; it wasn't read for this rebuild.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_variegated_cutworm.py`, run in CI:

- 45 °F is 7.2 °C; no upper threshold; from January 1.
- The flights peak at 900 and 2,156 degree days, against Simonet's 900 and 2,160 (500 and 1,200 °C·d) in 15 years of catches at Wooster; 1,256 apart, inside their range of 625–925 °C·d (1,125–1,665 °F·d).
- Two flights and no third.
- The larvae's lag and duration are Simonet's times carried to 7.2 °C at 20 °C: 320 and 645 °F·d. Caterpillars hatch 320 degree days after a moth emerges; Enviroweather's hatch comes 302 after its first flight.
- The scouting window opens at each flight's peak, 900 and 2,160 (± 20).

### Flights against Wisconsin's black light traps

`scripts/check_cutworms.py`, part 2; full output in [black-cutworm/traps.md](black-cutworm/traps.md). Each moth caught is dated by single-sine degree days 45 °F without an upper threshold from January 1 at its week's middle day, on the archive at the trap's cell, and the flights are split at July 7 (as `scripts/check_insect_traps.py` does).

<!-- prettier-ignore -->
| Flight | Moths | Site-weeks with moths | 10 % | 25 % | 50 % | 75 % | 90 % | Model's 10 / 50 / 90 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| First | 79 | 35 | 488 | 625 | 1,072 | 1,072 | 1,157 | 551 / 887 / 1,209 |
| Second | 194 | 59 | 1,655 | 1,788 | 2,064 | 2,230 | 2,412 | 1,781 / 2,146 / 2,500 |

- 273 moths in seven years, 4 to 64 a flight-year; the first flight's median rests on 2025's 37 moths (1,072). Year by year the first flight's median ranged from 504 (2020) to 1,162 (2024) and the second's from 1,851 (2021) to 2,230 (2022).
- The first flight's spread was set from these catches, so its percentiles are a fit; its median, 1,072 against the model's 887, isn't.
- The second flight came about 80 degree days earlier than the model's (2,064 against 2,146), within the year-to-year range.

### Normal dates

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 45 °F without an upper threshold, from January 1):

<!-- prettier-ignore -->
| Event (°F·d from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First flight, 10 % (551) | May 28 | May 31 | June 7 |
| First flight peak (900); scouting begins | June 14 | June 18 | June 25 |
| Scouting window closes (1,279) | June 30 | July 4 | July 13 |
| First caterpillars' peak (1,533) | July 10 | July 14 | July 24 |
| Second flight peak (2,156) | August 2 | August 8 | August 22 |
| Second caterpillars' peak (2,790) | August 28 | September 6 | October 5 |

Version 0.1 reached 900, 1,450 and 2,100 from May 1 (45/80.1 °F) around June 23, July 15 and August 10 at Arlington. UW Vegetable Entomology's cutworms page describes variegated cutworm only in a photo caption, and VDIFN's text put egg laying at 900 from May 1, so there is no UW timing to compare with.

## Limits and open questions

- **Which source:** Simonet's Ohio light traps (45 °F, from January 1) or Coop and Berry's peppermint model (41/88 °F) is Ben's call; this rebuild takes Simonet.
- Outbreaks are sporadic (Simonet et al.: "prediction capabilities … are difficult or impractical" from temperature alone), and the moths may overwinter as adults, larvae or pupae, which may explain early double peaks. The model times flights, not whether a damaging population will appear.
- Wisconsin's black light traps catch few moths; a better check needs more catches or scouting records.
- The degree-day method behind Simonet's trap sums isn't stated.
- The stages' conversions to one base assume a 20 °C day: on cooler days the pre-oviposition and egg periods (lower thresholds) take fewer degree days at 45 °F than the conversion gives, and on hotter days more.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_variegated_cutworm.py
uv run python scripts/check_cutworms.py   # needs the archive in data/
# The normal dates: /api/v2/climate/normals?dd=sine_45 at each place (Arlington 43.30, −89.35; Hancock 44.12, −89.53;
# Rhinelander 45.64, −89.41) through Django's test client in `uv run app/manage.py shell`, read off at each total
```
