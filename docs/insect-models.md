# Insect model review

The work list for PLAN.md Phase 3 D8 step 4: moving each insect from its legacy definition (a VDIFN generation table or a Crop Risk Tool stage table) to life-stage curves (D36), using the degree-day method its source used (D37). Seedcorn maggot is done and is the worked example. Last updated 2026-10-29.

## How each insect is reviewed

1. **Find the source** of the current numbers, and any newer or more local work. Put PDFs in `tmp/references/insects/<insect-id>/`.
2. **Check the method:** the lower and upper thresholds, the calculation (single sine, simple average, modified average), where the upper threshold applies, the biofix, and whether the numbers came from air or soil temperatures. VDIFN computed every insect with single sine 39.2/86 °F or similar, whatever its source used. Single sine runs about 70–100 FDD ahead of the average method by May (Eau Claire, 2025).
3. **Rebuild** each life stage's start, peak and end from the source's numbers (first emergence, 10/50/90%, peak flight). Set the generation interval from the source's adult-to-adult time. A stage with a known lag and duration is a `DerivedStage`. Add the action windows.
4. **Record it:** citations with DOIs, checked by `test_citations --network`; a version bump and a changelog line; the intended differences in PLAN.md; drafts of the model page and topic page.

**Status:** ✅ done · 🔎 source found (PDF needed) · ❓ source not identified yet.

## Summary

| Insect                               | Current (all single sine)          | Likely source                                                   | Source's method                                                        | Status           |
| ------------------------------------ | ---------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------- |
| Seedcorn maggot                      | Average 39/84.2 °F, Jan 1 (2.0)    | Sanborn et al. 1982; Funderburk et al. 1984                     | Average, 3.9 °C, 29 °C cap                                             | ✅               |
| Alfalfa weevil                       | 48.2/86, Jan 1, CRT stage table    | Litsinger & Apple 1973 (WI); Whitford & Quisenberry 1990        | 48 °F max-min (Whitford)                                               | 🔎               |
| Aphid PVY vectors                    | 39.2/86, Jan 1, (1838, 2515, 3228) | Probably UW suction-trap data (Groves lab)                      | ?                                                                      | ❓ Ben           |
| Black cutworm                        | 50/86, May 15, (300, 700, 1000)    | Luckmann et al. 1976; Story et al. 1984                         | Sine, 10.4 °C (50.7 °F), biofix moth capture                           | 🔎               |
| Cabbage looper                       | 50/90, May 15, 2 gens 790 apart    | Toba et al. 1973                                                | 50/90 °F lab; egg to adult 791.5 FDD                                   | 🔎               |
| Cabbage maggot                       | 42.8/86, Jan 1, 2 gens             | Eckenrode & Chapman 1971, 1972 (WI)                             | **Modified max-min**, 43 °F; first emergence 300, adult to adult 1,176 | 🔎               |
| Colorado potato beetle (CRT)         | 50/86, Jan 1, stage table          | CRT: 10 years of Central Sands scouting data; Ferro et al. 1985 | 10 °C                                                                  | 🔎 + Ben         |
| CPB adults / larvae (VDIFN)          | 50/86, Jan 1                       | Ferro et al. 1985                                               | 10 °C lab                                                              | 🔎               |
| Common asparagus beetle              | 50, Jan 1, (105, 250, 405)         | Taylor & Harcourt 1978                                          | lab rates                                                              | 🔎               |
| Corn earworm                         | 55/92, Aug 1, (70, 275, 440)       | Butler 1976? (H. zea development)                               | ?                                                                      | ❓               |
| Corn rootworm                        | 52/none, Jan 1, (329, 472, 636)    | Jackson & Elliott 1988? (WCR immatures)                         | ? (often soil DD)                                                      | ❓               |
| Crucifer flea beetle                 | 50/none, Jan 1, 2 gens             | Ulmer & Dosdall 2006                                            | ?                                                                      | 🔎               |
| European corn borer                  | 50/86, Jan 1, 2 gens               | Matteson & Decker 1965; Anderson et al. 1982                    | lab; spring emergence model                                            | 🔎               |
| Imported cabbageworm                 | 50/none, Jan 1, 2 gens             | ?                                                               | ?                                                                      | ❓               |
| Japanese beetle                      | 50/none, Jan 1, (970, 1600, 2150)  | Régnière et al. 1981                                            | development model (NC)                                                 | 🔎               |
| Mint flea beetle                     | 41/none, Jan 1, (1475, 1675, 1880) | Probably Oregon State mint IPM                                  | ?                                                                      | ❓               |
| Mint root borer                      | 50/none, Apr 1, (430, 1280, 2150)  | Tollerup et al. 2013 (CA); Oregon State                         | ?                                                                      | 🔎               |
| Onion maggot                         | 39.2/86, Jan 1, 2 gens             | Eckenrode et al. 1975 (NY); Liu et al. 1982 (ON)                | Sine 4.4 °C (39.9 °F) (Liu)                                            | 🔎               |
| Spotted wing drosophila              | 45/86, Jan 1, (1276, 3180, 4000)   | Kamiyama et al. 2020 (Midwest); Tochen et al. 2014              | see paper                                                              | 🔎 (open access) |
| Squash vine borer                    | 50/none, Jan 1, (750, 900, 1000)   | Extension (UMN?)                                                | ?                                                                      | ❓               |
| Stalk borer                          | 41/86, Jan 1, (1110, 1400, 1700)   | Levine 1983; Davis & Pedigo 1990                                | 5 °C                                                                   | 🔎               |
| Tarnished plant bug                  | 52/none, Jan 1, (275, 1000, 2000)  | Fleischer & Gaylor 1988                                         | ? (UC IPM's Lygus: 54 °F sine)                                         | 🔎               |
| Variegated cutworm                   | 45/80.1, May 1, (900, 1450, 2100)  | Simonet et al. 1981 (via UC IPM)                                | 45/80.1 °F; first flight 900, adult to adult 1,260                     | 🔎               |
| Western bean cutworm                 | 50/none, May 1, (1320, 1420, 1535) | Hanson et al. 2015                                              | see paper (25/50/75% flight)                                           | 🔎               |
| Western flower thrips                | 45/none, Jan 1, 4 gens 670 apart   | ? (McDonald et al. 1997 is cold tolerance)                      | ? (often 9–10 °C)                                                      | ❓               |
| Oak wilt vectors (`models/oak_wilt`) | 41 °F, Jan 1                       | Jagemann et al. 2018 (cited)                                    | check                                                                  | 🔎 method only   |

## Papers to find

Ordered roughly by how many insects they unblock and how far the current model may be off. DOIs checked against Crossref.

**Wisconsin sources (most likely to match the current numbers):**

- Eckenrode, C. J. and Chapman, R. K. (1972). Seasonal adult cabbage maggot populations in the field in relation to thermal-unit accumulations. _Annals of the Entomological Society of America_ 65, 151–156. [10.1093/aesa/65.1.151](https://doi.org/10.1093/aesa/65.1.151)
- Eckenrode, C. J. and Chapman, R. K. (1971). Effect of various temperatures upon rate of development of the cabbage maggot under artificial conditions. _Annals of the Entomological Society of America_ 64, 1079–1083. [10.1093/aesa/64.5.1079](https://doi.org/10.1093/aesa/64.5.1079)
- Litsinger, J. A. and Apple, J. W. (1973). Thermal requirements for embryonic and larval development of the alfalfa weevil in Wisconsin. _Journal of Economic Entomology_ 66, 309–311. [10.1093/jee/66.2.309](https://doi.org/10.1093/jee/66.2.309)
- Kamiyama, M. T., Bradford, B. Z., Groves, R. L. and Guédot, C. (2020). Degree day models to forecast the seasonal phenology of _Drosophila suzukii_ in tart cherry orchards in the Midwest. _PLOS ONE_ 15, e0227726. [10.1371/journal.pone.0227726](https://doi.org/10.1371/journal.pone.0227726) (open access)
- Strong, F. E. and Apple, J. W. (1958). Studies on the thermal constants and seasonal occurrence of the seedcorn maggot in Wisconsin. _Journal of Economic Entomology_ 51, 704–707. (Background for seedcorn maggot; DOI not checked.)

**Midwest field and lab sources:**

- Luckmann, W. H., Shaw, J. T., Sherrod, D. W. and Ruesink, W. G. (1976). Developmental rate of the black cutworm. _Journal of Economic Entomology_ 69, 386–388. [10.1093/jee/69.3.386](https://doi.org/10.1093/jee/69.3.386)
- Story, R. N., Keaster, A. J., Showers, W. B. and Shaw, J. T. (1984). Survey and phenology of cutworms (Lepidoptera: Noctuidae) infesting field corn in the Midwest. _Journal of Economic Entomology_ 77, 491–494. [10.1093/jee/77.2.491](https://doi.org/10.1093/jee/77.2.491)
- Kaster, L. V. and Showers, W. B. (1984). Modeling black cutworm (Lepidoptera: Noctuidae) field development in Iowa. _Environmental Entomology_ 13, 384–389. [10.1093/ee/13.2.384](https://doi.org/10.1093/ee/13.2.384)
- Matteson, J. W. and Decker, G. C. (1965). Development of the European corn borer at controlled constant and variable temperatures. _Journal of Economic Entomology_ 58, 344–349. [10.1093/jee/58.2.344](https://doi.org/10.1093/jee/58.2.344)
- Anderson, T. E., Kennedy, G. G. and Stinner, R. E. (1982). Temperature-dependent model for postdiapause development and spring emergence of the European corn borer. _Environmental Entomology_ 11, 1307–1311. [10.1093/ee/11.6.1307](https://doi.org/10.1093/ee/11.6.1307)
- Hanson, A. A., Moon, R. D., Wright, R. J., Hunt, T. E. et al. (2015). Degree-day prediction models for the flight phenology of western bean cutworm (Lepidoptera: Noctuidae) assessed with the concordance correlation coefficient. _Journal of Economic Entomology_ 108, 1728–1738. [10.1093/jee/tov110](https://doi.org/10.1093/jee/tov110)
- Levine, E. (1983). Temperature requirements for development of the stalk borer, _Papaipema nebris_. _Annals of the Entomological Society of America_ 76, 892–895. [10.1093/aesa/76.5.892](https://doi.org/10.1093/aesa/76.5.892)
- Davis, P. M. and Pedigo, L. P. (1990). Evaluation of two management strategies for stalk borer, _Papaipema nebris_, in corn. _Crop Protection_ 9, 387–391. [10.1016/0261-2194(90)90013-W](<https://doi.org/10.1016/0261-2194(90)90013-W>)
- Jackson, J. J. and Elliott, N. C. (1988). Temperature-dependent development of immature stages of the western corn rootworm, _Diabrotica virgifera virgifera_. _Environmental Entomology_ 17, 166–171. [10.1093/ee/17.2.166](https://doi.org/10.1093/ee/17.2.166)
- Fleischer, S. J. and Gaylor, M. J. (1988). _Lygus lineolaris_ population dynamics: nymphal development, life tables, and Leslie matrices on selected weeds and cotton. _Environmental Entomology_ 17, 246–253. [10.1093/ee/17.2.246](https://doi.org/10.1093/ee/17.2.246)

**Lab development studies (thresholds and stage durations):**

- Ferro, D. N., Logan, J. A., Voss, R. H. and Elkinton, J. S. (1985). Colorado potato beetle temperature-dependent growth and feeding rates. _Environmental Entomology_ 14, 343–348. [10.1093/ee/14.3.343](https://doi.org/10.1093/ee/14.3.343)
- Toba, H. H., Kishaba, A. N., Pangaldan, R. and Vail, P. V. (1973). Temperature and the development of the cabbage looper. _Annals of the Entomological Society of America_ 66, 965–974. [10.1093/aesa/66.5.965](https://doi.org/10.1093/aesa/66.5.965)
- Simonet, D. E., Clement, S. L., Rubink, W. L. and Rings, R. W. (1981). Temperature requirements for development and oviposition of _Peridroma saucia_. _The Canadian Entomologist_ 113, 891–897. [10.4039/Ent113891-10](https://doi.org/10.4039/Ent113891-10)
- Taylor, R. G. and Harcourt, D. G. (1978). Effects of temperature on developmental rate of the immature stages of _Crioceris asparagi_. _The Canadian Entomologist_ 110, 57–62. [10.4039/Ent11057-1](https://doi.org/10.4039/Ent11057-1)
- Guppy, J. C. and Mukerji, M. K. (1974). Effects of temperature on developmental rate of the immature stages of the alfalfa weevil, _Hypera postica_. _The Canadian Entomologist_ 106, 93–100. [10.4039/Ent10693-1](https://doi.org/10.4039/Ent10693-1)
- Whitford, F. and Quisenberry, S. S. (1990). Population dynamics and seasonal biology of the alfalfa weevil on alfalfa in Louisiana. _Environmental Entomology_ 19, 1443–1451. [10.1093/ee/19.5.1443](https://doi.org/10.1093/ee/19.5.1443)
- Régnière, J., Rabb, R. L. and Stinner, R. E. (1981). _Popillia japonica_: simulation of temperature-dependent development of the immatures, and prediction of adult emergence. _Environmental Entomology_ 10, 290–296. [10.1093/ee/10.3.290](https://doi.org/10.1093/ee/10.3.290)
- Tochen, S., Dalton, D. T., Wiman, N., Hamm, C. et al. (2014). Temperature-related development and population parameters for _Drosophila suzukii_ on cherry and blueberry. _Environmental Entomology_ 43, 501–510. [10.1603/EN13200](https://doi.org/10.1603/EN13200)
- Butler, G. D., Jr. (1976). Bollworm: development in relation to temperature and larval food. _Environmental Entomology_ 5, 520–522. [10.1093/ee/5.3.520](https://doi.org/10.1093/ee/5.3.520) (a guess for corn earworm)

**Onion maggot, flea beetles and mint:**

- Eckenrode, C. J., Vea, E. V. and Stone, K. W. (1975). Population trends of onion maggots correlated with air thermal unit accumulations. _Environmental Entomology_ 4, 785–789. [10.1093/ee/4.5.785](https://doi.org/10.1093/ee/4.5.785)
- Liu, H. J., McEwen, F. L. and Ritcey, G. (1982). Forecasting events in the life cycle of the onion maggot, _Hylemya antiqua_: application to control schemes. _Environmental Entomology_ 11, 751–755. [10.1093/ee/11.3.751](https://doi.org/10.1093/ee/11.3.751)
- Ulmer, B. J. and Dosdall, L. M. (2006). Emergence of overwintered and new generation adults of the crucifer flea beetle, _Phyllotreta cruciferae_. _Crop Protection_ 25, 23–30. [10.1016/j.cropro.2005.03.003](https://doi.org/10.1016/j.cropro.2005.03.003)
- Tollerup, K. E., Marcum, D., Wilson, R. and Godfrey, L. (2013). Biology of mint root borer and control options on California peppermint. _Journal of Integrated Pest Management_ 4, 1–4. [10.1603/IPM13004](https://doi.org/10.1603/IPM13004) (open access)

**Not identified yet (Ben, or a wider search):**

- **Aphid PVY vectors:** (1838, 2515, 3228) from January 1 at 39.2 °F looks like a fit to suction-trap captures, perhaps the UW network. Where did it come from? Candidates for comparison: Mondal et al. 2016, _Environmental Entomology_ 45, 1445–1462 ([10.1093/ee/nvw131](https://doi.org/10.1093/ee/nvw131)); Yoho et al. 2026, _Journal of Economic Entomology_ ([10.1093/jee/toag257](https://doi.org/10.1093/jee/toag257)).
- **Corn earworm:** 55/92 °F from August 1, which looks like a migratory-flight biofix.
- **Corn rootworm:** 52 °F with no upper, (329, 472, 636). Egg hatch is usually given in soil degree days.
- **Imported cabbageworm, squash vine borer, mint flea beetle, western flower thrips:** no development study found yet. The mint pests are probably from Oregon State's mint IPM work.
- **Colorado potato beetle (Crop Risk Tool):** the stage table is a fit to 10 years of Central Sands scouting data. Is that data, or a write-up of it, available?

## Notes by insect

- **Cabbage maggot:** the Wisconsin source uses the **modified max-min** method at 43 °F. It puts first spring emergence at 300 FDD and adult to adult at 1,176 FDD. VDIFN's second generation starts 1,521 after its first, so its interval is longer than the source's.
- **Cabbage looper:** VDIFN's thresholds (50/90) and generation spacing (790) match Toba et al.'s egg-to-adult time (791.5 FDD). Its biofix (May 15) needs a source, since loopers migrate north.
- **Black cutworm:** the sources' threshold is 10.4 °C (50.7 °F), and the biofix should be a significant moth capture, not May 15. Story et al. found larvae in the field "far ahead" of lab-based predictions.
- **Variegated cutworm:** VDIFN's 900 is Simonet's first flight; the field adult-to-adult time is 1,260.
- **Onion maggot:** Liu et al. use single sine at 4.4 °C (39.9 °F), so this one may stay single sine.
- **Alfalfa weevil:** the Crop Risk Tool uses 48 °F, as Whitford and Quisenberry do (max-min). Litsinger and Apple is the Wisconsin study to check it against.
- **Spotted wing drosophila:** Kamiyama et al. 2020 is open access and from the UW group, so it should be the source to follow.
