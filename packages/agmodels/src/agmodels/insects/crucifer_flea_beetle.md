---
id: crucifer-flea-beetle
status: draft
updated: 2026-11-21
summary: Times crucifer flea beetle adults from degree days since January 1, the overwintered beetles that feed on seedlings and transplants in spring and the new adults of late summer, and marks when to scout new plantings every one to two days.
sources:
  - Delahaut, Degree Days for Common Fruit & Vegetable Insect Pests (XHT1087), UW–Madison Extension (the method and the spring beetles)
  - Kinoshita, Svec, Harris and McEwen 1979 (development from egg to adult and egg laying, southwestern Ontario; the summer adults' timing)
  - UMass Extension Vegetable Program, Flea Beetle Biology (the seasonal pattern in Massachusetts; compared)
  - UW Vegetable Entomology's flea beetles page and University of Minnesota Extension's flea beetles page (life cycle, scouting and thresholds)
  - Midwest Vegetable Production Guide 2026 (thresholds)
---

## What it predicts

Crucifer flea beetles are small, shiny black beetles that chew small round holes in the leaves of cabbage, broccoli, radish, mustard greens and other cole crops. Seedlings and new transplants suffer most: heavy feeding can stunt or kill them. The model follows the beetles through the season:

- **Adults feeding**: how many beetles are active. In spring these are the beetles that spent the winter in leaf litter and soil near fields; in late summer, the new generation. Both count in the risk.
- **Egg laying**: the spring beetles laying eggs in the soil. Their larvae feed on roots and rarely cause damage, so this stage carries no risk of its own.
- **Scout new plantings every one to two days**: the days from 5 % to 95 % of each generation of beetles active.

A risk of 1 means as many beetles active as at the spring peak.

## How it works

Degree days are counted from January 1 by the modified average method, base 50 °F with a cutoff at 86 °F: a day's low is raised to 50 °F and its high capped at 86 °F before they are averaged. This is the modified method in UW–Madison Extension's guide to calculating degree days, the companion to its degree-day table (Delahaut's XHT1087).

- **The spring beetles.** UW–Madison's table puts flea beetles at 150 to 200 degree days. In the model, a tenth of the overwintered beetles are active by about 145 degree days, and activity peaks at 200. The old beetles keep feeding into June and die off as they finish laying eggs.
- **Egg laying.** The beetles begin laying eggs in the soil about 300 degree days after they become active, and lay for about 300 more. Both numbers are our estimates. In an average year, egg laying peaks in mid- to late June.
- **The summer adults.** A study in southwestern Ontario (Kinoshita and others, 1979) found that the beetles take 820 degree days above 51.8 °F to develop from egg to adult, which is about 910 of the model's degree days. The new adults peak about 1,350 degree days after the spring beetles. They feed on late plantings and then overwinter. The model includes no further generation.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In an average year (AgWeather's degree days for 1996 to 2025), the spring beetles are active from late April at Arlington and Hancock and early May at Rhinelander, and peak in early to mid-May. The summer adults peak around July 28 at Arlington, August 2 at Hancock and August 15 at Rhinelander.

## How to read it

- **Scout new plantings every one to two days** while the spring window is open. Flea beetles can damage young plants quickly.
- **Plant after the spring peak where you can,** or use floating row covers set up just before the crop emerges, to keep beetles off seedlings.
- **Treat young plants when feeding threatens the stand.** No threshold fits every cole crop: the Midwest Vegetable Production Guide suggests about one beetle per plant on small plants and two to five on larger ones, with the lower numbers where beetles feed on the part you sell, and the University of Minnesota suggests treating when 10 to 20 % of a stand shows feeding damage.
- **The summer window** matters most for late plantings and for leafy crops such as kale, bok choy and mustard greens, where holes in the leaves make them unmarketable.

The [crucifer flea beetle topic page](/topics/crucifer-flea-beetle) explains the insect, its monitoring and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The spring beetles come from UW–Madison's degree-day table for Wisconsin; the summer adults' timing from laboratory and field work in southwestern Ontario.
- **The spring beetles are on firmer ground than the summer adults.** UW–Madison's table doesn't say which part of the beetles' activity its 150 to 200 degree days cover. The summer adults rest on two estimates: when the spring beetles lay their eggs, and the conversion of the Ontario study's degree days, which were counted on soil temperatures, to the model's air temperatures. If the beetles lay earlier, as UW–Madison's "May" suggests, the summer adults would come up to about two weeks sooner.
- **The summer adults come later than in Massachusetts.** The model's new adults peak in late July and early August; UMass reports new adults from late June. The Ontario study found one generation in some years and two in others.
- The model hasn't been compared with trap or scouting counts in Wisconsin.
- Every generation of adults counts alike in the risk, though the spring beetles on seedlings do the most damage to stands.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
