# Wind against anemometers

Generated 2026-11-11 by `scripts/compare_wind.py` (PLAN.md Phase 6 D3 (a), D84). Daily mean wind speed, 2016-01-01 to 2026-10-31, at the stations in the `wisconsin` box: the archive (URMA's hourly 10 m analysis, the mean of the CST day's hours) at the station's cell and gridMET (NLDAS-2, 10 m) bilinear to the station, against the station's mean of the day. Wisconet's 3 m anemometers are brought to 10 m by FAO-56's log profile (× 1.231); airport anemometers are at about 10 m. URMA assimilates the airport stations, and Wisconet's reach MADIS (78 of 81 have MADIS ids), so the archive may have seen either. Days are each network's own (Wisconet's and IEM's local days; the archive's CST days; gridMET's day runs into our next morning, D2), which matters little for a day's mean wind.

## Wisconet

80 stations. Bias and MAE in m/s at 10 m; ratio is of the totals over the same station-days.

| Source | station-days | bias | MAE | ratio | r |
| --- | --- | --- | --- | --- | --- |
| Archive (URMA) | 65,732 | +0.54 | 0.91 | 1.21 | 0.765 |
| Archive, gridMET's days only | 41,911 | +0.60 | 0.94 | 1.23 | 0.757 |
| gridMET | 41,911 | +2.12 | 2.18 | 1.82 | 0.640 |

### By month

| Month | archive ratio | archive r | gridMET ratio | gridMET r | station mean (m/s) |
| --- | --- | --- | --- | --- | --- |
| Jan | 1.13 | 0.757 | 1.68 | 0.613 | 3.32 |
| Feb | 1.15 | 0.763 | 1.64 | 0.654 | 3.08 |
| Mar | 1.14 | 0.762 | 1.56 | 0.600 | 3.45 |
| Apr | 1.14 | 0.745 | 1.53 | 0.649 | 3.47 |
| May | 1.16 | 0.713 | 1.57 | 0.555 | 2.83 |
| Jun | 1.24 | 0.694 | 1.86 | 0.572 | 2.36 |
| Jul | 1.32 | 0.643 | 2.11 | 0.469 | 1.75 |
| Aug | 1.36 | 0.617 | 2.26 | 0.555 | 1.67 |
| Sep | 1.36 | 0.654 | 2.34 | 0.582 | 1.74 |
| Oct | 1.29 | 0.701 | 2.02 | 0.586 | 2.41 |
| Nov | 1.19 | 0.747 | 1.82 | 0.631 | 2.95 |
| Dec | 1.17 | 0.726 | 1.71 | 0.572 | 3.00 |

### By station

Each station's ratio over its own days (stations with at least 180), sorted by the archive's. Across stations, the archive's ratio runs 0.79 (P10), 1.12 (median), 1.76 (P90).

| Station | days | archive ratio | gridMET ratio | gridMET days |
| --- | --- | --- | --- | --- |
| Mineral Point (MLPT) | 190 | 0.61 | nan | 0 |
| Manitowish Waters (MNWT) | 829 | 0.69 | 1.31 | 525 |
| Bayfield (BYFD) | 499 | 0.70 | 1.36 | 196 |
| Warrens (WRNS) | 855 | 0.73 | 1.28 | 551 |
| Grantsburg (CREX) | 485 | 0.74 | 1.31 | 182 |
| Soldiers Grove (STAR) | 780 | 0.78 | 1.09 | 476 |
| Fairchild (FRCD) | 817 | 0.78 | 1.17 | 513 |
| Crandon (CNDN) | 737 | 0.78 | 1.63 | 437 |
| Osseo (OSEO) | 816 | 0.79 | 1.18 | 512 |
| Darlington (DLTN) | 520 | 0.79 | 1.06 | 216 |
| Black River Falls (WCRS) | 1,114 | 0.88 | 2.15 | 810 |
| Greenwood (GNWD) | 1,118 | 0.96 | 1.46 | 814 |
| Brigham (BGHM) | 543 | 0.98 | 1.15 | 239 |
| Suring (SRNG) | 741 | 0.98 | 1.80 | 437 |
| Antigo (ANGO) | 786 | 0.99 | 1.48 | 483 |
| Grand Marsh (GMSH) | 507 | 0.99 | 1.54 | 203 |
| Babcock (BBCK) | 845 | 0.99 | 1.43 | 541 |
| Montana (MNTN) | 756 | 1.00 | 1.21 | 452 |
| Arlington (ALTN) | 1,181 | 1.00 | 1.23 | 878 |
| Walworth (DUDA) | 896 | 1.00 | 1.37 | 592 |
| Flambeau (FLMB) | 499 | 1.00 | 2.46 | 197 |
| De Pere (DEPR) | 871 | 1.01 | 1.23 | 569 |
| Rhinelander (RNLD) | 1,400 | 1.01 | 1.89 | 1,096 |
| Cold Spring (COSP) | 1,113 | 1.01 | 1.52 | 809 |
| Rice Lake (RLKE) | 484 | 1.01 | 1.48 | 181 |
| Montello (MTLO) | 760 | 1.02 | 1.46 | 463 |
| Cutler (CTLR) | 836 | 1.03 | 1.75 | 534 |
| Hay River (HRVR) | 486 | 1.03 | 1.57 | 183 |
| Lost Lake (LOLK) | 557 | 1.05 | 1.46 | 253 |
| Westboro (WBRO) | 534 | 1.06 | 2.18 | 232 |
| Iola (IOLA) | 746 | 1.06 | 1.85 | 442 |
| Valders (VLDR) | 736 | 1.06 | 1.34 | 432 |
| Brillion (BRLN) | 870 | 1.06 | 1.35 | 567 |
| Kewaskum (KSKM) | 864 | 1.09 | 1.52 | 560 |
| Fence (HDMK) | 429 | 1.09 | 2.64 | 129 |
| West Jacksonport (WJPT) | 1,172 | 1.09 | 1.86 | 868 |
| Maple (MAPL) | 754 | 1.10 | 1.52 | 457 |
| Durand (DRND) | 755 | 1.12 | 1.52 | 451 |
| Plymouth (PLYM) | 734 | 1.12 | 1.43 | 431 |
| Clear Lake (CLLK) | 837 | 1.12 | 1.77 | 533 |
| Richland Center (RCHD) | 887 | 1.13 | 1.84 | 583 |
| Marshfield (MRFD) | 1,400 | 1.14 | 1.31 | 1,096 |
| Blanchardville (BCVL) | 428 | 1.16 | 1.37 | 125 |
| Lancaster (LNCT) | 1,396 | 1.17 | 1.43 | 1,094 |
| Prairie du Sac (DFRC) | 1,128 | 1.21 | 1.88 | 824 |
| Gleason (GLSN) | 434 | 1.23 | 2.44 | 134 |
| Hunter (HNTR) | 498 | 1.24 | 3.05 | 196 |
| Sister Bay (SIBA) | 1,171 | 1.26 | 2.27 | 870 |
| Ripon (RIPN) | 873 | 1.28 | 1.59 | 569 |
| Wittenberg (WTBG) | 738 | 1.29 | 2.18 | 437 |
| Spooner (SPNR) | 1,400 | 1.29 | 1.95 | 1,096 |
| Sturgeon Bay (PARS) | 1,175 | 1.30 | 2.18 | 871 |
| Bristol (BSTL) | 914 | 1.37 | 2.06 | 615 |
| Brooklyn (BKLN) | 761 | 1.37 | 1.68 | 463 |
| Wilkinson (WKSN) | 418 | 1.39 | 2.29 | 122 |
| Woodville (WDVL) | 794 | 1.41 | 1.81 | 490 |
| Nasewaupee (NASE) | 1,172 | 1.42 | 2.02 | 870 |
| Luxemburg (LXBG) | 1,164 | 1.43 | 2.00 | 860 |
| Porter (GLCP) | 892 | 1.47 | 1.72 | 588 |
| La Farge (LAFG) | 881 | 1.47 | 3.16 | 577 |
| Grafton (GFTN) | 862 | 1.48 | 2.25 | 560 |
| New Berlin (NBLN) | 842 | 1.48 | 2.00 | 538 |
| Plover (FFEC) | 860 | 1.51 | 2.06 | 556 |
| Verona (OJNR) | 1,131 | 1.54 | 1.77 | 827 |
| Crivitz (CVTZ) | 434 | 1.54 | 4.15 | 132 |
| Mindoro (MNDR) | 487 | 1.56 | 2.95 | 184 |
| Hancock (HNCK) | 1,399 | 1.58 | 2.17 | 1,095 |
| Arthur (RTHR) | 797 | 1.58 | 2.56 | 493 |
| Kewaunee (KWNE) | 1,170 | 1.59 | 2.30 | 866 |
| River Falls (UWRF) | 502 | 1.61 | 2.01 | 198 |
| Taycheedah (TCDA) | 556 | 1.65 | 1.53 | 252 |
| South Milwaukee (SMKE) | 767 | 1.74 | 1.95 | 463 |
| Yorkville (UGRV) | 787 | 1.90 | 2.36 | 483 |
| Knight (KNGT) | 824 | 2.07 | 3.58 | 524 |
| Southern Door (SODO) | 1,176 | 2.23 | 3.67 | 872 |
| WiscNetTest (WNTEST1) | 468 | 2.25 | 2.73 | 463 |
| Egg Harbor (EGHA) | 1,167 | 2.25 | 3.49 | 863 |
| Black Creek (BLCR) | 872 | 2.96 | 3.98 | 568 |
| Shanagolden (SHGD) | 519 | 3.73 | 10.23 | 218 |
| Woodruff (KEMP) | 1,136 | 4.10 | 6.78 | 832 |

## Airports (ASOS/AWOS)

70 stations. Bias and MAE in m/s at 10 m; ratio is of the totals over the same station-days.

| Source | station-days | bias | MAE | ratio | r |
| --- | --- | --- | --- | --- | --- |
| Archive (URMA) | 270,839 | -0.10 | 0.44 | 0.97 | 0.917 |
| Archive, gridMET's days only | 250,264 | -0.11 | 0.45 | 0.96 | 0.915 |
| gridMET | 251,027 | +1.53 | 1.59 | 1.51 | 0.777 |

### By month

| Month | archive ratio | archive r | gridMET ratio | gridMET r | station mean (m/s) |
| --- | --- | --- | --- | --- | --- |
| Jan | 0.96 | 0.910 | 1.51 | 0.777 | 3.20 |
| Feb | 0.97 | 0.908 | 1.46 | 0.778 | 3.36 |
| Mar | 0.97 | 0.919 | 1.40 | 0.807 | 3.50 |
| Apr | 0.97 | 0.910 | 1.38 | 0.775 | 3.70 |
| May | 0.96 | 0.913 | 1.42 | 0.747 | 3.09 |
| Jun | 0.96 | 0.895 | 1.49 | 0.701 | 2.80 |
| Jul | 0.97 | 0.898 | 1.58 | 0.695 | 2.29 |
| Aug | 0.98 | 0.899 | 1.65 | 0.700 | 2.22 |
| Sep | 0.96 | 0.882 | 1.66 | 0.710 | 2.52 |
| Oct | 0.97 | 0.910 | 1.58 | 0.779 | 3.03 |
| Nov | 0.96 | 0.922 | 1.55 | 0.777 | 3.31 |
| Dec | 0.96 | 0.921 | 1.52 | 0.782 | 3.25 |

### By station

Each station's ratio over its own days (stations with at least 180), sorted by the archive's. Across stations, the archive's ratio runs 0.86 (P10), 0.96 (median), 1.11 (P90).

| Station | days | archive ratio | gridMET ratio | gridMET days |
| --- | --- | --- | --- | --- |
| La Crosse (LSE) | 3,946 | 0.77 | 1.18 | 3,653 |
| EAU CLAIRE (EAU) | 3,945 | 0.81 | 1.31 | 3,653 |
| WISCONSIN RAPIDS (ISW) | 3,942 | 0.81 | 1.34 | 3,649 |
| WAUSAU (AUW) | 3,938 | 0.83 | 1.34 | 3,645 |
| PRAIRIE DU CHIEN (PDC) | 3,886 | 0.85 | 1.65 | 3,609 |
| Ashland (ASX) | 3,945 | 0.86 | 1.30 | 3,652 |
| Camp Douglas - Volk Field (VOK) | 3,911 | 0.86 | 1.29 | 3,619 |
| STURGEON BAY (SUE) | 3,933 | 0.86 | 1.43 | 3,643 |
| WAUKESHA CNTY (UES) | 3,946 | 0.87 | 1.35 | 3,653 |
| HAYWARD (HYR) | 3,921 | 0.88 | 1.90 | 3,628 |
| OSCEOLA (OEO) | 3,940 | 0.88 | 1.37 | 3,647 |
| MILWAUKEE (MKE) | 3,946 | 0.88 | 1.27 | 3,653 |
| KENOSHA (ENW) | 3,929 | 0.89 | 1.24 | 3,653 |
| MILWAUKEE/LAWREN (MWC) | 3,946 | 0.89 | 1.47 | 3,653 |
| Wautoma (Y50) | 3,918 | 0.89 | 1.61 | 3,640 |
| NEW RICHMOND MUN (RNH) | 3,945 | 0.89 | 1.34 | 3,652 |
| LONE ROCK (LNR) | 3,925 | 0.89 | 1.37 | 3,632 |
| Platteville (PVB) | 3,937 | 0.90 | 1.09 | 3,644 |
| APPLETON/OUTAGAM (ATW) | 3,946 | 0.90 | 1.16 | 3,653 |
| JANESVILLE/ROCK (JVL) | 3,946 | 0.90 | 1.26 | 3,653 |
| FOND DU LAC (FLD) | 3,945 | 0.90 | 1.15 | 3,652 |
| RHINELANDER (RHI) | 3,942 | 0.90 | 1.63 | 3,649 |
| Ashwaubenon (GRB) | 3,946 | 0.92 | 1.19 | 3,653 |
| MARSHFIELD (MFI) | 3,936 | 0.92 | 1.14 | 3,643 |
| MOSINEE/CENTRAL (CWA) | 3,946 | 0.93 | 1.23 | 3,653 |
| Manitowish Waters (D25) | 3,734 | 0.93 | 1.79 | 3,441 |
| MINOCQUA/WOODRUF (ARV) | 3,848 | 0.93 | 1.78 | 3,556 |
| CLINTONVILLE (CLI) | 3,674 | 0.93 | 1.43 | 3,407 |
| Ladysmith (RCX) | 3,880 | 0.94 | 1.72 | 3,587 |
| MONROE (EFT) | 3,933 | 0.94 | 1.03 | 3,640 |
| Viroqua (Y51) | 3,734 | 0.95 | 1.21 | 3,552 |
| Black River Falls (BCK) | 3,926 | 0.95 | 2.30 | 3,643 |
| MINERAL POINT (MRJ) | 3,393 | 0.95 | 1.24 | 3,404 |
| Cumberland (UBE) | 3,930 | 0.96 | 1.42 | 3,641 |
| Menomonie  WI (LUM) | 3,879 | 0.96 | 1.29 | 3,586 |
| SUPERIOR (SUW) | 3,862 | 0.96 | 1.56 | 3,569 |
| MADISON (MSN) | 3,946 | 0.97 | 1.43 | 3,653 |
| EAGLE RIVER (EGV) | 3,872 | 0.97 | 1.78 | 3,580 |
| DELLS/BARABOO (DLL) | 3,924 | 0.97 | 1.47 | 3,631 |
| ANTIGO (AIG) | 3,920 | 0.98 | 1.49 | 3,629 |
| Solon Springs (OLG) | 3,899 | 0.98 | 1.97 | 3,606 |
| WATERTOWN (RYV) | 3,557 | 0.98 | 1.60 | 3,333 |
| SIREN (RZN) | 3,860 | 0.99 | 1.44 | 3,567 |
| Land O Lakes (LNL) | 3,945 | 0.99 | 2.05 | 3,652 |
| BURLINGTON (BUU) | 3,939 | 0.99 | 1.67 | 3,646 |
| MEDFORD (MDZ) | 3,945 | 0.99 | 1.59 | 3,652 |
| MANITOWAC MUNI (MTW) | 3,934 | 0.99 | 1.61 | 3,641 |
| PHILLIPS/PRICE (PBH) | 3,943 | 1.00 | 2.13 | 3,650 |
| RACINE (RAC) | 3,906 | 1.00 | 1.31 | 3,647 |
| MERRILL (RRL) | 3,687 | 1.01 | 1.85 | 3,426 |
| OSHKOSH (OSH) | 3,945 | 1.02 | 1.20 | 3,652 |
| RICE LAKE (RPD) | 3,941 | 1.02 | 1.67 | 3,648 |
| SHEBOYGAN (SBM) | 3,940 | 1.03 | 1.45 | 3,647 |
| STEVENS POINT (STE) | 3,879 | 1.03 | 1.55 | 3,586 |
| Reedsburg (C35) | 3,929 | 1.04 | 1.67 | 3,642 |
| Ephraim (3D2) | 3,919 | 1.05 | 1.89 | 3,626 |
| JUNEAU (UNU) | 3,890 | 1.06 | 1.62 | 3,611 |
| WEST BEND (ETB) | 3,854 | 1.07 | 1.59 | 3,564 |
| Middleton (C29) | 3,937 | 1.07 | 1.35 | 3,646 |
| Lisbon Union (82C) | 3,912 | 1.09 | 1.73 | 3,619 |
| Waupaca (PCZ) | 3,909 | 1.09 | 1.86 | 3,616 |
| East Troy (57C) | 2,984 | 1.09 | 1.67 | 2,689 |
| SPARTA/MCCOY AAF (CMY) | 3,868 | 1.11 | 2.38 | 3,578 |
| Shawano (EZS) | 3,807 | 1.12 | 1.79 | 3,514 |
| Oconto (OCQ) | 3,916 | 1.12 | 1.73 | 3,637 |
| Washington Island (2P2) | 3,681 | 1.16 | 1.47 | 3,388 |
| Chetek (Y23) | 3,935 | 1.21 | 2.17 | 3,642 |
| BOSCOBEL (OVS) | 3,911 | 1.22 | 1.85 | 3,631 |
| La Pointe (4R5) | 3,298 | 1.52 | 2.11 | 3,003 |
| Tomahawk (TKV) | 3,908 | 1.59 | 3.47 | 3,615 |
