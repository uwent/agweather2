# Weather totals over a period

Totals over a period at one or more locations: precipitation, reference evapotranspiration (ET0), water balance (precipitation minus ET0), sunlight, and counts of hours such as those with relative humidity of 90% or more. Each row is one location, with each variable's total, and how many of its days were estimated or missing.

Every total except precipitation bridges gaps of up to seven days with an estimate from the days around them, counted in `<variable>_estimated_days` (`gaps=missing` turns this off). Precipitation is never estimated: a missing day is counted in `precipitation_sum_missing_days` and adds nothing to the total, so check that count before relying on a total. Water balance combines the two rules: a day without precipitation data counts as no rain, and ET0 is bridged as in its own total. Both kinds of day are counted in `water_balance_estimated_days`, and a day still without an ET0 value is left out and counted in `water_balance_missing_days`.

You can also count days or hours within bounds, such as the days with a high of 86 °F or more (`count=air_temperature_max:days_above_86`) or the hours between 50 and 86 °F (`count=air_temperature:hours_between_50_86`), and with `interval=month` get a row for each month. Counts are never estimated: days or hours without a value are left out and counted in the count's `_missing_days` or `_missing_hours` column.

To find dates, `first=air_temperature_min:frost` gives each location's first frost (32 °F or colder) since July 1, `last=` the last such day, and `since=` the days since it; `hard_freeze` (28 °F) and `killing_freeze` (24 °F) are the other named temperatures, and any daily variable takes bounds, such as `first=soil_temperature_10cm_mean:above_50`. Only measured days count.
