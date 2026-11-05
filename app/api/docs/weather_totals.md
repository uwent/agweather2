# Weather totals over a period

Totals over a period at one or more locations: precipitation, reference evapotranspiration (ET0), sunlight, and counts of hours such as those with relative humidity of 90% or more. Each row is one location, with each variable's total, and how many of its days were estimated or missing.

Every total except precipitation bridges gaps of up to seven days with an estimate from the days around them, counted in `<variable>_estimated_days` (`gaps=missing` turns this off). Precipitation is never estimated: a missing day is counted in `precipitation_sum_missing_days` and adds nothing to the total, so check that count before relying on a total.
