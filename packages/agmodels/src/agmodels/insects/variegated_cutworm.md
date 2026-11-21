---
id: variegated-cutworm
status: draft
updated: 2026-11-21
summary: Times variegated cutworm's two moth flights and the caterpillars from each from degree days since January 1, and marks when to scout for eggs and young caterpillars after each flight's peak.
sources:
  - Simonet, Clement, Rubink and Rings 1981 (development times and 15 years of light-trap catches, Ohio)
  - Wisconsin DATCP black light trap network, 2020–2026 (the first flight's spread; compared)
  - MSU Enviroweather's variegated cutworm model (compared)
---

## What it predicts

Variegated cutworm caterpillars cut seedlings and transplants, climb larger plants to eat foliage, buds and flowers, and chew holes in tomatoes and other fruit. They feed at night and hide in the soil by day. Outbreaks are sporadic. The model follows two generations through the season:

- **Adult flight**: how many moths are flying, compared with the first flight's peak.
- **Larvae**: how many caterpillars are feeding, timed from the moths of each flight. This is the risk, from 0 to 1, where 1 means as many caterpillars as at the first generation's peak.
- **Scout for eggs and young caterpillars**: the days from each flight's peak until 95 % of its moths have flown.

## How it works

Degree days are counted from January 1 by the single-sine method, base 45 °F with no upper cutoff, as Simonet and others (1981) counted them for 15 years of black light trap catches at Wooster, Ohio.

- **Two flights.** The first moths of the year (the overwintering generation) fly from late spring, peaking at about 900 degree days. The next generation's moths peak about 1,260 degree days later, at about 2,160, the peaks Simonet and others found at Wooster. The study doesn't give the flights' spread, so the first flight's start and end are set roughly from DATCP's Wisconsin trap catches.
- **Caterpillars.** Females begin laying eggs about a week after they emerge in summer, and eggs hatch about 320 degree days after the moths emerge. The caterpillars then feed for about 645 degree days before pupating (Simonet and others, from laboratory rearing).
- **No third flight.** A third generation would peak near 3,400 degree days, after most Wisconsin seasons end.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In AgWeather's long-term averages (1996–2025), the first flight peaks around June 14 at Arlington, June 18 at Hancock and June 25 at Rhinelander, and the second around August 2, August 8 and August 22. Caterpillars of the first generation are most numerous around July 10, July 14 and July 24.

## How to read it

- **Scout after each flight's peak.** Simonet and others suggest starting to look for eggs and young caterpillars at peak moth capture. Check stems and the undersides of leaves for egg masses, and the soil around plants for caterpillars, which feed at night and hide by day.
- **Use traps where you can.** Black light or pheromone traps near your fields show whether moths are present this year; moth counts in Wisconsin's black light traps are usually low.
- Outbreaks are sporadic, so a high level in the model means caterpillars could be present if moths laid eggs nearby, not that they will be.

The [variegated cutworm topic page](/topics/variegated-cutworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The flight peaks and development times come from Ohio light traps and laboratory rearing.
- The flights peak at Simonet and others' 900 and 2,160 degree days. In Wisconsin's black light traps from 2020 to 2026, half the first flight's moths were caught by about 1,070 degree days, later than the model's 890, and half the second flight's by about 2,060, earlier than the model's 2,150. Only 273 moths were caught in those seven years, so these comparisons are rough.
- The study measured each stage's development above a different base temperature. We converted them to the model's 45 °F base for a day averaging about 68 °F, so the caterpillars' timing is approximate in cooler or hotter weather. The study also doesn't say how it computed daily degree days; the model assumes the single-sine method.
- Simonet and others found flights hard to predict from temperature alone, and the moths may spend the winter at more than one stage. The model times the flights; it can't say whether a damaging population will appear.
- Another model, from peppermint fields in Oregon (Coop and Berry), uses different temperature thresholds (41 and 88 °F); AgWeather uses the Ohio study's, which counted moths in the Midwest.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
