---
id: apple-scab
status: draft
updated: 2026-11-18
sources:
  - Gadoury and MacHardy 1982 (ascospore maturity by degree days)
  - Stensvand, Eikemo, Gadoury and Seem 2005 (maturity from green tip, the dry-spell rule, the end of the primary season)
  - MacHardy and Gadoury 1989 (the Revised Mills table of wet hours for infection)
  - Gadoury et al. 2004 (maturity and trapped ascospore release)
  - NEWA's apple scab model (infection periods, ascospore release; compared)
  - Leaf wetness sensors at NEWA's Wisconsin orchard stations, 2024–2026 (the wetness estimate)
  - Enviroweather's apple scab model (compared)
---

## What it predicts

In spring, apple scab spreads by ascospores, spores that mature over several weeks and are released by rain. They infect the tree when it stays wet long enough at the temperature of the time. Growers time scab sprays by these infection periods. From green tip until the season's ascospores are spent, the model shows:

- **Infection periods**: the days on which a wet period lasted long enough, at its mean temperature, for ascospores to infect. The risk is Infection on those days and Low on the others.
- **The wet period**: its wet hours and mean temperature, so you can see how close a period came to an infection.
- **Ascospores mature**: the estimated share of the season's ascospores that are ready to be released.
- **Ascospores released**: the estimated share released so far, and on each day.
- **The primary season**: whether ascospores remain to be released. Once the season is over, the model stops.

## How it works

- **Green tip starts the season.** Green tip is when green leaf tissue shows at the tips of half the McIntosh buds. The model takes it from the apple stages model, at 101 degree days (base 43 °F) from January 1, or from your own date at a location. On the map, each location starts at its own estimated green tip.
- **Ascospore maturity.** Maturity follows Gadoury and MacHardy's curve (1982), counted from green tip as Stensvand and others (2005) recommend. It uses degree days above 32 °F (0 °C) from each day's mean temperature: half the season's ascospores are mature after about 450 degree days (250 above 0 °C), and 95 % after about 760 (420). After 7 dry days in a row, with under 0.008 inch (0.2 mm) of rain each, the count stops until the next rain (Stensvand et al. 2005).
- **Release.** Rain releases mature ascospores. We follow NEWA's daily estimate, for which no published source was found: rain from 8 p.m. to 6 a.m. CST releases 5 % of the mature ascospores not yet released. Rain from 7 a.m. to 7 p.m. then releases 90 % of those left if it totals at least 0.1 inch and its rainy hours average at least 50 °F, 50 % if one of those holds, and 25 % if neither. An hour counts as rainy with 0.01 inch or more.
- **The end of the primary season.** The season ends once ascospores are 95 % mature and a daytime rain of more than 0.1 inch falls with its rainy hours above 50 °F, which releases the rest (Stensvand et al. 2005). If that hasn't happened by 2,340 degree days above 32 °F (1,300 above 0 °C) after green tip, the latest such release in 16 seasons Stensvand and others trapped, the season ends then.
- **Wet hours.** We have no leaf wetness sensors, so we estimate wetness from the weather: an hour counts as wet when the relative humidity is 90 % or more or at least 0.01 inch of rain falls. We chose this estimate by comparing several with the leaf wetness sensors at NEWA's Wisconsin orchard stations from 2024 to 2026.
- **Infection periods.** A wet period begins with an hour of rain and continues while hours stay wet. Periods less than 24 hours apart join into one, adding their wet hours but not the dry hours between. An infection occurs when the wet hours reach the number in the Revised Mills table (MacHardy and Gadoury 1989, as NEWA tabulates it) for the period's mean temperature: for example, 41 hours at 34 °F, 11 at 50 °F, 8 at 55 °F, 6 from 61 to 76 °F and 11 at 79 °F. Outside 34–79 °F the table gives no infection.

This is NEWA's apple scab model, the Cornell system many Wisconsin growers use, with these differences. NEWA reads wetness from each station's leaf wetness sensor, where we estimate it. NEWA approximates Gadoury and MacHardy's curve closely and starts it a day before green tip. We mark an infection on the day the wet hours reach the table, where NEWA marks the days the wet period starts and ends. Our days run from midnight to midnight CST; NEWA's follow the local clock. NEWA continues to report infection periods through the summer; we show only the primary season.

## How to read it

- An infection period means the weather allowed ascospores to infect during that wet period. Whether it matters in your orchard depends on whether your trees were protected when it began; follow your fruit pest management guide for products and timing.
- Enter your own green tip date at your location. The model then starts on your date instead of the degree-day estimate, which matters most after a warm March.
- The model covers only primary infections by ascospores. After the primary season it stops, and secondary infections in summer by conidia, a second kind of scab spore, aren't modelled.
- There is one level of infection; the light, moderate and heavy grades some other tools give aren't used.

## Validation and caveats

- Draft (model version 0.1, beta). The maturity curve was developed in New Hampshire and Norway and the Revised Mills table in New Hampshire. Infection periods haven't been checked against scab that appeared in Wisconsin orchards.
- We checked that we reproduce NEWA's results exactly from its published rules, then compared our model with NEWA's on Wisconsin orchard stations: on the stations' own weather, ours found 85 % of NEWA's infection periods.
- The wetness estimate found about three in four of the infection periods the orchard sensors gave and added others, so the model tends to show more infection periods than a sensor in your orchard would.
- After a warm late winter, the degree-day green tip can come weeks before buds move (101 degree days came on March 14, 2024 at Eau Claire), so the season and its first infection periods may open too early. Your own green tip date fixes this at a location; the map can't.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your orchard. Rain comes from radar combined with rain gauges, which can miss a local shower.
