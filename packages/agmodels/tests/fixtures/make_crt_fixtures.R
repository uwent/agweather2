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

# Field crops: the daily inputs they read (beyond crt_daily) and each build over the year
write(
  daily |> select(date, temperature_mean, relative_humidity_min, relative_humidity_mean, relative_humidity_max,
                  dew_point_min, dew_point_depression_mean, dew_point_depression_max, wind_speed_max),
  "daily_more_eau_claire_2025"
)
write(build_tar_spot(daily) |> select(date, probability), "tar_spot_eau_claire_2025")
write(build_gray_leaf_spot(daily) |> select(date, probability), "gray_leaf_spot_eau_claire_2025")
write(build_don(daily) |> select(date, probability), "don_eau_claire_2025")
write(build_white_mold(daily, irrigated = FALSE) |> select(date, probability), "white_mold_dry_eau_claire_2025")
write(build_white_mold(daily, irrigated = TRUE, row_spacing = "30") |> select(date, probability), "white_mold_irrigated_30_eau_claire_2025")
write(build_white_mold(daily, irrigated = TRUE, row_spacing = "15") |> select(date, probability), "white_mold_irrigated_15_eau_claire_2025")
write(build_frogeye_leaf_spot(daily) |> select(date, probability), "frogeye_eau_claire_2025")
write(
  build_soybean_cercospora(daily) |> select(date, species, probability) |> pivot_wider(names_from = species, values_from = probability),
  "soybean_cercospora_eau_claire_2025"
)
write(
  build_red_crown_rot(daily, "2025-07-01") |> select(date, temperature_mean_rep, precipitation_veg, precipitation_rep, incidence),
  "red_crown_rot_r1_2025_07_01_eau_claire_2025"
)
write(
  build_wheat_scab(daily) |> select(date, resistance, probability) |> pivot_wider(names_from = resistance, values_from = probability),
  "wheat_scab_eau_claire_2025"
)
write(
  tibble(probability = seq(0, 1, 0.005)) |> mutate(
    risk_1_20_35 = as.integer(risk_from_prob(probability, 1, 20, 35)$risk) - 1,
    risk_1_5_10 = as.integer(risk_from_prob(probability, 1, 5, 10)$risk) - 1
  ),
  "risk_from_prob_sweep"
)

# Insects: degree days from the tool's sine, the key's severity and stage, and the end-of-season freeze, over the year
for (id in names(insect_models)) {
  m <- insect_models[[id]]
  write(
    build_insect(daily, m$tmin, m$tmax, m$key) |> select(date, gdd_f, cum_gdd, freezing, kill, severity, label),
    paste0("insect_", id, "_eau_claire_2025")
  )
}
