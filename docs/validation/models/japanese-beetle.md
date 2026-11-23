# Japanese beetle (`japanese-beetle`): validation

Model version 0.2, written 2026-11-21 (D98; part H, H5); Régnière et al. 1981 read in full 2026-11-23. The model: `packages/agmodels/src/agmodels/insects/japanese_beetle.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `japanese_beetle.md` beside it. Version 0.1 was VDIFN's window (970, 1,600, 2,150 degree days, single sine 50 °F without an upper threshold), which turns out to be the first version of USPest's model; this version moves to USPest's second version (2024) as a D36 curve.

**In short:** Oregon State's Japanese beetle model (USPest `jpb`, Coop and Barker 2024) as one curve of adult beetles: single sine 50/92 °F from January 1, through USPest's 10, 50, 90 and 94 % of beetles trapped (1,100, 1,540, 1,985, 2,110), the means of about 14 site-years of trap catches at five Minnesota sites. The curve follows those points within 1.1 percentage points. On Wisconsin's weather the 92 °F cap moves the dates by a day at most. Against 2,818 iNaturalist records of adults in Wisconsin, the curve's 10 % and 50 % are within about 55 degree days (2 days) of the records', and the records run later in the tail, as records of beetles still feeding would.

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Coop and Barker 2024, USPest's Japanese beetle model version 2 ([PDF](https://uspest.org/wea/japanese_beetle_model.pdf), 23 pages, read 2026-11-21) | Single sine, 50/92 °F (10/33.3 °C), from January 1 (p. 1). Events (p. 1): pupation begins 650; place traps 920; 2 % adults 1,000; 10 % 1,100; 50 % 1,540 (first egg hatch); 90 % 1,985; 94 % 2,110 (end of main activity); last adults trapped 2,700. They are the rounded means of about 14 site-years of adult trap catches at five Minnesota sites (the means come out exactly with 14 rows; Rosemount, Forest Lake, Hastings and the Landscape Arboretum 2019–2021, Ebbenga et al. 2022; a fourth site 1994–1997, Wawrzynski and Ascerno 1998): 2 % 1,027, 10 % 1,128, 50 % 1,540, 90 % 1,985, 94 % 2,108, last 2,534 (p. 15). The 2 % was lowered "to be conservative" and the last adults raised for southern places (p. 16). Version 1 was 970 (first), 1,050 (10 %), 1,600 (peak), 2,080 (90 %), 2,150 (end of main activity), 2,790 (last) (p. 16). Validation on daily trap catches at Waltham, Massachusetts, 1983–1984 (Vittum 1986's site; not used to build it): 2 % a day early, 10 % 4 days early, 50 % half a day early, 90 % 3 days late, 94 % 3.5 days late (p. 8). 92 °F is near the optimum in Ludwig 1928's development rates (p. 4) | The method, the curve's four shares, the window's ends, the training area |
| VDIFN (`../ag-vdifn/db/seeds.rb`) | Version 0.1's window: 970, 1,600 and 2,150, base 50 °F without an upper threshold | Replaced. Its three numbers are USPest's version 1 (first adults, peak, end of main activity), whose source wasn't documented in VDIFN |
| Ebbenga et al. 2022 ([doi:10.3389/finsc.2022.1075807](https://doi.org/10.3389/finsc.2022.1075807)) | Pheromone trap catches at three Minnesota sites, 2019–2021; their own model, a simple average with substitutions at 59/71 °F from January 1: 10 % at 463, 50 % at 623, 90 % at 837 | Their trap data, through USPest's analysis; their model compared only (USPest found it 7.5–9 days late on the Massachusetts data, p. 9) |
| Vittum 1986 ([doi:10.1093/jee/79.2.387](https://doi.org/10.1093/jee/79.2.387)) | Life history in eastern Massachusetts | USPest's pupation and egg-hatch events (not modeled) and the site of its validation data |
| Régnière, Rabb and Stinner 1981 ([doi:10.1093/ee/10.3.290](https://doi.org/10.1093/ee/10.3.290)), read in full; North Carolina | Nonlinear development rates (no degree days), simulated from soil temperatures at 10 cm and checked against adult emergence at Clayton and Raleigh, 1977–1979. Ludwig 1928's rates refitted with lower limits of 13 °C for eggs and the first two instars and 10 °C (50 °F) for pupae and overwintered third instars, and upper limits of 31–36 °C (34 °C, 93 °F, for overwintered grubs; Table 1). Overwintered third instars collected in March took 65.1 days to the callow adult at 22 °C, 45.3 at 26, 37.0 at 28 and 36.6 at 30 (Table 2); at 14 °C only 10 % had pupated after about 150 days and at 12 °C none reached the prepupa in 180 (p. 293). Callow adults stay in the soil about 7.25 days above 22 °C before emerging, 14.2 at 22 (Table 3). Soil moisture didn't change emergence in the laboratory; the simulation spread emergence more than the field showed (p. 294) | No numbers: no degree-day events. Background for USPest's 50 °F base (the grubs' and pupae's 10 °C) and 92 °F upper threshold (near the grubs' 34 °C) |
| UW–Madison: Wisconsin Horticulture (Williamson, Liesch and Pandian), UW Vegetable Entomology | First adults in late June or early July at about 1,000 degree days, 900–1,200 by the horticulture page's range; first adults in mid-June by Vegetable Entomology | Compared, below |
| iNaturalist (`tmp/inat-check/`, 2026-11-19) | 2,818 research-grade records of Japanese beetle in Wisconsin, 2016–2026, inside the grid, coordinates within 5 km | A field check, below |

## Choices and differences

- **Degree days:** single sine, 50 °F with a 92 °F upper threshold, from January 1 (USPest; stored as the 50 °F total less the 92 °F one). In 2016–2025 the cap took at most 2.7 degree days off a season's total at Arlington, Hancock or Rhinelander (Hancock, 2023) and under half a degree day in most years (the archive's daily highs and lows at each cell), so a day at most.
- **One stage, the adults:** USPest's percentages are of beetles caught in traps, and a day's catch is the beetles flying and feeding that day, so the curve stands for adult activity (the damage), not for emergence. PERT (722, 1,513, 2,503), fitted by least squares to the 10, 50, 90 and 94 % (9.9, 50.2, 89.1 and 95.0 % there). Its 2 % is at 921 and its 99 % at 2,275. Weight 1. One generation a year, so no generation time.
- **The 2 % point:** USPest's 1,000 is set below its data's mean (1,027) to warn early; the curve's 2 % comes earlier still, at 921, near USPest's "place traps" (920). At 1,000 the curve is at 4.7 %.
- **The last adults:** USPest's 2,700 is a last catch, raised above its data's mean (2,534) for longer southern seasons; the curve is done by about 2,500. Beetles caught after 2,300 are a few percent of the season.
- **Action window:** "Scout for beetles feeding", from 2 % (921) to 94 % (2,085, USPest's end of main activity, 2,110).
- **Against UW–Madison:** UW's guides time the first adults at about 1,000 degree days (base 50 °F; the horticulture page) or in mid-June (Vegetable Entomology). The curve's first beetles come in the last days of June in southern Wisconsin (below).

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_specialty_insects.py`, run in CI:

- The curve passes 10, 50, 90 and 94 % of the beetles at 1,102, 1,538, 2,001 and 2,085 degree days, against USPest's 1,100, 1,540, 1,985 and 2,110 (test: within 1.2 percentage points at each).
- Its first beetles (2 %) come at 921 degree days, earlier than USPest's 1,000 (test: 900 to 1,000); its last (99 %) at 2,275, before USPest's last adults at 2,700.
- The scouting window runs from 921 to 2,085.

### Against iNaturalist records in Wisconsin

`tmp/inat-check/` (2026-11-19; each record's degree days at its own grid cell and date, here recomputed on 50/92 °F, which changed no percentile by more than a degree day). 2,818 records, 2016–2026; raw percentiles (each record counts once):

<!-- prettier-ignore -->
| Share of records | 2 % | 5 % | 10 % | 25 % | 50 % | 75 % | 90 % | 95 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Records, DD50/92 | 875 | 967 | 1,048 | 1,223 | 1,487 | 1,855 | 2,255 | 2,435 |
| Our curve | 921 | 1,007 | 1,102 | 1,292 | 1,538 | 1,791 | 2,001 | 2,111 |

Half the records fell by 1,487 degree days and 10 % by 1,048, within about 50 degree days (2 days) of our 50 % and 10 %; the last tenth of the records ran later than our curve (90 % at 2,255 against 2,001), as records of beetles still feeding would: a record is a beetle seen, not one emerging, and the effort-corrected median (1,641) is later again. Degree days don't narrow the records' year-to-year spread (the 10 % point's SD 114 degree days, about 5 days, against 5.5 days by date). The model wasn't fitted to these records. Records of a conspicuous beetle in gardens lag emergence and follow abundance, so the leading edge and the median are the useful parts.

### On the normals

`scripts/specialty_insect_normals.py`: each event's day on AgWeather's 1996–2025 normal running total (single sine 50/92 °F from January 1). A typical-year calendar, not a forecast.

<!-- prettier-ignore -->
| Event (DD50/92) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| First beetles, 2 % (921) | June 29 | July 4 | July 13 |
| 10 % (1,102) | July 8 | July 13 | July 23 |
| Half, 50 % (1,538) | July 29 | August 4 | August 18 |
| 90 % (2,001) | August 20 | August 29 | September 26 |
| End of main activity, 94 % (2,085) | August 25 | September 4 | October 12 |
| Normal total on October 15 | 2,706 | 2,476 | 2,092 |

UW–Madison's horticulture page: first adults in late June or early July at about 1,000 degree days, adults into September. The model's first beetles come June 29 at Arlington and July 4 at Hancock, as UW's horticulture page says; UW Vegetable Entomology's mid-June is a week or two earlier than the model in the south. At Rhinelander fall freezes end the season before the last tenth of the beetles would fly.

## Limits and open questions

- **Developed in Minnesota** (the data behind USPest's numbers), checked by USPest in Massachusetts and here against Wisconsin's iNaturalist records; no Wisconsin trap counts are in hand.
- **UW Vegetable Entomology's mid-June** first adults is earlier than the model and the iNaturalist records (5 % at 967, early July at Arlington); the horticulture page and the records agree with the model.
- **Activity, not numbers:** the curve says where the season stands, not how many beetles there are; a dry summer can mean fewer the next year.
- **iNaturalist's check** is from the exploratory pull in `tmp/inat-check`; a citable GBIF download with a DOI is H0's to-do before the check is quoted publicly in more detail.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_specialty_insects.py
uv run app/manage.py shell < scripts/specialty_insect_normals.py  # the dates on the normals
```
