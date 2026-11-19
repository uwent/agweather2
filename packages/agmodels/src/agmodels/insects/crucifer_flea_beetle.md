---
id: crucifer-flea-beetle
status: draft
updated: 2026-11-19
summary: Rates the risk from the two summer generations of crucifer flea beetle adults in windows of degree days from January 1; the overwintered adults that feed on seedlings and transplants in spring, the most damaging, aren't in the model.
sources:
  - VDIFN's crucifer flea beetle model (the threshold, the January 1 start and the two windows, unchanged; its source isn't identified)
  - UMass Extension Vegetable Program, Flea Beetle Biology (the seasonal pattern in Massachusetts; compared)
  - UW Vegetable Entomology's flea beetles page and University of Minnesota Extension's flea beetles page (life cycle, scouting and thresholds)
  - Midwest Vegetable Production Guide 2026 (thresholds)
---

## What it predicts

Crucifer flea beetles chew small round holes in the leaves of cabbage, broccoli, kale, radish, mustards and the other crucifers. Adults spend the winter in leaf litter and field edges, become active in early spring and feed on seedlings and transplants, which they can quickly destroy. Their larvae feed on roots in the soil, doing little harm, and emerge as new adults in summer. The model rates the risk from the adults of two summer generations, from 0 (Very low) to 4 (Very high). It doesn't include the overwintered adults that feed in spring.

## How it works

Degree days are counted by the single-sine method, base 50 °F with no cutoff, from January 1.

- **The first summer generation:** new adults from 820 degree days, peaking at 965 and feeding through 1,155.
- **The second summer generation:** adults from 1,640, peaking at 1,785 and feeding through 1,975.
- **The rating** rises a level at a time from Low at a window's start through Moderate and High to Very high, and falls the same way to its end. It's Very high from about 915 to 1,030 degree days in the first window and from about 1,735 to 1,850 in the second, and Very low before, between and after them.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

The model comes from VDIFN, the vegetable forecasting tool AgWeather replaces. VDIFN's notes point to a University of California page on the insect, which we haven't yet read against the windows; the source of the numbers isn't identified.

## How to read it

- **In spring, scout whatever the model shows.** It reads Very low through the weeks when overwintered beetles do the most harm. Check new plantings every one to two days from emergence or transplanting; feeding damage is easier to spot than the beetles, which jump away.
- **Treat by the beetles or the damage.** The Midwest Vegetable Production Guide suggests treating at about one beetle per plant on small plants and two to five on larger ones, using the lower numbers where beetles feed on the part you sell; the University of Minnesota suggests treating when 10 to 20 % of a stand shows feeding damage.
- **Use the windows for summer plantings,** especially kale, bok choy, mustard and other greens, whose leaves are the harvest; by summer most other plants can withstand feeding. Row covers laid at seeding or transplanting and sealed at the edges keep beetles off young plants.

The [crucifer flea beetle topic page](/topics/crucifer-flea-beetle) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- Given the same degree days, the model's rating matches VDIFN's exactly, and its degree days match those of the calculator VDIFN used. This shows that AgWeather reproduces VDIFN, not that VDIFN's timing is right for Wisconsin. The source of the windows isn't identified, and the model hasn't been compared with field counts in Wisconsin.
- **The spring adults are missing.** The beetles that matter most, overwintered adults feeding on seedlings and transplants from early spring, aren't in the model.
- **The summer windows fit the pattern UMass reports.** On AgWeather's long-term averages (degree days for 1996 to 2025), the first window opens in late June in southern Wisconsin, at Arlington and Lancaster, and in early July in the north, at Rhinelander, in line with the new generation UMass reports in Massachusetts from late June. The second runs from late July to mid-August in southern Wisconsin, peaking in early August, about the time of or a little after the late-July generation UMass reports. This is a comparison with another state's account, not with Wisconsin counts.
- A study of when overwintered and new adults emerge (Ulmer and Dosdall 2006) could check the windows; we haven't yet compared them.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
