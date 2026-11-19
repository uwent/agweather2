---
id: japanese-beetle
status: draft
updated: 2026-11-19
summary: Rates the risk of feeding by Japanese beetle adults from degree days since January 1, from first emergence at about 970 degree days through peak feeding at about 1,600 to the end of feeding at about 2,150.
sources:
  - VDIFN's Japanese beetle model (the threshold and the window; the source of its numbers isn't documented)
  - Coop and Barker, Japanese beetle phenology and degree-day model, Oregon IPM Center, Oregon State University (adult emergence by degree days, with a 92 °F cutoff; compared)
  - Williamson, Liesch and Pandian, Japanese Beetle, UW–Madison Extension, Wisconsin Horticulture (first adults in late June or early July at about 1,000 degree days)
  - University of Minnesota Extension, Japanese beetles in yards and gardens (feeding season and scouting)
---

## What it predicts

Japanese beetle adults skeletonize the leaves of many fruit, vegetable and ornamental plants and feed on flowers, fruit and corn silks. They have one generation a year: grubs spend the winter in the soil under turf, and adults emerge in early summer and feed for six to eight weeks. The model rates the risk of adult feeding from 0 (Very low) to 4 (Very high).

## How it works

Degree days are counted from January 1 by the single-sine method, base 50 °F with no upper cutoff.

- **The window** follows VDIFN's description: adults begin to emerge at about 970 degree days, feeding peaks at about 1,600, and feeding ends by about 2,150.
- **The levels.** The level rises a level at a time from 0 at 970 to 4 near 1,600 and falls back the same way to 0 at 2,150. It is Very high from about 1,390 to 1,783.
- **The end of the season.** After early September, the level drops by one for each day in the last two weeks at or below about 28 °F (−2 °C).

In AgWeather's long-term averages (1996–2025), 970 degree days comes around July 2 at Arlington and July 6 at Hancock, and 2,150 around August 28 at Arlington. At Rhinelander the window opens around mid-July, and an average season there doesn't reach 2,150, so the window stays open until fall freezes end it.

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces.

## How to read it

- **Look for beetles from late June**, whatever the model shows, and start control as soon as they appear: a few beetles feeding draw in many more.
- Keep checking until numbers fall. Most feeding is in July and August.
- Don't use pheromone traps for control. They show when beetles are flying, but they draw in more beetles than they catch, and damage near traps can increase.
- Well-established plants tolerate a good deal of leaf feeding; young or weak plants, blossoms and ripe fruit suffer most.

The [Japanese beetle topic page](/topics/japanese-beetle) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's level matches VDIFN's formula at every total tested, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that the timing is right: it hasn't been checked against field counts in Wisconsin.
- **The source isn't documented.** USPest.org's model, from Oregon State's analysis of lab and field studies, is the likely source: it puts 2 % of adults out at 1,000 degree days, half at 1,540 and 90 % at 1,985, close to the model's window. Its events haven't been compared with the table in detail.
- **The upper cutoff is unsettled.** The model has none, USPest.org's model uses 92 °F, and UW Vegetable Entomology's table of degree-day models gives 100 °F. In AgWeather's long-term averages, a cutoff at 92 °F changes the totals by less than one degree day, because few days pass 92 °F; in a hot summer it would put the dates a little later.
- The window's opening agrees fairly well with UW–Madison Horticulture's first adults in late June or early July at about 1,000 degree days. UW Vegetable Entomology's page puts the first adults earlier, in mid-June.
- The levels show where the season stands in the window, not how many beetles there are. Numbers vary with things the model doesn't follow: a dry summer, for one, can mean fewer beetles the next year.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
