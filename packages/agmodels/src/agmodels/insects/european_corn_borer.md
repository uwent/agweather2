---
id: european-corn-borer
status: draft
updated: 2026-11-19
summary: Rates the risk from European corn borer moth flights from degree days since January 1, during a first flight from 550 to 900 degree days and a second from 1,660 to 2,190.
sources:
  - VDIFN's European corn borer model (the thresholds and both flight windows; the study behind them isn't identified)
  - University of Minnesota Extension, European Corn Borer in Minnesota Field Corn (first moths at about 374 degree days; compared)
  - Flandermeyer and Bick, Managing European Corn Borers in Wisconsin Corn Fields, UW–Madison Extension, 2025 (spray timing by degree days)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's European corn borer page (scouting and thresholds)
  - MSU Enviroweather's European corn borer model (compared)
---

## What it predicts

European corn borer caterpillars bore into the stalks, ear shanks and ears of field and sweet corn, and into peppers, snap beans and potatoes. Sprays work only before the caterpillars bore in, so timing matters. The model rates the risk from 0 (Very low) to 4 (Very high) during each of the two moth flights of a season, when moths are laying eggs:

- **First flight**: the moths that spent the winter as caterpillars in old stalks.
- **Second flight**: the moths from caterpillars that matured early in the summer.

## How it works

Degree days are counted from January 1 by the single-sine method, base 50 °F with a cutoff at 86 °F.

- **First flight:** from 550 to 900 degree days, peaking at 740.
- **Second flight:** from 1,660 to 2,190 degree days, peaking at 1,950.
- **The levels.** In each flight the level rises a level at a time from 0 at the start to 4 near the peak and falls back the same way to 0 at the end. It is Very high from about 677 to 793 degree days in the first flight and from about 1,853 to 2,030 in the second, and Very low between the flights.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

The numbers come from VDIFN, the vegetable forecasting tool AgWeather replaces. The study they were taken from hasn't been identified.

## How to read it

- Use the model's rising risk as a reminder to watch black light trap counts, which DATCP posts weekly, and to scout your own fields. Trap counts and scouting, not the model, decide whether to treat.
- **Field corn, first generation:** once corn is 18 inches tall, look for pinholes in the whorl leaves and count live caterpillars; UW–Madison's worksheet shows whether a spray will pay. UW–Madison times sprays against these caterpillars at about 800 to 1,000 degree days (base 50 °F), while they are still in the whorl.
- **Second generation:** UW–Madison times sprays at about 1,500 to 2,100 degree days, when egg masses are near hatching. Check late-planted fields weekly for egg masses near and above the ear.
- **Sweet corn:** in southern Wisconsin, start checking fresh-market plantings for egg masses by June 15, and treat through early silk if 5 % of plants have egg masses, caterpillars or feeding. For processing sweet corn, UW–Madison's thresholds are 25 % of plants infested in the whorl stage and 4 to 5 % from late tassel to silk.

The [European corn borer topic page](/topics/european-corn-borer) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The model hasn't been compared with Wisconsin's black light trap counts or with other models on the same weather. VDIFN lowered the level for freezes only from November.
- **The first flight may start late.** Minnesota's guide expects the first moths of the two-generation strain at about 374 degree days counted from March, well before the model's 550.
- **The second flight may start late too.** UW–Madison's spray window for the second generation opens at about 1,500 degree days, before the model's second flight begins at 1,660, though UW–Madison counts degree days by a slightly different method.
- MSU Enviroweather's model, counting from March 1 with no upper cutoff, puts the first flight at 450 to 950 degree days and the second at 1,450 to 1,950, and adds a third flight, which it doesn't expect in most years.
- In Wisconsin's northern counties corn borers usually have only one generation a year, but the model shows a second flight wherever the degree days reach it. In AgWeather's long-term averages (1996–2025), Rhinelander reaches the second flight around August 27 and its peak around September 20.
- The levels show where the season stands in each flight, not how many moths there are; both flights count alike.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
