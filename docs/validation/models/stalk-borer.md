# Stalk borer (`stalk-borer`): validation

Model version 0.2, written 2026-11-21 (D98; part H, batch H4), its sources read in full 2026-11-23. The model: `packages/agmodels/src/agmodels/insects/stalk_borer.py`, run by the insect engine (`agmodels.phenology`, D36); its page: `stalk_borer.md` beside it. Version 0.1 was VDIFN's window (1,110, 1,400, 1,700 degree days, single sine 41/86 °F from January 1), labelled as moth flight and checked only against VDIFN; this report replaces that one.

**In short:** one stage, caterpillars moving from grassy areas into corn, timed by degree days above 41 °F from January 1: first movement at about 1,100, 10 % at about 1,400 and half at about 1,650, as Lasack and Pedigo 1986 measured in Iowa in 1984 and 1985 (half at 1,627 and 1,586) and Iowa State's and UW–Madison's guides give them. A window from about 1,300 to 1,700 covers the guides' scouting and spraying. It hasn't been compared with observations in Wisconsin (stalk borer isn't in DATCP's traps).

## Sources and what we took from each

<!-- prettier-ignore -->
| Source | What it gives | What we took |
| --- | --- | --- |
| Lasack and Pedigo 1986 ([doi:10.1093/jee/79.6.1697](https://doi.org/10.1093/jee/79.6.1697)), read in full; Iowa | Two fields 6.5 km southwest of Baxter, central Iowa (a reduced-tillage field with smooth brome terraces and a no-till field with a waterway), 1984 and 1985 (pp. 1697–1698). Plant samples from the grassy areas and the first two or three corn rows, and linear pitfall traps in front of rows 1 and 2 (1984) or 1 and 3 (1985), emptied 2–3 times a week: 94 larvae trapped in 1984, 384 in 1985 (p. 1701). Degree days by Allen's (1976) sine above 5.1 °C (Levine 1983) from January 1, from the NOAA station at Newton, 11 km away (p. 1698). Moving larvae mostly fifth and sixth instars in 1984 (77.7 %), fourth and fifth in 1985 (77.6 %) (Fig. 5). Larvae first caught after 600 °C·d in both years; half caught after 904 °C·d (June 25) in 1984 and 881 (June 9) in 1985; movement after 1,100 °C·d probably within the field (p. 1702, Fig. 6). In 1985 the catches rose steeply from 600 °C·d to near their peak by about 720; in 1984 they peaked near 880–950 (Fig. 6). In °F·d: first 1,080, half 1,627 and 1,586, little after 1,980. Damage was heaviest in the first two rows; small larvae also hatched inside the field from eggs on giant foxtail and fed on seedling corn early (p. 1700) | The curve's start, middle (with the guides) and end (1,080, 1,586–1,627 and 1,980 °F·d); the training area (Iowa, 1984–1985) |
| Lasack, Bailey and Pedigo 1987 ([doi:10.1093/ee/16.1.296](https://doi.org/10.1093/ee/16.1.296)), read in full; the same fields | Logistic curves of each instar's development on °C·d (sine, 5.1 °C, from January 1; Table 2): half the larvae in the first instar at 403.7 (1984) and 341.1 (1985), both later than Levine's 256.8 for half hatched; fourth instar 730.4 and 667.3, fifth 820.3 and 831.4, sixth 1,015.2 and 1,028.5. A cool, wet April and May in 1984 against a warm, dry 1985; heavy rain at hatch cut 1984's numbers. Late instars, pupation and moth flight kept closer to the calendar than to degree days (seventh instars 6 days apart by date, 108 °C·d by degree days; p. 300); in 1985 the first moth came on August 12 (1,980 °C·d) and half the flight on September 14 (2,546), against Levine's 1,946.7. Most larvae died while moving between hosts (fourth to sixth instars; Table 3) | Background: the caveat that the move follows degree days only roughly |
| Rice and Davis 2010 ([doi:10.1603/IPM10006](https://doi.org/10.1603/IPM10006)) | Lasack and Pedigo's numbers as 1,110 and 1,650 FDD (base 41.2 °F; the paper's 600 and about 900 °C·d rounded); scout at 1,300–1,400, spray at 1,400–1,700 if needed; no upper threshold | The window |
| Iowa State, Stalk Borer (Table 2) | Base 41 °F from January 1: egg hatch 575–750; scouting from 1,300; 10 % larval movement 1,400; treatment decisions 1,400–1,700; 50 % (peak) 1,700. No upper threshold stated; no source given for the table | 10 % at 1,400 |
| UW–Madison, Pest Management in Wisconsin Field Crops (A3646, 2025), pp. 53–54 and 74 | Base 41 °F: scout border rows at 1,300–1,400; movement first at about 1,110 and peaking at about 1,650; treat between 1,400 and 1,700; check last year's weed patches from 900–1,000; thresholds by leaf stage (Table 2-8, adapted from Iowa State) | The window; checks |
| Levine 1983 ([doi:10.1093/aesa/76.5.892](https://doi.org/10.1093/aesa/76.5.892)), read in full; Illinois | Larvae collected at Cisco and Maroa in June 1981, eggs laid in a screenhouse at Champaign and reared at five constant temperatures, 12.8–23.9 °C, from March 3, 1982 (Table 1). Thresholds for half the individuals (Table 2): egg 8.4 °C (182.6 °C·d), larva 3.7 (1,397.2), pupa 6.1 (404.0), egg to adult 5.1 (41.2 °F; 1,946.7); on the 5.1 °C threshold, half hatched at 256.8 °C·d (462 °F·d), half pupated at 1,508.0 and half the moths out at 1,946.7. Degree days by Allen's (1976) sine (his Table 1, equation 7) from January 1, no upper (p. 894). Checks in 1982 (Table 3): screenhouse eggs half hatched on May 5 (281.9 °C·d observed against 256.8 predicted, a day apart); half the moths caught at a Lanark, Illinois, black light by September 19 (2,038.2), against September 12 predicted. One generation | The method |
| Allen 1976 ([doi:10.1093/ee/5.3.388](https://doi.org/10.1093/ee/5.3.388)), read in full; Lake Alfred, Florida | A FORTRAN subroutine (DDAY) for degree days between a lower and an upper threshold from the daily maximum and minimum, fitting a sine to each half day: the first half from the day's minimum to its maximum, the second from the maximum to the next day's minimum (Table 1's equations 1–16 for the six ways a half day's curve can sit against the thresholds; equation 7 the area above the lower threshold when the curve crosses it). Compared with planimeter readings of thermograph charts from Alaska, Arizona, Florida and Michigan, with an optional linear correction for local bias (equations 3–6; Appendix I includes Florida's, Appendix II has none) | The method's identity: a double sine (below) |
| VDIFN | 41/86 °F; (1,110, 1,400, 1,700) labelled "adult flight" | Replaced |

## Choices and differences

- **Degree days:** single sine above 41 °F, no upper threshold, from January 1 (Levine's 5.1 °C, 41.2 °F, as Lasack and Pedigo and the guides use it; 41 °F adds a few degree days by late June). None of the sources uses an upper threshold. VDIFN's 86 °F cutoff changes the normal total by July 15 by 1–3 degree days (Arlington 3.1, Hancock 2.8, Rhinelander 1.3). Levine cites Allen's Table 1, equation 7 (p. 894), and Lasack and Pedigo "the sine wave method (Allen 1976)". Equation 7 is Allen's area above the lower threshold for a half day whose sine crosses it, 1/(2π)·[(T − k₁)(π/2 − θ) + α cos θ] with θ = arcsin((k₁ − T)/α), T and α the half day's mean and half range. Allen's method (his subroutine DDAY) applies it to the day's two halves, the first with the day's minimum and the second with the next day's minimum: a double sine. Applied to both halves with the same minimum, the two halves are equal and their sum is the single sine, exactly what `agmodels.degree_days.degree_days_sine` computes (its formula is twice equation 7). Levine says only that he used daily maximum and minimum temperatures with equation 7, and Lasack and Pedigo only "the sine wave method", so which minimum they took for the second half isn't stated; Allen's published method would be the double sine. The difference is small: on AgWeather's daily temperatures at Arlington, Hancock and Rhinelander in 2016–2025 (27 place-years; 2020 left out for a missing day), the double sine above 41 °F gives 2.5 to 9.0 degree days more than the single sine by the day the single sine reaches 1,650, and reaches 1,650 the same day or one day sooner. The model keeps the single sine (no change proposed); Allen's bias correction (his equations 3–6, fitted to Florida, Arizona, Michigan and Alaska) isn't part of either paper's method as described.
- **One stage:** "Caterpillars moving into corn", a PERT curve (1,100, 1,670, 2,100), weight 1: 10, 50 and 99 % at 1,390, 1,652 and 2,018. The middle sits a little after Lasack and Pedigo's 1,586 and 1,627 (1,650 in A3646 and Rice and Davis) and before Iowa State's 1,700. One generation a year; the moths fly from August to October, after the season this models.
- **Window:** "Scout corn borders and treat if needed" from 3 % moved to 60 %, 1,292 to 1,704 degree days: the guides' scouting from 1,300 and spray window 1,400–1,700. Sprays work only while caterpillars are moving, before they bore in.
- **Against VDIFN:** VDIFN's labels called these numbers moth flight; they are caterpillar movement. Its peak at 1,400 was the start of the spray window, not the peak of movement.
- **Season (D128):** its season opens at each place about a week before the area's 30-year normal degree days (its own method, from January 1) reach 1,187, the first caterpillars moving into corn (where a stage's activity first reaches 5 % of its first-generation peak), averaged over about 50 km: June 6 at Madison, June 11 at Hancock, June 21 at Rhinelander on the development archive's normals, and over Wisconsin's farmland (the 10th percentile of its cultivated cells) June 2. Where we don't have the normals it opens on May 15. It ends after August 31 whatever the weather.

## Checks

### Against its sources' numbers

`packages/agmodels/tests/test_stalk_borer.py`, run in CI:

- The curve starts at 1,100 (Lasack and Pedigo's first catch, 600 °C·d, 1,080 °F·d; A3646's 1,110).
- 10 % have moved at 1,390 degree days, against Iowa State's 1,400.
- Half at 1,652, against Lasack and Pedigo's 1,627 and 1,586 in their two years (904 and 881 °C·d; 1,650 in UW–Madison's guide and Rice and Davis) and Iowa State's 1,700.
- 99 % at 2,018, against little movement after 1,100 °C·d (1,980 °F·d).
- The window runs from 1,292 to 1,704 degree days, as the guides' 1,300 to 1,700.
- The model hasn't been compared with observations in Wisconsin: stalk borer isn't counted in DATCP's traps, and no Wisconsin records of movement are known to us.

### Normal dates

On AgWeather's 1996–2025 normals (`/api/v2/climate/normals`, single sine 41 °F without an upper threshold, from January 1):

<!-- prettier-ignore -->
| Event (°F·d from January 1) | Arlington | Hancock | Rhinelander |
| --- | --- | --- | --- |
| Window opens: scout border rows (1,292) | June 19 | June 23 | July 1 |
| 10 % moved (1,390) | June 22 | June 26 | July 5 |
| Half moved (1,652) | July 1 | July 6 | July 15 |
| Window closes (1,704) | July 3 | July 8 | July 17 |
| 90 % moved (1,895) | July 9 | July 14 | July 24 |

Version 0.1 (41/86 °F) reached 1,110, 1,400 and 1,700 around June 12, June 23 and July 3 at Arlington. A3646 gives no dates; the topic page puts 1,110 around June 12 at Arlington and 1,650 around July 1.

## Limits and open questions

- **The early part of the move:** Iowa State's 10 % at 1,400 (778 °C·d) has no stated source. Lasack and Pedigo's figure of weekly trap catches (Fig. 6) shows 1985's catches rising steeply from 600 °C·d to near their peak by about 720 (1,296 °F·d), so that year a good share had moved before 1,400; 1984's came later. The model's 10 % follows Iowa State; the paper gives no 10 % point to set against it, and its two years differ by about as much.
- **Degree days only roughly time the move:** Lasack, Bailey and Pedigo 1987 found the first instars later than Levine's hatch (half at 404 °C·d in a cool, wet 1984 and 341 in a warm, dry 1985, against his 256.8 for half hatched), and the late instars, pupation and moth flight closer to the calendar than to degree days. Two years in one place.
- Caterpillars from last year's weed patches inside a field start feeding on corn earlier (A3646: check those patches from 900–1,000); the model times movement from field edges.
- No Wisconsin observations.

## Reproducing

```bash
uv run pytest packages/agmodels/tests/test_stalk_borer.py
# The normal dates: /api/v2/climate/normals?dd=sine_41 at each place (Arlington 43.30, −89.35; Hancock 44.12, −89.53;
# Rhinelander 45.64, −89.41) through Django's test client in `uv run app/manage.py shell`, read off at each total
```
