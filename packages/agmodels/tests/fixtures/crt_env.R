# Loads the Crop Risk Tool's code (tmp/shiny/crop-risk-tool) for the fixture makers, with its renv lockfile
# restored into tmp/shiny/crop-risk-tool/renv-linux-lib (sf and terra built from source against the system GDAL;
# PLAN.md Phase 3 F). The tool's .Rprofile points at a Windows library, so run with `Rscript --no-init-file`.
crt_dir <- normalizePath("tmp/shiny/crop-risk-tool")
.libPaths(file.path(crt_dir, "renv-linux-lib"))
suppressMessages(source(file.path(crt_dir, "global.R"), chdir = TRUE))
