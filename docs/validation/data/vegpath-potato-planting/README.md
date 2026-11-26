# Potato planting and emergence dates at Wisconsin's potato areas, 2020–2026

The early, mid and late potato planting dates and their 50 % emergence dates that UW Vegetable Pathology's Vegetable Crop Updates give each season, in the early and late blight table, at seven Wisconsin potato areas. We use them to fit `potato-stages`' emergence threshold and potato's typical planting dates on the grid (`agdata.potatoplanting`), and to check both ([report](../../models/potato-stages.md)).

## File

`dates.csv`, one row per planting (120 rows: 12 a year in 2020–2022, 21 a year in 2023–2026):

- `year`, `location`: the season and the place as the newsletter names it (Spring Green, Arlington, Grand Marsh, Hancock, Plover, Antigo, Rhinelander).
- `lat`, `lng`: a cultivated field near the place, chosen by Ben Bradford (about 0.01°), where we read the grid.
- `planting`: `early`, `mid` or `late`, as the table gives them.
- `planting_date`, `emergence_date`: the dates in the table.

## Source

Compiled by Ben Bradford from the Vegetable Crop Updates (vegpath.plantpath.wisc.edu), 2020–2026, in November 2026 (`potato_dates.xlsx`, sheet Dates; sheet Locations gives the fields). The CSV is the sheet as written, dates as ISO dates.

## Caveats

- The planting dates come from growers' reports and the emergence dates are the newsletter's estimates, not counts in fields. The plans note that the newsletter's numbers come from the old AgWeather and VDIFN; whether that includes the emergence dates isn't recorded.
- The tiers are the newsletter's, not percentages of the area planted: they come earlier than NASS's crop progress percentages for Wisconsin.
- 2020–2022 have fewer places (12 rows a year) than 2023–2026 (21).
- All seven places are in Wisconsin, from Spring Green (43.2° N) to Rhinelander (45.7° N).
