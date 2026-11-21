---
id: western-bean-cutworm
status: draft
updated: 2026-11-21
summary: Times the western bean cutworm moth flight and the egg masses that follow from degree days since March 1, on Hanson et al.'s 2015 model, which NEWA also uses, and marks when to scout corn for egg masses.
sources:
  - Hanson, Moon, Wright, Hunt and Hutchison 2015 (the degree-day method and the flight model, from Nebraska black light traps)
  - NEWA's western bean cutworm model, Cornell University (the same model; compared)
  - Wisconsin DATCP western bean cutworm pheromone and black light trap networks, 2020–2026 (compared)
  - UW–Madison, Pest Management in Wisconsin Field Crops (A3646), 2025, and UW Vegetable Entomology's western bean cutworm page (egg development, scouting and thresholds)
---

## What it predicts

Western bean cutworm has one generation a year. The moths emerge from the soil in summer and lay egg masses on corn just before tasseling; the caterpillars feed in corn ears and in dry bean pods. Sprays work only before the caterpillars get into the ear, so finding egg masses in time is what matters. The model follows the season from degree days:

- **Adult flight**: how much of the season's moth flight has happened, and how many moths are flying compared with the peak.
- **Egg masses**: how many egg masses are in fields, compared with their peak. This is the risk to the crop.
- **Scout corn for egg masses**: the days from the first moths (5 % of the flight) until most have flown (90 %).

## How it works

Degree days are counted from March 1 by the simple average method, base 38 °F, with the day's average temperature capped at 75 °F: a day averaging 80 °F counts as 75. This is the method Hanson and colleagues found predicted the flight best in 2015, from black light trap catches at four sites in Nebraska, 1981–2009. NEWA (the Network for Environment and Weather Applications at Cornell University) uses their model too.

- **The flight.** The model follows their flight curve: 5 % of the moths have flown by about 2,400 degree days, a quarter by about 2,560, half by about 2,705, three quarters by about 2,850 and 90 % by about 2,980.
- **Egg masses.** Eggs hatch 5 to 7 days after they're laid (UW–Madison). No study gives the time from a moth's emergence to egg laying in degree days, so the model starts each moth's eggs on the day it emerges and counts them as present for about 200 degree days, six days at the usual late-July rate, so egg masses peak about 80 degree days after the middle of the flight.
- **Scouting window.** The window runs from 5 % to 90 % of the flight, about 2,400 to 2,980 degree days, which covers UW–Madison's advice to scout from the first moths until 7 to 10 days after the peak.

On the 1996–2025 normals, half the moths have flown by about July 27 at Arlington, August 2 at Hancock and August 13 at Rhinelander. These are long-term averages: the flight comes earlier in a warm year and later in a cool one.

## How to read it

- **Traps first.** Set pheromone traps at field edges by July 1 and check them at least weekly. DATCP's trap network posts counts and maps across Wisconsin. Your own traps tell you whether moths are in your area at all; the model tells you when the flight is likely to be under way.
- **When to scout:** start when the window opens, or when the first moths are caught nearby, and keep going until the window closes.
- **How to scout:** check 20 plants in a row at five places, looking at the top leaves and the leaves around the ear for egg masses and small caterpillars. Scout tasseling fields first.
- **Thresholds:** consider a spray when 5 % of field corn plants, or 4 % of processing sweet corn plants, have egg masses or small caterpillars. Time it before the caterpillars reach the silks.

The [western bean cutworm topic page](/topics/western-bean-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.3, beta). The flight model was fitted in Nebraska. Version 0.3 replaced an older model that counted from May 1 with a different method; on the normals the two put half the flight within a few days of each other.
- Against DATCP's Wisconsin pheromone traps, 2021–2026 (286 trap-years), the model's date for half the flight fell a median 3 days before the end of the week in which half the season's moths were caught, inside that week in about half the trap-years and within a week of it in almost all. Pheromone traps catch only males, and the model was fitted to black light traps, which catch both. On DATCP's fewer black light traps, the model ran a median 2 days late.
- NEWA's model, run on the weather of Wisconsin's NEWA stations, puts half the flight a median 3 days later than ours. Its program caps each day's high temperature at 75 °F, where the published method caps the day's average, and so counts fewer degree days on hot days.
- The time eggs take to hatch is given in days, not degree days, so the egg mass curve is an estimate.
- Moths can fly in from elsewhere on storms and winds, which no degree-day model can predict. Confirm the flight with traps before scouting.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
