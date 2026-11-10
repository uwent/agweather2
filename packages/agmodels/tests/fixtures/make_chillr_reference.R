# Writes chillr_reference.csv: chillR's own Dynamic, Utah and chilling-hours models on a synthetic fall and winter
# of hourly temperatures, for agmodels.chill's parity test. chillR needn't be installed: its model functions are
# plain R, sourced from the package's source (temp_models.R, chillR 0.75 from CRAN's archive):
#   curl -LO https://cran.r-project.org/src/contrib/Archive/chillR/chillR_0.75.tar.gz && tar xzf chillR_0.75.tar.gz
#   Rscript packages/agmodels/tests/fixtures/make_chillr_reference.R chillR/R/temp_models.R \
#     packages/agmodels/tests/fixtures/chillr_reference.csv
args <- commandArgs(trailingOnly = TRUE)
source(args[1])
hours <- 0:(24 * 120 - 1)  # 120 days from October 1
day <- hours %/% 24
# A cooling season with a daily cycle, a warm spell (days 40-44) that undoes chill, and freezing nights later
temp <- 14 - 0.12 * day + 7 * sin(2 * pi * ((hours %% 24) - 9) / 24)
warm <- day >= 40 & day <= 44
temp[warm] <- temp[warm] + 12
temp <- round(temp, 1)
out <- data.frame(
  hour = hours,
  temperature_c = temp,
  dynamic_cumulative = Dynamic_Model(temp),
  utah_cumulative = Utah_Model(temp),
  chill_hours_cumulative = Chilling_Hours(temp)
)
write.csv(out, args[2], row.names = FALSE)
