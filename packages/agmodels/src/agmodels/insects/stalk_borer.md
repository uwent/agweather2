---
id: stalk-borer
status: draft
updated: 2026-11-23
summary: Times stalk borer caterpillars moving from grasses and weeds into corn from degree days since January 1, and marks the window to scout field borders and treat if needed.
sources:
  - Lasack and Pedigo 1986 (caterpillars moving into corn, Iowa, 1984–1985)
  - Lasack, Bailey and Pedigo 1987 (caterpillar development in the same Iowa fields; how closely it follows degree days)
  - Rice and Davis 2010 (stalk borer ecology and management; scouting and spray timing)
  - Iowa State University Extension, Stalk Borer (10 % of caterpillars moving at 1,400 degree days)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025 (movement from about 1,110 to a peak at about 1,650; scouting and spray timing)
  - Levine 1983 (development by temperature, base 41 °F)
---

## What it predicts

Stalk borer caterpillars hatch in spring in grasses and weeds. When they outgrow those stems, or when the weeds are killed, they move into nearby corn and tunnel into the stems, usually in the first rows beside grassy field edges and waterways. Sprays work only while caterpillars are moving and before they bore in, so the useful question is when that move happens. The model gives:

- **Caterpillars moving into corn**: how many are on the move, compared with the peak. This is the risk, from 0 to 1.
- **Scout corn borders and treat if needed**: the days from about 1,300 to 1,700 degree days, when UW–Madison and Iowa State advise scouting border rows and, if needed, spraying.

## How it works

Degree days are counted from January 1 by the single-sine method, base 41 °F with no upper cutoff, the method of the studies behind the numbers (Levine 1983).

- **Movement.** In two Iowa fields in 1984 and 1985, caterpillars were first caught moving from grassy areas into corn at about 1,100 degree days, and half had moved by about 1,590 to 1,630; little movement was seen after about 2,000 (Lasack and Pedigo 1986). UW–Madison's guide and a later review round the middle to 1,650. Iowa State puts 10 % at 1,400. The model's curve follows these: 10 % at about 1,390, half at about 1,650, nearly all by about 2,020.
- **The window** opens when about 3 % have moved, at about 1,290 degree days, and closes when about 60 % have, at about 1,700.
- **One generation a year.** The moths fly from August to October and lay the eggs for next spring; the model covers only the caterpillars' move into corn.

In AgWeather's long-term averages (1996–2025), the window opens around June 19 at Arlington, June 23 at Hancock and July 1 at Rhinelander, half the caterpillars have moved around July 1, July 6 and July 15, and the window closes around July 3, July 8 and July 17.

## How to read it

- **Scout border rows when the window opens.** Look for caterpillars in the whorls and frass in the whorl or at entry holes, starting with field edges next to grassy borders, and check the whole field where grassy weeds were widespread last year (A3646, Iowa State).
- **If a spray is needed, apply it inside the window**, while caterpillars are moving. Once they are inside the stem, sprays don't reach them. UW–Madison's field crops guide gives thresholds by leaf stage, corn price and expected yield; plants are unlikely to be killed once they reach about the seventh leaf.
- **Check last year's weed patches earlier.** Caterpillars that hatch in weeds inside a field start feeding on corn earlier; A3646 suggests checking those patches from about 900 to 1,000 degree days.

The [stalk borer topic page](/topics/stalk-borer) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The timing comes from Iowa field studies and the extension guides that use them; the model reproduces their numbers but hasn't been compared with observations in Wisconsin.
- The sources differ a little on the middle of the move: about 1,590 to 1,630 degree days in the Iowa study's two years, 1,650 in UW–Madison's guide and 1,700 in Iowa State's table. The model's 1,650 sits between them.
- **Degree days time the move only roughly.** In the Iowa fields, a cool, wet spring delayed hatch, and the older caterpillars kept closer to the calendar than to degree days (Lasack, Bailey and Pedigo 1987). In a warm spring, some caterpillars moved well before 1,400 degree days. Scout border rows by what you find, not only by the model's dates.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
