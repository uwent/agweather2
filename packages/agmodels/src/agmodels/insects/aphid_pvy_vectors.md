---
id: aphid-pvy-vectors
status: draft
updated: 2026-11-19
summary: Estimates the risk of potato virus Y spread by winged aphids through the season from degree days, using a curve fitted to Wisconsin's suction trap catches.
sources:
  - Bradford and Groves, unpublished analysis of Wisconsin suction trap catches, 2016–2023 (UW–Madison Vegetable Entomology), refitted 2026
  - Suction trap aphid records via EDDMapS (Doris Lagos-Kutz, University of Illinois Urbana-Champaign)
  - VDIFN's PVY vector model (compared)
  - UW–Madison Vegetable Entomology, Potato Virus Y Management (https://vegento.russell.wisc.edu/resources/potato-virus-y-management/)
---

## What it predicts

Potato virus Y (PVY) is spread from plant to plant by winged aphids probing leaves as they move through a field, mostly by species that don't colonize potato, such as the soybean aphid. The model estimates how much PVY-spreading aphid flight a typical Wisconsin season has at each point, as a share of the season's peak. It shows typical pressure for the time of the season and when the flight usually begins; it doesn't forecast when this year's flight will peak.

## How it works

Degree days are counted from January 1 by the single-sine method, base 39.2 °F (4 °C) with a cutoff at 86 °F. The curve comes from Wisconsin's suction traps from 2016 to 2023. Each week's catch was scored by how many of each aphid species were caught and how well that species transmits PVY, and a smooth curve was fitted to those scores by degree days, allowing for differences between years and traps.

- Risk is already Moderate by about 730 degree days (late May in southern Wisconsin, early June in the north), holds near 40 % of the peak through early summer, and turns High at about 2,240 (mid-July in the south, about August 1 near Antigo).
- It stays near its peak from about 2,980 to 3,990 degree days, peaking near 3,580: late August in southern Wisconsin and late September in the northern seed areas, so in the north risk is still rising through the season.
- Before about 290 degree days the traps have no data, and the model shows no risk.

## How to read it

- Risk levels compare the day's value with the season's peak. Very high means aphid vector flight is usually near its peak at this point in the season.
- The model's early-season rise is its most useful signal: in tests on years left out of the fit, degree days timed the start of the season's catch about two days better than the calendar alone. Later in the season they did no better than the calendar, since most of these aphids fly in from elsewhere, on weather far from your field. Read midsummer and late-season levels as typical pressure for the time of year.
- Seasons differ widely: in single years the peak has come anywhere from about 1,700 to 4,800 degree days. Current trap catches are the better guide when they're available.

## What it means for seed potato production

Seed growers manage two kinds of aphids all season (UW–Madison Vegetable Entomology):

- **Colonizing aphids**, such as the green peach aphid, settle and reproduce on potato. After the early-season protection of a neonicotinoid seed or at-plant treatment wears off, scout weekly for small colonies of wingless aphids and treat with systemic foliar aphicides when they appear, rotating modes of action.
- **Non-colonizing aphids**, such as the soybean aphid, spread most PVY but only pass through the field, and systemic insecticides don't stop them from transmitting the virus. Paraffinic oils, which interfere with transmission, are applied weekly through the season from about two weeks after full emergence.

The model shows when vector pressure builds. As risk rises toward High, increase the frequency of aphicide and oil sprays, and keep coverage up through the season. In the north, risk is still rising when the season ends, so killing vines early, before the late-season surge of aphids, is one of the most effective ways to keep PVY out of a seed lot.

## Validation and caveats

- Draft (model version 0.2, beta). The curve describes the trap catches it was fitted to. Refitted with each year or each trap left out, it timed a held-out season's catch about as well as the calendar date did, except at the start, where it did about two days better; a single season was often two weeks or more off the typical timing. Base temperatures from 32 to 43 °F (0 to 6 °C) fitted the catches equally well, so the model keeps 39.2 °F.
- The trap records include weeks with aphids but not weeks with none, so the start and end of the season may show more risk than they should.
- VDIFN's version of this model put the peak at 2,515 degree days and ended at 3,228, before the actual peak; this version corrects that.
