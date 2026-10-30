# Shortwave against Wisconet's pyranometers

Generated 2026-10-30 by `scripts/compare_pyranometers.py` (PLAN.md Phase 2 H). Daily totals (MJ/m²), 2025-01-01 to 2026-10-27, at 80 Wisconet stations in the `wisconsin` box: v2 (HRRR's hourly means) at the station's cell and the old API's SSEC satellite insolation at the nearest 0.1° point, against the station's `daily_solar_radiation_mj_tot`. Station days outside 0–36 MJ/m² are left out. Bias and MAE in MJ/m²; ratio is of the totals over the same days.

## Which day a Wisconet stamp closes

Correlation of v2 with the stations, their days shifted (0 is the reading used: the day before the stamp).

| Shift (days) | r |
|---|---|
| -1 | 0.665 |
| +0 | 0.955 |
| +1 | 0.695 |

## Overall

| Source | days | bias | MAE | ratio | r |
|---|---|---|---|---|---|
| v2 (HRRR) | 47889 | +0.06 | 1.64 | 1.00 | 0.955 |
| old API (SSEC) | 47368 | -0.41 | 1.35 | 0.97 | 0.965 |
| Open-Meteo ncep_nbm_conus | 47350 | +1.99 | 2.31 | 1.15 | 0.957 |
| Open-Meteo ecmwf_ifs | 47889 | +1.82 | 2.14 | 1.13 | 0.955 |
| Open-Meteo best_match | 47889 | +2.81 | 2.98 | 1.21 | 0.944 |

Open-Meteo is its historical-forecast API at each station's location (its own cell), on Central days. WISP 3 takes ET0 from Open-Meteo, NBM first, then best_match.

## By month

| Month | days | v2 bias | v2 MAE | v2 ratio | SSEC bias | SSEC MAE | SSEC ratio | ncep_nbm_conus ratio | ecmwf_ifs ratio | best_match ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-01 | 1783 | +0.24 | 1.01 | 1.04 | -0.41 | 0.92 | 0.94 | 1.17 | 1.09 | 1.26 |
| 2025-02 | 1636 | -0.25 | 1.55 | 0.97 | -2.69 | 2.90 | 0.70 | 1.13 | 1.13 | 1.21 |
| 2025-03 | 1779 | -0.30 | 1.66 | 0.98 | -1.54 | 1.80 | 0.88 | 1.12 | 1.11 | 1.16 |
| 2025-04 | 1682 | +0.33 | 2.15 | 1.02 | -0.78 | 1.46 | 0.95 | 1.13 | 1.13 | 1.23 |
| 2025-05 | 1861 | +0.21 | 2.30 | 1.01 | -1.32 | 1.73 | 0.93 | 1.12 | 1.09 | 1.19 |
| 2025-06 | 1941 | +1.30 | 2.28 | 1.07 | -1.09 | 1.50 | 0.94 | 1.20 | 1.18 | 1.28 |
| 2025-07 | 2212 | +0.24 | 1.68 | 1.01 | -0.71 | 1.36 | 0.97 | 1.16 | 1.13 | 1.20 |
| 2025-08 | 2253 | +0.07 | 1.90 | 1.00 | -0.05 | 1.08 | 1.00 | 1.18 | 1.15 | 1.21 |
| 2025-09 | 2297 | -0.55 | 1.68 | 0.96 | +0.23 | 0.99 | 1.02 | 1.15 | 1.15 | 1.17 |
| 2025-10 | 2405 | -0.40 | 1.40 | 0.96 | +0.31 | 0.86 | 1.03 | 1.12 | 1.12 | 1.16 |
| 2025-11 | 2334 | +0.44 | 1.19 | 1.08 | +0.40 | 0.76 | 1.07 | 1.21 | 1.14 | 1.31 |
| 2025-12 | 2399 | +0.23 | 1.01 | 1.05 | -0.42 | 1.09 | 0.90 | 1.24 | 1.21 | 1.36 |
| 2026-01 | 2397 | -0.18 | 1.06 | 0.97 | -1.13 | 1.53 | 0.82 | 1.12 | 1.12 | 1.22 |
| 2026-02 | 2186 | -0.38 | 1.49 | 0.96 | -1.45 | 1.57 | 0.84 | 1.13 | 1.10 | 1.20 |
| 2026-03 | 2388 | -0.25 | 1.67 | 0.98 | -1.81 | 2.23 | 0.85 | 1.12 | 1.10 | 1.20 |
| 2026-04 | 2338 | -0.32 | 1.80 | 0.98 | -0.28 | 0.97 | 0.98 | 1.10 | 1.11 | 1.18 |
| 2026-05 | 2398 | +0.78 | 2.00 | 1.04 | -0.03 | 1.29 | 1.00 | 1.13 | 1.10 | 1.21 |
| 2026-06 | 2337 | +0.50 | 2.08 | 1.02 | -0.27 | 1.33 | 0.99 | 1.14 | 1.15 | 1.21 |
| 2026-07 | 2415 | +0.24 | 1.80 | 1.01 | +0.28 | 1.20 | 1.01 | 1.17 | 1.15 | 1.20 |
| 2026-08 | 2415 | +0.18 | 1.67 | 1.01 | +0.34 | 1.30 | 1.02 | 1.17 | 1.18 | 1.22 |
| 2026-09 | 2335 | -0.06 | 1.55 | 0.99 | +0.97 | 1.28 | 1.08 | 1.16 | 1.17 | 1.22 |
| 2026-10 | 2098 | -0.69 | 1.43 | 0.94 | +1.15 | 1.20 | 1.11 | 1.09 | 1.12 | 1.11 |

## By station

| Station | days | v2 ratio | v2 r | SSEC ratio | SSEC r |
|---|---|---|---|---|---|
| Antigo (ANGO) | 658 | 0.99 | 0.958 | 0.90 | 0.938 |
| Arlington (ALTN) | 659 | 0.98 | 0.962 | 0.93 | 0.955 |
| Arthur (RTHR) | 657 | 1.02 | 0.917 | 0.98 | 0.935 |
| Babcock (BBCK) | 664 | 1.01 | 0.958 | 0.96 | 0.967 |
| Bayfield (BYFD) | 491 | 1.00 | 0.961 | 0.97 | 0.980 |
| Black Creek (BLCR) | 656 | 1.04 | 0.963 | 0.99 | 0.967 |
| Black River Falls (WCRS) | 664 | 1.03 | 0.963 | 0.98 | 0.981 |
| Blanchardville (BCVL) | 421 | 0.99 | 0.958 | 0.96 | 0.972 |
| Brigham (BGHM) | 533 | 0.99 | 0.958 | 0.95 | 0.961 |
| Brillion (BRLN) | 656 | 0.99 | 0.955 | 0.94 | 0.945 |
| Bristol (BSTL) | 651 | 0.98 | 0.966 | 0.97 | 0.954 |
| Brooklyn (BKLN) | 653 | 0.99 | 0.952 | 0.94 | 0.952 |
| Clear Lake (CLLK) | 655 | 0.97 | 0.961 | 0.93 | 0.974 |
| Cold Spring (COSP) | 656 | 0.98 | 0.960 | 0.95 | 0.960 |
| Crandon (CNDN) | 653 | 1.02 | 0.942 | 1.00 | 0.966 |
| Crivitz (CVTZ) | 429 | 0.98 | 0.961 | 0.99 | 0.979 |
| Cutler (CTLR) | 662 | 1.02 | 0.960 | 0.98 | 0.970 |
| Darlington (DLTN) | 487 | 0.99 | 0.944 | 0.96 | 0.935 |
| De Pere (DEPR) | 658 | 0.95 | 0.955 | 0.91 | 0.946 |
| Durand (DRND) | 657 | 1.03 | 0.951 | 0.98 | 0.960 |
| Egg Harbor (EGHA) | 656 | 1.15 | 0.932 | 1.09 | 0.937 |
| Fairchild (FRCD) | 660 | 1.01 | 0.956 | 0.96 | 0.965 |
| Fence (HDMK) | 424 | 0.98 | 0.961 | 0.99 | 0.985 |
| Flambeau (FLMB) | 494 | 1.02 | 0.961 | 1.01 | 0.984 |
| Gleason (GLSN) | 427 | 0.97 | 0.965 | 0.97 | 0.980 |
| Grafton (GFTN) | 658 | 0.98 | 0.957 | 0.98 | 0.978 |
| Grand Marsh (GMSH) | 500 | 1.02 | 0.962 | 1.01 | 0.977 |
| Grantsburg (CREX) | 480 | 0.95 | 0.963 | 0.94 | 0.981 |
| Greenwood (GNWD) | 662 | 1.00 | 0.959 | 0.93 | 0.965 |
| Hancock (HNCK) | 661 | 1.05 | 0.966 | 1.01 | 0.974 |
| Hay River (HRVR) | 481 | 0.96 | 0.959 | 0.94 | 0.981 |
| Hunter (HNTR) | 491 | 1.01 | 0.967 | 1.00 | 0.981 |
| Iola (IOLA) | 656 | 0.99 | 0.960 | 0.96 | 0.971 |
| Kewaskum (KSKM) | 660 | 1.01 | 0.966 | 0.98 | 0.964 |
| Kewaunee (KWNE) | 665 | 1.01 | 0.952 | 0.98 | 0.950 |
| Knight (KNGT) | 637 | 1.05 | 0.957 | 0.99 | 0.985 |
| La Farge (LAFG) | 663 | 1.03 | 0.962 | 0.98 | 0.977 |
| Lancaster (LNCT) | 653 | 1.01 | 0.961 | 0.97 | 0.965 |
| Lost Lake (LOLK) | 546 | 1.00 | 0.960 | 0.97 | 0.969 |
| Luxemburg (LXBG) | 665 | 1.00 | 0.955 | 0.96 | 0.960 |
| Manitowish Waters (MNWT) | 661 | 0.97 | 0.954 | 0.94 | 0.979 |
| Maple (MAPL) | 651 | 0.96 | 0.955 | 0.92 | 0.980 |
| Marshfield (MRFD) | 661 | 0.99 | 0.960 | 0.92 | 0.962 |
| Mindoro (MNDR) | 479 | 1.02 | 0.910 | 0.98 | 0.931 |
| Montana (MNTN) | 655 | 1.00 | 0.960 | 0.95 | 0.977 |
| Montello (MTLO) | 649 | 1.03 | 0.949 | 1.00 | 0.967 |
| Nasewaupee (NASE) | 660 | 1.00 | 0.963 | 0.97 | 0.977 |
| New Berlin (NBLN) | 662 | 0.99 | 0.963 | 1.00 | 0.974 |
| Osseo (OSEO) | 661 | 0.99 | 0.951 | 0.93 | 0.968 |
| Plover (FFEC) | 659 | 1.01 | 0.958 | 0.96 | 0.970 |
| Plymouth (PLYM) | 661 | 0.98 | 0.957 | 0.95 | 0.965 |
| Porter (GLCP) | 660 | 0.99 | 0.965 | 0.94 | 0.960 |
| Prairie du Sac (DFRC) | 664 | 1.01 | 0.957 | 0.97 | 0.969 |
| Rhinelander (RNLD) | 662 | 1.01 | 0.949 | 0.97 | 0.981 |
| Rice Lake (RLKE) | 478 | 0.96 | 0.964 | 0.94 | 0.970 |
| Richland Center (RCHD) | 659 | 1.02 | 0.959 | 0.97 | 0.975 |
| Ripon (RIPN) | 660 | 0.98 | 0.956 | 0.93 | 0.949 |
| River Falls (UWRF) | 496 | 1.00 | 0.970 | 0.97 | 0.973 |
| Shanagolden (SHGD) | 509 | 1.14 | 0.956 | 1.12 | 0.977 |
| Sister Bay (SIBA) | 657 | 1.02 | 0.955 | 1.01 | 0.970 |
| Soldiers Grove (STAR) | 655 | 1.00 | 0.960 | 0.96 | 0.973 |
| South Milwaukee (SMKE) | 659 | 0.99 | 0.961 | 0.99 | 0.973 |
| Southern Door (SODO) | 660 | 1.05 | 0.963 | 1.03 | 0.981 |
| Spooner (SPNR) | 663 | 1.02 | 0.956 | 0.98 | 0.977 |
| Sturgeon Bay (PARS) | 662 | 1.01 | 0.962 | 0.99 | 0.973 |
| Suring (SRNG) | 655 | 1.00 | 0.964 | 0.97 | 0.969 |
| Taycheedah (TCDA) | 542 | 1.00 | 0.960 | 0.97 | 0.964 |
| Valders (VLDR) | 650 | 0.98 | 0.959 | 0.95 | 0.950 |
| Verona (OJNR) | 663 | 1.02 | 0.958 | 0.97 | 0.963 |
| Walworth (DUDA) | 653 | 1.01 | 0.957 | 0.99 | 0.942 |
| Warrens (WRNS) | 659 | 0.99 | 0.961 | 0.95 | 0.977 |
| West Jacksonport (WJPT) | 664 | 0.98 | 0.962 | 0.97 | 0.978 |
| Westboro (WBRO) | 529 | 1.00 | 0.955 | 0.97 | 0.982 |
| Wilkinson (WKSN) | 413 | 0.99 | 0.964 | 0.98 | 0.980 |
| WiscNetTest (WNTEST1) | 76 | 1.07 | 0.957 | 0.92 | 0.868 |
| Wittenberg (WTBG) | 649 | 0.99 | 0.955 | 0.96 | 0.974 |
| Woodruff (KEMP) | 661 | 1.11 | 0.950 | 1.07 | 0.978 |
| Woodville (WDVL) | 654 | 0.99 | 0.957 | 0.94 | 0.969 |
| Yorkville (UGRV) | 659 | 0.99 | 0.964 | 0.98 | 0.955 |
