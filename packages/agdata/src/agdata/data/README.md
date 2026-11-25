# agdata static data

Built once by scripts in `scripts/`; no live sources (docs/decisions.md D34). Rebuild with the commands in each script's docstring.

<!-- prettier-ignore -->
| File | Built by | Source | License |
| --- | --- | --- | --- |
| `counties.npz`, `counties.csv` (with each county's land area and its cells on the 2.5 km grid) | `build_counties.py` | U.S. Census Bureau, 2024 cartographic boundary file, counties, 1:500,000 (`cb_2024_us_county_500k`), kept in `data/census/` | Public domain (U.S. government work) |
| `planting_dates.csv`, county rows | `build_planting_dates.py` | Deines, J. M., Swatantran, A., Ye, D., Myers, B., Archontoulis, S. and Lobell, D. B. (2023). Field-scale dynamics of planting dates in the US Corn Belt from 2000 to 2020. Remote Sensing of Environment 291, 113551. https://doi.org/10.1016/j.rse.2023.113551; data https://doi.org/10.5281/zenodo.7790257 | CC BY 4.0 (medians over years computed here) |
| `planting_dates.csv`, state rows | `build_planting_dates.py` | USDA NASS (2010). Usual planting and harvesting dates for U.S. field crops. Agricultural Handbook 628 | Public domain (U.S. government work) |
| `coverage-upper_midwest.npz` (the launch coverage, D105: the mask's cells over its bounding window) | `make_coverage_mask.py` | U.S. Census Bureau, 2023 cartographic boundary file, states, 1:5,000,000 (`cb_2023_us_state_5m`), kept in `data/census/`; the Great Lakes from `water.npz` | Public domain (U.S. government work) |
| `outlines.npz` | `make_outlines.py` | U.S. Census Bureau, 2023 cartographic boundary files, states and counties, 1:5,000,000 (`cb_2023_us_state_5m`, `cb_2023_us_county_5m`); the lower 48 and DC; kept in `data/census/` | Public domain (U.S. government work) |

## Built into `data/` by commands

Larger static stores built from outside files by a management command, kept in the data folder rather than this package (each command's module docstring says how).

<!-- prettier-ignore -->
| Store | Built by | Source | License |
| --- | --- | --- | --- |
| `data/terrain.zarr` | `manage.py terrain` (`agdata.terrain`, Phase 6 D6) | EPA and USGS, NHDPlus Version 2.1 (NHD snapshot and 30 m NED), kept as received in `data/nhdplus/` | Public domain (U.S. government work) |
| `data/cropland.zarr` | `manage.py cropland` (`agdata.cropland`, D116) | USDA National Agricultural Statistics Service, Cropland Data Layer, 2021–2025, national 30 m files (`<year>_30m_cdls.zip` from https://www.nass.usda.gov/Research_and_Science/Cropland/Release/), kept as received in `data/cdl/`; the cultivated rule and class list from NASS's 2025 Cultivated Layer metadata. Credit: "USDA National Agricultural Statistics Service Cropland Data Layer, 2021–2025" | Public domain, free to redistribute (NASS's metadata) |
