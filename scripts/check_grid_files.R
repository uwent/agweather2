# Checks v2 grid files the way an R user opens them (PLAN.md Phase 5 E, D65): each file loads in terra, has a CRS,
# and reprojects onto a lat/lon template over Wisconsin. Found 2026-11-04: 2-D lat/lon arrays in a NetCDF made GDAL
# use them as geolocation arrays, and terra's projection collapsed to a point; api/gridfiles.py leaves them out.
#
#   curl -o /tmp/tmax.nc "localhost:8000/api/v2/grids/air_temperature_max?start=2026-07-01&end=2026-07-07&format=netcdf"
#   curl -o /tmp/tmax.tif "localhost:8000/api/v2/grids/air_temperature_max?start=2026-07-01&end=2026-07-07&format=geotiff"
#   Rscript scripts/check_grid_files.R /tmp/tmax.nc /tmp/tmax.tif
#
# Files over the whole service box should fill ~100% of the template; a region= file fills only the region's share.
suppressMessages(library(terra))
failed <- FALSE
for (f in commandArgs(TRUE)) {
  r <- rast(f)
  template <- rast(ext(-92.9, -86.8, 42.5, 47.1), res = 0.05, crs = "EPSG:4326")
  filled <- 100 * mean(!is.na(values(project(r[[1]], template))))
  e <- as.vector(ext(project(r, "EPSG:4326")))
  ok <- crs(r) != "" && e[2] - e[1] > 1 && filled > 0
  cat(sprintf("%s %s: %d layers, lon %.2f..%.2f, lat %.2f..%.2f, fills %.1f%% of Wisconsin's template\n",
              if (ok) "ok  " else "FAIL", basename(f), nlyr(r), e[1], e[2], e[3], e[4], filled))
  failed <- failed || !ok
}
quit(status = if (failed) 1 else 0)
