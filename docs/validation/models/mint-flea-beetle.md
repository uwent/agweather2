# Mint flea beetle (`mint-flea-beetle`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H5). The model: `packages/agmodels/src/agmodels/insects/mint_flea_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `mint_flea_beetle.md` beside it. Version 0.1 was VDIFN's window (1,475, 1,675, 1,880 degree days, single sine 41 °F from January 1), whose start was USPest's and whose peak and end weren't; this version rebuilds it on USPest's events as curves.

**In short:** Oregon State's mint flea beetle model (USPest `mfb`, Berry et al.; partly validated, Pacific Northwest) as D36 curves: single sine above 41 °F from January 1 (its 103 °F upper threshold never binds in Wisconsin), egg hatch from 405 and larval feeding until the larvae leave the rhizomes (from 900), adult emergence from 1,475 and the adults' feeding after it. USPest gives only when each stage begins, so every spread is a judgment. In Wisconsin the model's first adults come in late June in the south and early July in the north; Commercial Vegetable Production in Wisconsin says late July, but its own soil degree-day number (1,100 above 40 °F at 6 inches) comes even earlier on AgWeather's soil temperatures. No Wisconsin field counts are known.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| USPest's mint flea beetle model ([uspest.org, `mfb`](https://uspest.org/cgi-bin/ddmodel2.pl?spp=mfb), read 2026-11-21; Berry et al., Oregon State) | Single sine, 41/103 °F, from January 1; "partly validated", Pacific Northwest. Events: 405 eggs hatch (first instar begins); 580 second instar; 785 third instar; 900 larvae exit rhizomes; 1,205 prepupa; 1,395 pupa; 1,475 adult emergence begins | The method (without the upper threshold, below), the starts of hatch, of larvae leaving and of adult emergence |
| Pacific Northwest Insect Management Handbook, mint flea beetle (2026) | Eggs overwinter in the soil and hatch from early April through May; larvae in roots and rhizomes until early June; adults emerge late June and July, feed two to three weeks before laying eggs in July and August; sweep sampling | The spreads of hatch and emergence (judgments), the adults' feeding before egg laying |
| Commercial Vegetable Production in Wisconsin (A3422), 2026 | One generation; adults emerge in late July in Wisconsin, at about 1,100 degree days above 40 °F in soil 6 inches deep; thresholds in adults per 100 sweeps; treat adults before egg laying | A check (below); the page's advice |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's window: 1,475 (USPest's), 1,675 and 1,880 (no known source) | Replaced |

## Choices and differences

- **Degree days:** single sine above 41 °F from January 1, without USPest's 103 °F upper threshold, which isn't a stored total and doesn't bind here: on the archive's daily highs and lows a 103 °F cap changed no season's total at Arlington, Hancock or Rhinelander in 2016–2025 (`scripts/check_mint_flea_beetle.py`: a difference of 0.0 every year). So the stored 41 °F total is USPest's model on Wisconsin weather.
- **Egg hatch** (weight 0): PERT (380, 560, 980), 2 % at 416 (USPest's hatch begins at 405), half at 590, 99 % at 863. The spread is a judgment from the handbook's "early April through May", about 550 degree days in the Pacific Northwest.
- **Larval feeding** (a `DerivedStage`, weight 1): from hatch for 495 degree days, USPest's first hatch (405) to its first larvae leaving the rhizomes (900). Its first larvae leave at 911 and all by about 1,360, before the first adults.
- **Adult emergence** (weight 0): PERT (1,440, 1,650, 2,300), 2 % at 1,479 (USPest's 1,475), half at 1,706, 95 % at 2,001. The spread is a judgment from the handbook's "late June and July", about 900 degree days there. USPest's table stops at the first adults.
- **Adult feeding** (a `DerivedStage`, weight 1): 600 degree days after each adult emerges, about three to four weeks in July: two to three weeks of feeding before egg laying, and some while laying (the handbook; a judgment).
- **Action window:** "Sweep mint for adults", from 2 % to 95 % of emergence (1,479 to 2,001). A3422's thresholds are adults per 100 sweeps, and sprays go on after most adults are out and before egg laying begins two to three weeks later.
- **Training area:** USPest's model is from Pacific Northwest mint (Oregon, Washington, Idaho); Berry et al.'s years aren't in hand, so 1990–1997 is an estimate.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 387, the first egg hatch (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: April 27 at Madison, May 3 at Hancock, May 12 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) April 24. Where we don't have the normals it opens on April 15. It ends after August 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_specialty_insects.py`, run in CI:

- Egg hatch begins (2 %) at 416 degree days and the first larvae leave the rhizomes at 911, against the model's 405 and 900 (test: within 15); adult emergence begins (2 %) at 1,479, against its 1,475 (test: within 10).
- The model gives only when each stage begins, so the spread of each is our judgment; nothing tests the spreads.

### Against Wisconsin's guide

A3422 puts adult emergence in late July, at about 1,100 degree days above 40 °F in soil 6 inches deep. AgWeather's archive holds soil temperatures at 10 and 30 cm (ERA5-Land's layers); 6 inches (15 cm) is interpolated between them, and soil degree days are the daily average of the hourly minimum and maximum above 40 °F from January 1 (by degree hours instead, the dates move a day at most). `scripts/check_mint_flea_beetle.py`, 2016–2025:

<!-- prettier-ignore -->
| Place | 1,100 soil DD40 at 6 in reached | The model's first adults (1,475 DD41 in air) | Soil before air, days: median (range) |
| --- | --- | --- | --- |
| Arlington | June 7 to June 23 | June 17 to July 2 | 9 (6 to 12) |
| Hancock | June 13 to June 28 | June 23 to July 7 | 10.5 (6 to 14) |
| Rhinelander | June 26 to July 10 | June 30 to July 14 | 7.5 (2 to 10) |

On AgWeather's soil temperatures, 1,100 soil degree days came 2 to 14 days before the model's first adults (1,475 in air) at Arlington, Hancock and Rhinelander in 2016–2025, from early June to early July, not late July. So A3422's degree-day number and its late July disagree with each other, and the model's first adults (late June in the south, early July in the north) fall between them, weeks before the guide's late July. Where A3422's number came from isn't known (a soil depth, a start date or an older guide's count may differ), and ERA5-Land's soil temperatures are a model's, not measurements.

### On the normals

`scripts/specialty_insect_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (single sine 41 °F from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD41) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Hatch begins, 2 % (416) | May 8 | May 13 | May 20 |
| Larval feeding peak (882) | June 3 | June 7 | June 14 |
| First larvae leave rhizomes (911) | June 4 | June 8 | June 15 |
| Adults begin, 2 % (1,479) | June 25 | June 29 | July 8 |
| Adults half emerged (1,706) | July 3 | July 8 | July 17 |
| Adult feeding peak (2,053) | July 15 | July 20 | July 30 |
| Sweep window (1,479–2,001) | June 25 to July 13 | June 29 to July 18 | July 8 to July 28 |
| Normal total on October 15 | 4,307 | 4,018 | 3,530 |

The handbook's larvae feed until early June and its adults emerge in late June and July in the Pacific Northwest; the model puts them at about the same times in Wisconsin. A3422's late July is two to four weeks after the model's first adults; its adult feeding peak, mid- to late July, is nearer.

## Limits and open questions

- **Wisconsin's emergence:** A3422's late July against the model's late June to early July; A3422's own soil number points earlier still. Sweep counts in Wisconsin mint would settle it; none are known. Ben (2026-11-23) kept the model, with the doubt stated on its page ("Wisconsin's guide disagrees with itself and with the model", and the advice to sweep from late June into August) and on the topic page.
- **Every spread is a judgment:** USPest gives only the start of hatch, of larvae leaving and of emergence.
- **Air, not soil:** the larvae and pupae develop in the soil, which USPest's air degree days stand in for.
- **Developed in the Pacific Northwest**, partly validated; Berry et al.'s work isn't online.
- Mint is a small crop in Wisconsin; whether to keep the model was Ben's question 1 in part H's plan, and he kept it (2026-11-23, D103).

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_specialty_insects.py
uv run python scripts/check_mint_flea_beetle.py                   # soil against air on the archive; needs data/
uv run app/manage.py shell < scripts/specialty_insect_normals.py  # the dates on the normals
```
