# Rebuilds alfalfa_plan_tool.csv: the UW alfalfa tool's cut scheduler (`schedule_cut_dates` in
# tmp/R/alfalfa-tool/app/src/3_timing.R, copied below with its Shiny inputs made arguments) on a made-up season, for
# `test_alfalfa_plan.py`'s parity test of `agmodels.alfalfa_plan.schedule`.
#
#   Rscript packages/agmodels/tests/fixtures/make_alfalfa_plan.R
#
# The season: 2025, a day's GDD 22 sin(pi (yday - 75) / 230) (none outside, none after day 305), the last spring
# killing freeze on day 100 (GDD count from day 101), and a fall chance of a killing freeze rising from 0 on day 270
# to 1 on day 320, so the tool's season end (the first day at 10 % or more) is day 275.

suppressPackageStartupMessages(library(dplyr))

best_divisions <- function(gdd_length, target) {
  r <- gdd_length / target
  cands <- sort(unique(pmax(1, c(floor(r), ceiling(r)))), decreasing = TRUE)
  cands[which.min(abs(gdd_length / cands - target))]
}

# The tool's function, verbatim but for `req(input$year)` (cur_yr) and `rv$held` (held), now arguments, and its
# end day and GDD returned beside the cut days
schedule_cut_dates <- function(df, cur_yr, held, gdd_interval = NULL, target_cuts = NULL) {
  gdd_on <- function(yd) df$gdd_since_kill[which.min(abs(df$yday - yd))]
  day_at <- function(gdd) df$yday[which.min(abs(df$gdd_since_kill - gdd))]
  held <- sort(held)
  last_df <- df |> filter(yday > 180, date >= last_kill)
  possible_cut <- last_df |> filter(gdd_since_kill >= 800, between(kill_by, 0.1, 0.25))
  end_gdd <- if (nrow(possible_cut) > 0) {
    end_gdd <- min(possible_cut$gdd_since_kill)
  } else {
    max(df$gdd_since_kill)
  }
  pts <- sort(unique(c(0, vapply(held, gdd_on, numeric(1)), end_gdd)))
  seg_lo <- head(pts, -1)
  seg_hi <- tail(pts, -1)
  seg_len <- seg_hi - seg_lo
  n_seg <- length(seg_len)
  is_tail <- seq_len(n_seg) == n_seg
  if (!is.null(target_cuts)) {
    divs <- rep(1L, n_seg)
    for (j in seq_len(max(0, target_cuts - n_seg))) {
      i <- which.max(seg_len / divs)
      divs[i] <- divs[i] + 1L
    }
  } else {
    divs <- vapply(seq_len(n_seg), function(i) {
      if (is_tail[i] && seg_len[i] < 360) return(0L)
      as.integer(best_divisions(seg_len[i], gdd_interval))
    }, integer(1))
  }
  gdd_cuts <- unlist(lapply(seq_len(n_seg), function(i) {
    if (divs[i] < 1) return(NULL)
    steps <- if (is_tail[i]) seq_len(divs[i]) else seq_len(divs[i] - 1)
    seg_lo[i] + seg_len[i] * steps / divs[i]
  }))
  end_day <- day_at(end_gdd)
  gen_days <- if (length(gdd_cuts)) vapply(gdd_cuts, day_at, numeric(1)) else numeric(0)
  gen_days <- gen_days[between(gen_days, 60, end_gdd)]
  days <- sort(unique(c(held, gen_days)))
  list(days = days, end_day = end_day, end_gdd = end_gdd)
}

yday <- 1:365
gdd <- pmax(0, 22 * sin(pi * (yday - 75) / 230))
gdd[yday > 305] <- 0
kill_day <- 100
gdd_since <- cumsum(gdd)
after <- yday > kill_day
gdd_since[after] <- cumsum(gdd[after])
gdd_since[yday == kill_day] <- 0
kill_by <- ifelse(yday < 200, 0, pmin(1, pmax(0, (yday - 270) / 50)))
dates <- as.Date("2025-01-01") + yday - 1
df <- tibble(
  date = dates,
  yday = yday,
  gdd = gdd,
  gdd_since_kill = gdd_since,
  kill_by = kill_by,
  last_kill = if_else(yday >= kill_day, as.Date("2025-01-01") + kill_day - 1, as.Date("2025-01-01"))
)

cases <- list(
  list(name = "interval 800", held = integer(0), interval = 800),
  list(name = "interval 900", held = integer(0), interval = 900),
  list(name = "interval 1000", held = integer(0), interval = 1000),
  list(name = "interval 1100", held = integer(0), interval = 1100),
  list(name = "interval 1200", held = integer(0), interval = 1200),
  list(name = "count 2", held = integer(0), count = 2),
  list(name = "count 3", held = integer(0), count = 3),
  list(name = "count 4", held = integer(0), count = 4),
  list(name = "count 5", held = integer(0), count = 5),
  list(name = "count 6", held = integer(0), count = 6),
  list(name = "held 160, interval 1000", held = c(160L), interval = 1000),
  list(name = "held 150 and 205, interval 1000", held = c(150L, 205L), interval = 1000),
  list(name = "held 150 and 205, count 5", held = c(150L, 205L), count = 5),
  list(name = "held 262, interval 1000", held = c(262L), interval = 1000),
  list(name = "held 140, count 4", held = c(140L), count = 4)
)

rows <- lapply(cases, function(k) {
  found <- schedule_cut_dates(df, 2025, k$held, gdd_interval = k$interval, target_cuts = k$count)
  tibble(
    case = k$name,
    held = paste(k$held, collapse = " "),
    interval = if (is.null(k$interval)) NA else k$interval,
    count = if (is.null(k$count)) NA else k$count,
    end_day = found$end_day,
    days = paste(found$days, collapse = " ")
  )
})
out <- bind_rows(rows)
here <- dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)))
write.csv(out, file.path(here, "alfalfa_plan_tool.csv"), row.names = FALSE)
write.csv(select(df, yday, gdd), file.path(here, "alfalfa_plan_season.csv"), row.names = FALSE)
print(as.data.frame(out))
