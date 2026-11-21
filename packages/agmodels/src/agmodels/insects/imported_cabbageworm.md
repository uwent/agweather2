---
id: imported-cabbageworm
status: draft
updated: 2026-11-21
summary: Times the cabbage white butterfly's flights, egg laying and imported cabbageworm caterpillar feeding from degree days since January 1, for each generation through the season, and marks when to scout for eggs and young caterpillars.
sources:
  - Delahaut, Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087), UW–Madison Extension (the method and the spring flight)
  - Tatchell 1981 (caterpillar development by temperature, in the laboratory; as UC IPM's model database gives it)
  - Liesch and Groves, Imported Cabbageworm, UW–Madison Division of Extension, and UW Vegetable Entomology's imported cabbageworm page (development times, flights and generations in Wisconsin)
  - iNaturalist records of cabbage white butterflies in Wisconsin, 2016–2026 (the timing of later flights; compared)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (scouting and thresholds)
---

## What it predicts

The imported cabbageworm is the caterpillar of the cabbage white butterfly, and the most important caterpillar pest of cole crops in Wisconsin. Butterflies come out of overwintering chrysalises in spring and lay eggs on cruciferous weeds and early cole crops; later generations feed on planted crops through the summer. The model follows each generation:

- **Adult flight**: how many butterflies are emerging, compared with the spring flight's peak.
- **Eggs**: eggs laid and not yet hatched.
- **Larval feeding**: caterpillars feeding on the crop. This is the risk.
- **Scout for eggs and young caterpillars**: the days from 10 % to 90 % of each generation's eggs hatched, when small caterpillars are appearing.

Risk follows the caterpillars, not the butterflies. A risk of 1 means as many caterpillars feeding as at the spring generation's peak.

## How it works

Degree days are counted from January 1 by the modified average method, base 50 °F with a cutoff at 86 °F: a day's low is raised to 50 °F and its high capped at 86 °F before they are averaged. This is the modified method in UW–Madison Extension's guide to calculating degree days, the companion to its degree-day table (Delahaut's XHT1087).

- **The spring flight.** UW–Madison's table puts the butterflies at 150 to 240 degree days. In the model, a tenth of the spring flight has emerged by 150 and half by 240; it peaks at about 210.
- **Eggs and caterpillars.** Females lay eggs over the days after they emerge (the model centers egg laying about 5 days after, our estimate), and the eggs hatch in about 5 days, about 105 degree days. The caterpillars then feed for about 350 degree days, two to three weeks in summer, as measured in the laboratory (Tatchell 1981).
- **Later generations.** Each generation follows the last about 840 degree days later. From one flight to the next, development times (egg laying, egg, caterpillar and chrysalis) add up to about 740 to 820 degree days; Wisconsin's iNaturalist records of cabbage white butterflies show flights about 840 apart, and the model follows them. There's no fixed number of generations: the season's warmth decides, and fall freezes end it.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In an average year (AgWeather's degree days for 1996 to 2025), the spring flight begins in late April at Arlington and early May at Rhinelander, and is half over by about May 10 in the south and May 20 in the north. Its caterpillars peak in mid- to late June. The second flight comes in early July in the south and mid-July in the north, with caterpillars peaking in late July in the south and early August in the north; a third flight follows in mid-August in the south and early September in the north.

## How to read it

- **Scout weekly through the season,** whatever the model shows. Walk a W-shaped path, examine 25 to 50 plants, and count a plant as infested if it has eggs or caterpillars of the imported cabbageworm, the cabbage looper or the diamondback moth.
- **Use the scouting window** to watch for eggs and newly hatched caterpillars. Insecticides, including _Bacillus thuringiensis_, work best on small caterpillars with good coverage of the leaves.
- **Treat by the share of infested plants.** For cabbage, Commercial Vegetable Production in Wisconsin gives 10 % in the seedbed, 30 % from transplanting to cupping, 20 % from cupping to early head and 10 % at mature head; for broccoli and cauliflower, 10 % in the seedbed, 50 % from transplanting to the first flower bud or curd, and 10 % after.
- **The second generation does the most damage,** by UW–Madison's account: nearly all of its caterpillars grow up on planted cole crops. The model rates every generation alike, so give the July and August windows close attention.

The [imported cabbageworm topic page](/topics/imported-cabbageworm) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The spring flight comes from UW–Madison's degree-day table for Wisconsin; caterpillar development was measured in the laboratory in England.
- **Butterflies in Wisconsin.** On the same degree days, iNaturalist records of cabbage white butterflies in Wisconsin (2016 to 2026, corrected for how many people were looking) put the middle of the spring flight at 234 degree days, against the model's 239. The time between later flights was set from the same records, so their agreement there isn't an independent test.
- **The second flight may come earlier than UW–Madison describes.** In an average year the model's second flight comes in early July in southern Wisconsin, a week or two before UW's mid-July; the iNaturalist records agree with the model.
- **Some steps are estimates.** UW–Madison's table doesn't say which part of the flight its 150 to 240 degree days cover, and the timing of egg laying, the egg and the chrysalis comes from development times in days, converted to degree days.
- Every generation counts alike in the risk, though UW–Madison says the second does the most damage.
- The model hasn't been compared with counts of caterpillars in fields.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
