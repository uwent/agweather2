# Apple stages: ours against NEWA's, and against observed stages in Wisconsin

Written by `scripts/check_apple_stages.py`. Ours: degree days base 43 °F by Baskerville–Emin's single sine from January 1, NEWA's stage thresholds. NEWA: the same thresholds on its own sine (`scripts/newa_reference.py`), on the station's daily max and min (local clock). Observations: `docs/validation/data/wi-apple-stages/observations.csv`, against the model on the archive's days (CST) at each site's cell; the stage codes each observation can be in are in brackets (- before silver tip).

## Same weather: our sine against NEWA's, first day of each stage (ours − NEWA's, days)

103 station-seasons

| Stage | −2 | −1 | 0 | +1 | +2 |
| --- | --- | --- | --- | --- | --- |
| ST | 0 | 0 | 95 | 6 | 2 |
| GT | 0 | 0 | 97 | 6 | 0 |
| HIG | 1 | 0 | 100 | 2 | 0 |
| TC | 0 | 0 | 102 | 0 | 1 |
| P | 1 | 2 | 99 | 1 | 0 |
| B | 0 | 1 | 102 | 0 | 0 |
| PF | 0 | 1 | 100 | 2 | 0 |
| FS | 0 | 4 | 99 | 0 | 0 |

## Observed stages against the model at each site's cell (archive)

| Site | Date | Cultivars | Observed | DD43 | Model stage | Days off |
| --- | --- | --- | --- | --- | --- | --- |
| WMARS (Verona) | 2023-04-24 | Zestar, Paula Red* | already at pink (P) | 217 | TC | +11 |
| Sunrise Orchards (Gays Mills) | 2023-05-05 | orchard | blossoms beginning to open; very few are open today (P B) | 325 | P | 0 |
| Sunrise Orchards (Gays Mills) | 2023-05-09 | orchard | at 75% blossom, heading toward 100% (B) | 399 | B | 0 |
| Sunrise Orchards (Gays Mills) | 2023-05-11 | orchard | reached 100% blossom (B) | 445 | B | 0 |
| PARS (Sturgeon Bay) | 2023-05-18 | not stated | entering king bloom (P B) | 324 | P | 0 |
| WMARS (Verona) | 2024-04-11 | Zestar* | late tight cluster (TC) | 172 | HIG | +3 |
| WMARS (Verona) | 2024-04-11 | Honeycrisp* | transitioning from green tip to tight cluster (GT HIG TC) | 172 | HIG | 0 |
| WMARS (Verona) | 2024-04-11 | Liberty, Gala* | at green tip (photo: Liberty half inch green) (GT HIG) | 172 | HIG | 0 |
| PARS (Sturgeon Bay) | 2024-04-11 | early cultivars | at green tip (GT) | 90 | ST | +2 |
| PARS (Sturgeon Bay) | 2024-04-11 | later cultivars | at silver tip (ST) | 90 | ST | 0 |
| Sunrise Orchards (Gays Mills) | 2024-04-16 | orchard | haven't observed any apple blossoms open yet (- ST GT HIG TC P) | 288 | TC | 0 |
| Sunrise Orchards (Gays Mills) | 2024-04-25 | orchard | only a few blossoms have opened (P B) | 340 | P | 0 |
| WMARS (Verona) | 2024-04-25 | Zestar | at king bloom (B) | 294 | P | +4 |
| WMARS (Verona) | 2024-04-25 | Liberty, Gala* | at pink (P) | 294 | P | 0 |
| PARS (Sturgeon Bay) | 2024-04-25 | apple cultivars | at tight cluster (TC) | 166 | HIG | +4 |
| Sunrise Orchards (Gays Mills) | 2024-04-29 | orchard | 1/3 of the blossoms open (B) | 391 | B | 0 |
| Sunrise Orchards (Gays Mills) | 2024-04-30 | orchard | apple blossoms are at a delightful 75% peak (B) | 404 | B | 0 |
| Blue Roof Orchard (Belmont) | 2024-04-30 | earliest and late varieties | earliest varieties have started petal fall, while late varieties are just beginning to bloom (B PF) | 396 | B | 0 |
| PARS (Sturgeon Bay) | 2024-05-09 | by variety | apples range between pink and king bloom depending on the variety (P B) | 303 | P | 0 |
| Blue Roof Orchard (Belmont) | 2024-05-13 | most varieties | past petal fall (PF FS) | 613 | FS | 0 |
| PARS (Sturgeon Bay) | 2024-05-16 | by variety | most trees have entered bloom, between king and full depending on the variety (B) | 367 | B | 0 |
| WMARS (Verona) | 2025-04-10 | early cultivars* | reached the green tip stage (GT) | 137 | GT | 0 |
| WMARS (Verona) | 2025-04-10 | later cultivars* | reached silver tip (ST) | 137 | GT | -14 |
| Gwenyn Hill Farm (Delafield) | 2025-04-21 | apples | green tip (apples) (GT) | 204 | TC | -6 |
| Sunrise Orchards (Gays Mills) | 2025-04-21 | orchard | haven't seen any apple blossoms open just yet (- ST GT HIG TC P) | 251 | TC | 0 |
| WMARS (Verona) | 2025-04-24 | Zestar, Ida Red* | reached first pink (P) | 252 | TC | +4 |
| WMARS (Verona) | 2025-04-24 | Fuji, Honeycrisp, McIntosh* | ½ inch green to tight cluster stage (HIG TC) | 252 | TC | 0 |
| Sunrise Orchards (Gays Mills) | 2025-05-02 | orchard | apple blossoms are on the verge of opening (P) | 382 | B | -4 |
| Gwenyn Hill Farm (Delafield) | 2025-05-05 | apples | full pink (photo table: full pink to king bloom) (P B) | 345 | P | 0 |
| Sunrise Orchards (Gays Mills) | 2025-05-07 | orchard | apple blossoms are about 75% at peak (B) | 459 | PF | -1 |
| WMARS (Verona) | 2025-05-07 | Gala, McIntosh* | full bloom (B) | 394 | B | 0 |
| WMARS (Verona) | 2025-05-07 | Zestar* | early petal fall (B PF) | 394 | B | 0 |
| WMARS (Verona) | 2025-05-07 | Ida Red* | early petal fall (photo caption: full bloom) (B PF) | 394 | B | 0 |
| WMARS (Verona) | 2025-05-07 | Honeycrisp* | king bloom (B) | 394 | B | 0 |
| WMARS (Verona) | 2025-05-07 | Fuji* | popcorn (P) | 394 | B | -4 |
| PARS (Sturgeon Bay) | 2025-05-08 | Door County | Growth Stage: Green Tip to Tight Cluster (GT HIG TC) | 165 | GT | 0 |
| PARS (Sturgeon Bay) | 2025-05-14 | Door County | Growth Stage: Tight Cluster to Pink (TC P) | 246 | TC | 0 |
| WMARS (Verona) | 2025-05-16 | not stated | had a petal fall date of 5/16 (PF) | 575 | PF | 0 |
| PARS (Sturgeon Bay) | 2025-05-21 | by variety | Growth Stage: Late Pink to Full Bloom, depending on variety (P B) | 306 | P | 0 |
| PARS (Sturgeon Bay) | 2025-05-28 | by variety | Growth Stage: Full Bloom to Petal Fall, depending on variety (B PF) | 382 | B | 0 |
| PARS (Sturgeon Bay) | 2025-06-04 | Zestar | fruit 12-16mm (FS) | 496 | PF | +5 |
| PARS (Sturgeon Bay) | 2025-06-04 | Honeycrisp, Liberty | fruit 6-10mm (PF FS) | 496 | PF | 0 |
| PARS (Sturgeon Bay) | 2025-06-04 | Snow Sweet | fruit 4-8mm (PF FS) | 496 | PF | 0 |
| PARS (Sturgeon Bay) | 2025-06-05 | Door County | Growth Stage: Petal Fall (PF) | 515 | PF | 0 |
| WMARS (Verona) | 2026-04-22 | Zestar, Ida Red* | reached king bloom (B) | 361 | B | 0 |
| WMARS (Verona) | 2026-04-22 | Fuji, Honeycrisp, McIntosh* | tight cluster to early pink stage (TC P) | 361 | B | -1 |
| WMARS (Verona) | 2026-04-30 | most cultivars | Most cultivars in southern Wisconsin were at full bloom by April 30 (B) | 455 | PF | -1 |
| Warm Belly Farm (Fort Atkinson) | 2026-05-18 | most apple varieties | at petal fall, with fruitlet size between 5 and 10mm (PF) | 724 | FS | -7 |
| PARS (Sturgeon Bay) | 2026-05-20 | Zestar | King Bloom (B) | 303 | P | +5 |
| PARS (Sturgeon Bay) | 2026-05-20 | Honeycrisp, Liberty | Pink (P) | 303 | P | 0 |
| PARS (Sturgeon Bay) | 2026-05-20 | Snow Sweet | Early Pink (P) | 303 | P | 0 |
| WMARS (Verona) | 2026-05-20 | Zestar, Ida Red | fruit 10-12mm (FS) | 711 | FS | 0 |
| WMARS (Verona) | 2026-05-20 | Honeycrisp, McIntosh | fruit 6-8mm (PF FS) | 711 | FS | 0 |
| PARS (Sturgeon Bay) | 2026-06-03 | Zestar | Petal Fall (PF) | 524 | PF | 0 |
| PARS (Sturgeon Bay) | 2026-06-03 | Honeycrisp, Snow Sweet | Early Petal Fall (B PF) | 524 | PF | 0 |
| PARS (Sturgeon Bay) | 2026-06-03 | Liberty | fruit 4-6mm (PF FS) | 524 | PF | 0 |
| PARS (Sturgeon Bay) | 2026-06-11 | Door County | Growth Stage: Early fruit set (PF FS) | 713 | FS | 0 |

All: 57 observations: 41 inside the model's window, 46 within 3 days; model late on 8, early on 8; mean +0.0 days, median +0.0.

Early cultivars (rows naming Zestar, Paula Red, early cultivars): 12 observations: 5 inside the model's window, 7 within 3 days; model late on 7, early on 0; mean +2.8 days, median +2.5.

The rest: 45 observations: 36 inside the model's window, 39 within 3 days; model late on 1, early on 8; mean -0.8 days, median +0.0.

* "southern Wisconsin" in the source, taken as WMARS.
