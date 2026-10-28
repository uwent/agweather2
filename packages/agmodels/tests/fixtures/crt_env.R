# Loads the Crop Risk Tool's model code (tmp/shiny/crop-risk-tool) for the fixture makers, without sf (its
# GIS stack needs system GDAL/PROJ, and the models don't use it). Packages: the tool's renv lockfile restored
# into tmp/shiny/crop-risk-tool/renv-linux-lib (see make_crt_fixtures.R).
crt_dir <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), "../../../../tmp/shiny/crop-risk-tool"))
.libPaths(file.path(crt_dir, "renv-linux-lib"))
real_library <- base::library
library <- function(package, ...) {
  p <- as.character(substitute(package))
  if (p == "sf") return(invisible(NULL))
  real_library(p, character.only = TRUE, ...)
}
packageVersion <- function(pkg, ...) if (pkg == "sf") "0" else utils::packageVersion(pkg, ...)
suppressMessages(source(file.path(crt_dir, "global.R"), chdir = TRUE))
