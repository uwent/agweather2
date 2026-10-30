# Shortwave against Wisconet's pyranometers

Generated 2026-10-30 by `scripts/compare_pyranometers.py` (PLAN.md Phase 2 H). Daily totals (MJ/m²), 2025-01-01 to 2026-10-27, at 80 Wisconet stations in the `wisconsin` box: v2 (HRRR's hourly means) at the station's cell and the old API's SSEC satellite insolation at the nearest 0.1° point, against the station's `daily_solar_radiation_mj_tot`. Station days outside 0–36 MJ/m² are left out. Bias and MAE in MJ/m²; ratio is of the totals over the same days.

## Which day a Wisconet stamp closes

Correlation of v2 with the stations, their days shifted (0 is the reading used: the day before the stamp).

| Shift (days) | r |
|---|---|
| -1 | 0.655 |
| +0 | 0.954 |
| +1 | 0.688 |

## Overall

| Source | days | bias | MAE | ratio | r |
|---|---|---|---|---|---|
| v2 (HRRR) | 47889 | +2.51 | 2.74 | 1.18 | 0.954 |
| old API (SSEC) | 47368 | -0.41 | 1.35 | 0.97 | 0.965 |
| Open-Meteo ncep_nbm_conus | 47350 | +1.99 | 2.31 | 1.15 | 0.957 |
| Open-Meteo ecmwf_ifs | 47889 | +1.82 | 2.14 | 1.13 | 0.955 |
| Open-Meteo best_match | 47889 | +2.81 | 2.98 | 1.21 | 0.944 |

Open-Meteo is its historical-forecast API at each station's location (its own cell), on Central days. WISP 3 takes ET0 from Open-Meteo, NBM first, then best_match.

## By month

| Month | days | v2 bias | v2 MAE | v2 ratio | SSEC bias | SSEC MAE | SSEC ratio | ncep_nbm_conus ratio | ecmwf_ifs ratio | best_match ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-01 | 1783 | +1.56 | 1.61 | 1.24 | -0.41 | 0.92 | 0.94 | 1.17 | 1.09 | 1.26 |
| 2025-02 | 1636 | +1.44 | 1.75 | 1.16 | -2.69 | 2.90 | 0.70 | 1.13 | 1.13 | 1.21 |
| 2025-03 | 1779 | +1.73 | 1.97 | 1.14 | -1.54 | 1.80 | 0.88 | 1.12 | 1.11 | 1.16 |
| 2025-04 | 1682 | +3.00 | 3.47 | 1.20 | -0.78 | 1.46 | 0.95 | 1.13 | 1.13 | 1.23 |
| 2025-05 | 1861 | +3.34 | 3.70 | 1.17 | -1.32 | 1.73 | 0.93 | 1.12 | 1.09 | 1.19 |
| 2025-06 | 1941 | +4.60 | 4.71 | 1.25 | -1.09 | 1.50 | 0.94 | 1.20 | 1.18 | 1.28 |
| 2025-07 | 2212 | +3.74 | 3.86 | 1.18 | -0.71 | 1.36 | 0.97 | 1.16 | 1.13 | 1.20 |
| 2025-08 | 2253 | +3.36 | 3.54 | 1.20 | -0.05 | 1.08 | 1.00 | 1.18 | 1.15 | 1.21 |
| 2025-09 | 2297 | +2.24 | 2.50 | 1.16 | +0.23 | 0.99 | 1.02 | 1.15 | 1.15 | 1.17 |
| 2025-10 | 2405 | +1.53 | 1.74 | 1.15 | +0.31 | 0.86 | 1.03 | 1.12 | 1.12 | 1.16 |
| 2025-11 | 2334 | +1.69 | 1.75 | 1.29 | +0.40 | 0.76 | 1.07 | 1.21 | 1.14 | 1.31 |
| 2025-12 | 2399 | +1.17 | 1.39 | 1.28 | -0.42 | 1.09 | 0.90 | 1.24 | 1.21 | 1.36 |
| 2026-01 | 2397 | +1.03 | 1.29 | 1.17 | -1.13 | 1.53 | 0.82 | 1.12 | 1.12 | 1.22 |
| 2026-02 | 2186 | +1.36 | 1.71 | 1.15 | -1.45 | 1.57 | 0.84 | 1.13 | 1.10 | 1.20 |
| 2026-03 | 2388 | +1.89 | 2.37 | 1.15 | -1.81 | 2.23 | 0.85 | 1.12 | 1.10 | 1.20 |
| 2026-04 | 2338 | +2.20 | 2.60 | 1.14 | -0.28 | 0.97 | 0.98 | 1.10 | 1.11 | 1.18 |
| 2026-05 | 2398 | +4.33 | 4.45 | 1.20 | -0.03 | 1.29 | 1.00 | 1.13 | 1.10 | 1.21 |
| 2026-06 | 2337 | +3.84 | 4.06 | 1.19 | -0.27 | 1.33 | 0.99 | 1.14 | 1.15 | 1.21 |
| 2026-07 | 2415 | +3.91 | 3.96 | 1.19 | +0.28 | 1.20 | 1.01 | 1.17 | 1.15 | 1.20 |
| 2026-08 | 2415 | +3.53 | 3.58 | 1.20 | +0.34 | 1.30 | 1.02 | 1.17 | 1.18 | 1.22 |
| 2026-09 | 2335 | +2.37 | 2.58 | 1.19 | +0.97 | 1.28 | 1.08 | 1.16 | 1.17 | 1.22 |
| 2026-10 | 2098 | +1.26 | 1.49 | 1.12 | +1.15 | 1.20 | 1.11 | 1.09 | 1.12 | 1.11 |

## By station

| Station | days | v2 ratio | v2 r | SSEC ratio | SSEC r |
|---|---|---|---|---|---|
| Antigo (ANGO) | 658 | 1.16 | 0.957 | 0.90 | 0.938 |
| Arlington (ALTN) | 659 | 1.16 | 0.961 | 0.93 | 0.955 |
| Arthur (RTHR) | 657 | 1.20 | 0.916 | 0.98 | 0.935 |
| Babcock (BBCK) | 664 | 1.19 | 0.956 | 0.96 | 0.967 |
| Bayfield (BYFD) | 491 | 1.17 | 0.959 | 0.97 | 0.980 |
| Black Creek (BLCR) | 656 | 1.23 | 0.961 | 0.99 | 0.967 |
| Black River Falls (WCRS) | 664 | 1.21 | 0.961 | 0.98 | 0.981 |
| Blanchardville (BCVL) | 421 | 1.17 | 0.956 | 0.96 | 0.972 |
| Brigham (BGHM) | 533 | 1.17 | 0.956 | 0.95 | 0.961 |
| Brillion (BRLN) | 656 | 1.17 | 0.953 | 0.94 | 0.945 |
| Bristol (BSTL) | 651 | 1.16 | 0.966 | 0.97 | 0.954 |
| Brooklyn (BKLN) | 653 | 1.17 | 0.951 | 0.94 | 0.952 |
| Clear Lake (CLLK) | 655 | 1.14 | 0.960 | 0.93 | 0.974 |
| Cold Spring (COSP) | 656 | 1.16 | 0.960 | 0.95 | 0.960 |
| Crandon (CNDN) | 653 | 1.21 | 0.941 | 1.00 | 0.966 |
| Crivitz (CVTZ) | 429 | 1.16 | 0.960 | 0.99 | 0.979 |
| Cutler (CTLR) | 662 | 1.20 | 0.959 | 0.98 | 0.970 |
| Darlington (DLTN) | 487 | 1.17 | 0.942 | 0.96 | 0.935 |
| De Pere (DEPR) | 658 | 1.13 | 0.954 | 0.91 | 0.946 |
| Durand (DRND) | 657 | 1.21 | 0.952 | 0.98 | 0.960 |
| Egg Harbor (EGHA) | 656 | 1.36 | 0.931 | 1.09 | 0.937 |
| Fairchild (FRCD) | 660 | 1.19 | 0.953 | 0.96 | 0.965 |
| Fence (HDMK) | 424 | 1.16 | 0.960 | 0.99 | 0.985 |
| Flambeau (FLMB) | 494 | 1.21 | 0.960 | 1.01 | 0.984 |
| Gleason (GLSN) | 427 | 1.15 | 0.965 | 0.97 | 0.980 |
| Grafton (GFTN) | 658 | 1.16 | 0.956 | 0.98 | 0.978 |
| Grand Marsh (GMSH) | 500 | 1.20 | 0.961 | 1.01 | 0.977 |
| Grantsburg (CREX) | 480 | 1.12 | 0.962 | 0.94 | 0.981 |
| Greenwood (GNWD) | 662 | 1.18 | 0.959 | 0.93 | 0.965 |
| Hancock (HNCK) | 661 | 1.24 | 0.963 | 1.01 | 0.974 |
| Hay River (HRVR) | 481 | 1.13 | 0.959 | 0.94 | 0.981 |
| Hunter (HNTR) | 491 | 1.19 | 0.965 | 1.00 | 0.981 |
| Iola (IOLA) | 656 | 1.17 | 0.958 | 0.96 | 0.971 |
| Kewaskum (KSKM) | 660 | 1.20 | 0.965 | 0.98 | 0.964 |
| Kewaunee (KWNE) | 665 | 1.19 | 0.951 | 0.98 | 0.950 |
| Knight (KNGT) | 637 | 1.24 | 0.954 | 0.99 | 0.985 |
| La Farge (LAFG) | 663 | 1.21 | 0.960 | 0.98 | 0.977 |
| Lancaster (LNCT) | 653 | 1.19 | 0.960 | 0.97 | 0.965 |
| Lost Lake (LOLK) | 546 | 1.18 | 0.959 | 0.97 | 0.969 |
| Luxemburg (LXBG) | 665 | 1.18 | 0.954 | 0.96 | 0.960 |
| Manitowish Waters (MNWT) | 661 | 1.14 | 0.953 | 0.94 | 0.979 |
| Maple (MAPL) | 651 | 1.13 | 0.952 | 0.92 | 0.980 |
| Marshfield (MRFD) | 661 | 1.17 | 0.958 | 0.92 | 0.962 |
| Mindoro (MNDR) | 479 | 1.20 | 0.909 | 0.98 | 0.931 |
| Montana (MNTN) | 655 | 1.18 | 0.958 | 0.95 | 0.977 |
| Montello (MTLO) | 649 | 1.22 | 0.947 | 1.00 | 0.967 |
| Nasewaupee (NASE) | 660 | 1.18 | 0.961 | 0.97 | 0.977 |
| New Berlin (NBLN) | 662 | 1.17 | 0.962 | 1.00 | 0.974 |
| Osseo (OSEO) | 661 | 1.16 | 0.950 | 0.93 | 0.968 |
| Plover (FFEC) | 659 | 1.19 | 0.957 | 0.96 | 0.970 |
| Plymouth (PLYM) | 661 | 1.16 | 0.955 | 0.95 | 0.965 |
| Porter (GLCP) | 660 | 1.17 | 0.964 | 0.94 | 0.960 |
| Prairie du Sac (DFRC) | 664 | 1.19 | 0.955 | 0.97 | 0.969 |
| Rhinelander (RNLD) | 662 | 1.19 | 0.948 | 0.97 | 0.981 |
| Rice Lake (RLKE) | 478 | 1.13 | 0.963 | 0.94 | 0.970 |
| Richland Center (RCHD) | 659 | 1.20 | 0.957 | 0.97 | 0.975 |
| Ripon (RIPN) | 660 | 1.15 | 0.954 | 0.93 | 0.949 |
| River Falls (UWRF) | 496 | 1.17 | 0.969 | 0.97 | 0.973 |
| Shanagolden (SHGD) | 509 | 1.35 | 0.954 | 1.12 | 0.977 |
| Sister Bay (SIBA) | 657 | 1.20 | 0.953 | 1.01 | 0.970 |
| Soldiers Grove (STAR) | 655 | 1.18 | 0.960 | 0.96 | 0.973 |
| South Milwaukee (SMKE) | 659 | 1.17 | 0.958 | 0.99 | 0.973 |
| Southern Door (SODO) | 660 | 1.24 | 0.961 | 1.03 | 0.981 |
| Spooner (SPNR) | 663 | 1.20 | 0.953 | 0.98 | 0.977 |
| Sturgeon Bay (PARS) | 662 | 1.19 | 0.961 | 0.99 | 0.973 |
| Suring (SRNG) | 655 | 1.19 | 0.962 | 0.97 | 0.969 |
| Taycheedah (TCDA) | 542 | 1.18 | 0.957 | 0.97 | 0.964 |
| Valders (VLDR) | 650 | 1.16 | 0.957 | 0.95 | 0.950 |
| Verona (OJNR) | 663 | 1.20 | 0.956 | 0.97 | 0.963 |
| Walworth (DUDA) | 653 | 1.20 | 0.957 | 0.99 | 0.942 |
| Warrens (WRNS) | 659 | 1.17 | 0.959 | 0.95 | 0.977 |
| West Jacksonport (WJPT) | 664 | 1.16 | 0.960 | 0.97 | 0.978 |
| Westboro (WBRO) | 529 | 1.18 | 0.955 | 0.97 | 0.982 |
| Wilkinson (WKSN) | 413 | 1.16 | 0.962 | 0.98 | 0.980 |
| WiscNetTest (WNTEST1) | 76 | 1.26 | 0.958 | 0.92 | 0.868 |
| Wittenberg (WTBG) | 649 | 1.17 | 0.953 | 0.96 | 0.974 |
| Woodruff (KEMP) | 661 | 1.31 | 0.948 | 1.07 | 0.978 |
| Woodville (WDVL) | 654 | 1.17 | 0.956 | 0.94 | 0.969 |
| Yorkville (UGRV) | 659 | 1.17 | 0.964 | 0.98 | 0.955 |
