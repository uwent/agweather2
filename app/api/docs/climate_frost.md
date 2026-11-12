# Freeze dates and season length

The typical dates of the last spring freeze and the first fall freeze at one or more locations, and the length of the frost-free season between them, from the past 30 years unless you choose a shorter period. A freeze is a day whose minimum temperature reached the threshold: 32, 28 and 24 °F unless you choose others.

Each row is one location and threshold. For each probability in `probabilities` (10, 50 and 90% by default):

- `last_spring_p10` is the date by which 10% of the years had had their last spring freeze (January through June). In the other 90%, a freeze came later. `last_spring_p90` is a date by which only one year in ten still had a freeze to come, and is a cautious planting date.
- `first_fall_p10` is the date by which 10% of the years had had their first fall freeze (July through December). Only one year in ten froze earlier.
- `season_days_p10` is the frost-free season's length, from the last spring freeze to the first fall freeze, that 10% of the years were at or under.

The dates are given in this year. A date is empty where too many years had no freeze at all in that season to set it, such as a 24 °F freeze near a lake. `years_without_spring` and `years_without_fall` count those years, and `years_spring` and `years_fall` count the years with enough data to be included.

The freeze dates are worked out from each year's daily minimum temperatures. Our grid's daily minimum is the lowest of the hourly readings. Low spots such as valleys and frost pockets can freeze earlier in fall and later in spring than the grid cell around them. The dates are guidance, not a guarantee for any one year. `/climate/frost/chances` gives the chance of a freeze for every date.

Freeze dates are available only inside the area we cover.
