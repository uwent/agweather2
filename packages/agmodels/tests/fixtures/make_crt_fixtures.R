# Rebuilds the Crop Risk Tool parity fixtures (crt_*.csv) from its R code and recorded weather.
#   Rscript --no-init-file packages/agmodels/tests/fixtures/make_crt_fixtures.R
# Needs the tool in tmp/shiny/crop-risk-tool with its renv library restored into renv-linux-lib (PLAN.md Phase 3 F).
source("packages/agmodels/tests/fixtures/crt_env.R")
out_dir <- "packages/agmodels/tests/fixtures"
write <- function(df, name) {
  readr::write_csv(df, file.path(out_dir, paste0("crt_", name, ".csv")), na = "")
  message("wrote crt_", name, ".csv (", nrow(df), " rows)")
}

# One grid cell's 2025 (Eau Claire, WI), hourly as the tool receives it and daily as it builds it
wx <- readRDS(file.path(crt_dir, "tests/testthat/test_hourly_wx.rds")) |> filter(grid_id == "44.815,-91.530")
write(
  wx |> transmute(local_time = format(datetime_local, "%Y-%m-%dT%H:%M"), temperature, dew_point, relative_humidity, precipitation),
  "hourly_eau_claire_2025"
)
daily <- build_daily(wx)
write(
  daily |> select(
    date, temperature_min, temperature_max, precipitation_daily, hours_temp_over_20, hours_temp_over_30,
    hours_rh_under_70, hours_rh_over_80, hours_rh_over_90, hours_rh_over_80_night, hours_rh_over_90_night,
    temperature_mean_rh_over_80, temperature_mean_rh_over_90, hot_past_5_days, dry
  ),
  "daily_eau_claire_2025"
)

# Late blight: the DSV table over temperature and hours, and the model over the year
write(
  expand_grid(t = seq(-2, 30, 0.2), h = 0:24) |> mutate(dsv = calc_late_blight_dsv(t, h)),
  "late_blight_dsv_sweep"
)
write(build_late_blight(daily) |> select(date, dsv, total14, total, severity), "late_blight_eau_claire_2025")

# Early blight: P-days over min and max, and the model over the year
write(
  expand_grid(tmin = seq(-5, 35, 0.5), tmax = seq(-5, 40, 0.5)) |> filter(tmin <= tmax) |> mutate(pdays = calc_pdays(tmin, tmax)),
  "early_blight_pdays_sweep"
)
write(build_early_blight(daily) |> select(date, pdays, total, avg7, severity), "early_blight_eau_claire_2025")

# Carrot foliar (Alternaria, TOMCAST)
write(expand_grid(t = seq(5, 35, 0.2), h = 0:24) |> mutate(dsv = calc_alternaria_dsv(t, h)), "alternaria_dsv_sweep")
write(build_alternaria(daily) |> select(date, dsv, total7, total, severity), "alternaria_eau_claire_2025")

# Cercospora leaf spot (beet), DIV from a table in °F (the function takes °C)
write(expand_grid(t = seq(10, 35, 0.05), h = 0:24) |> mutate(div = calc_cercospora_div(t, h)), "cercospora_div_sweep")
write(build_cercospora(daily) |> select(date, div = dsv, avg2, avg7, total, severity), "cercospora_eau_claire_2025")

# Botrytis leaf blight (onion, BOTCAST)
write(expand_grid(t = seq(0, 32, 0.25), h = 0:24) |> mutate(dinfv = botcast_dinfv(t, h)), "botcast_dinfv_sweep")
write(
  expand_grid(hot = c(FALSE, TRUE), dry = c(FALSE, TRUE), h = 0:24) |> mutate(dinov = botcast_dinov(hot, dry, h)),
  "botcast_dinov_sweep"
)
write(build_botrytis(daily) |> select(date, dsi = dsv, total, severity), "botcast_eau_claire_2025")
