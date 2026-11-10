# Chill

Winter chill at one or more locations, from hourly temperatures: the chill that fruit trees and other woody plants need over the winter before their buds can break normally in spring. Each row is one location and day: that day's chill (`chill`), the total since `start` (`chill_total`), and how many of the day's hours had no temperature (`missing_hours`). The period starts on the October 1 before the end date unless you choose another `start`.

Choose how chill is counted with `method`:

- `dynamic` (the default): chill portions from the Dynamic model (Fishman, Erez and Couvillon, 1987; Erez and others, 1990). Cool hours build up chill that warm hours can still undo, until enough has built up to become a permanent portion. It describes chill in mild winters better than the older methods, and is the method most current research uses. The model starts at zero on `start`.
- `utah`: Utah chill units (Richardson, Seeley and Walker, 1974). Each hour counts from −1 to 1 by its temperature: most for 36.5–48.4 °F (2.5–9.1 °C), less for cooler or slightly warmer hours, and warm hours above 60.6 °F (15.9 °C) count against the total, so it can fall.
- `hours`: chill hours, the hours between 32 and 45 °F (0 and 7.2 °C), or between the two temperatures you give in `bounds`.

Which method fits depends on the crop and the region: requirements published for a variety are given in one of these units, and the numbers don't convert from one to another. A day with any hour missing has no value of its own (`chill` is empty); the total adds the hours that day has, and `missing_hours` shows how many were left out. Values are calculated from our hourly weather data and the forecast; they are an estimate for the location, not a measurement in your orchard.
