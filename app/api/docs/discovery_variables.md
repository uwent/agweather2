# Weather variables

Every weather variable the service provides, hourly and daily, with its name, description, unit and the precision it is stored to. Use these names in the `vars` parameter and to set one variable's unit (as `precipitation=mm`).

A daily variable also says how it is computed from the hourly data, for example the day's maximum of hourly air temperature, or the number of hours with relative humidity of 90% or more. Days follow the location's own calendar. The dates each variable covers are given by `/status`.

A few variables are calculated from others each time you ask for them, rather than stored. Water balance is one: the day's precipitation minus its reference evapotranspiration (ET0), positive when rain exceeded what a well-watered grass crop would use and negative when it fell short. `computed_from` lists the variables each one is calculated from, and it is missing on any day one of them is missing.
