---
id: aphid-pvy-vectors
status: draft
updated: 2026-11-18
summary: Estimates the risk of potato virus Y spread by winged aphids through the season from degree days, using a curve fitted to Wisconsin's suction trap catches.
sources:
  - Bradford and Groves, unpublished analysis of Wisconsin suction trap catches, 2016–2023 (UW–Madison Vegetable Entomology), refitted 2026
  - Suction trap aphid records via EDDMapS (Doris Lagos-Kutz, University of Illinois Urbana-Champaign)
  - VDIFN's PVY vector model (compared)
---

## What it predicts

Potato virus Y (PVY) is spread from plant to plant by winged aphids probing leaves as they move through a field, mostly by species that don't colonize potato, such as the soybean aphid. The model estimates how much PVY-spreading aphid flight a typical Wisconsin season has at each point, as a share of the season's peak.

## How it works

Degree days are counted from January 1 by the single-sine method, base 39.2 °F (4 °C) with a cutoff at 86 °F. The curve comes from Wisconsin's suction traps from 2016 to 2023. Each week's catch was scored by how many of each aphid species were caught and how well that species transmits PVY, and a smooth curve was fitted to those scores by degree days, allowing for differences between years and traps.

- Risk rises from early summer and stays near its peak from about 2,980 to 3,990 degree days, peaking near 3,580.
- It falls by half by about 4,980 degree days, but late-season flights still carry some risk.
- Before about 290 degree days the traps have no data, and the model shows no risk.

## How to read it

- Risk levels compare the day's value with the season's peak. Very high means aphid vector flight is near its typical peak.
- Seasons differ widely: in single years the peak has come anywhere from about 1,700 to 4,800 degree days. Current trap catches are the better guide when they're available.

## Validation and caveats

- Draft (model version 0.2, beta). The curve describes the trap catches it was fitted to and hasn't been tested on other years.
- The trap records include weeks with aphids but not weeks with none, so the start and end of the season may show more risk than they should.
- VDIFN's version of this model put the peak at 2,515 degree days and ended at 3,228, before the actual peak; this version corrects that.
