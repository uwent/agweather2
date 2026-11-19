---
id: mint-flea-beetle
status: draft
updated: 2026-11-19
summary: Rates mint flea beetle adult activity from degree days since January 1 (base 41 °F) in one window, from the start of adult emergence at 1,475 degree days through a peak at 1,675 to its end at 1,880.
sources:
  - VDIFN's mint flea beetle model (all of the model's numbers)
  - Berry and others, Oregon State University's mint flea beetle degree-day model on USPest.org, partly validated for the Pacific Northwest (the start of adult emergence at 1,475)
  - Pacific Northwest Insect Management Handbook, mint flea beetle (2026) (life cycle, sampling, spray timing)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (emergence in Wisconsin; thresholds)
---

## What it predicts

The mint flea beetle has one generation a year. Its larvae feed on mint roots and tunnel into rhizomes from April into June, which stunts the mint and turns it purple. The adults emerge in summer, chew small round holes in the leaves, and after two to three weeks of feeding begin laying the eggs that carry the beetle through the winter. No insecticide is registered for the larvae in the soil, so control aims at the adults after most have emerged but before egg laying starts.

The model rates adult activity on five levels, from Very low to Very high (0 to 4), in one window around the adults' emergence.

## How it works

Degree days are counted in air from January 1 by the single-sine method, base 41 °F, with no upper threshold.

- **The window** opens at 1,475 degree days, peaks at 1,675 and closes at 1,880. The rating rises a level at a time, from Low just after 1,475 to Very high from about 1,610, holds there past the peak to about 1,745, and falls back to Very low at 1,880.
- **The numbers** come from VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces. The start matches Oregon State University's mint flea beetle model on USPest.org, which puts the beginning of adult emergence at 1,475 degree days from January 1 and lists itself as partly validated for the Pacific Northwest. Oregon State's model has no events for a peak or an end, so where 1,675 and 1,880 come from isn't known.
- **On the calendar**, from AgWeather's long-term averages (degree days for 1996 to 2025), an average year's window runs from about June 25 to July 9 at Arlington, peaking about July 2, and from about July 8 to July 23 at Rhinelander.

## How to read it

- Use the rising rating as a reminder to start sweeping for adults, and keep sweeping after the window closes (below). Sweep in the early morning, below about 60 °F, when the beetles stay on the leaves, and check the whole field, starting at the margins, where infestations usually begin.
- Commercial Vegetable Production in Wisconsin suggests treating the adults before they lay eggs if larval damage (stunting, purpling in June) was visible; or, without larval damage, if standing mint has more than 25 adults per 100 sweeps; or if standing mint has fewer but stubble after harvest has more than 25 per 100 sweeps.
- Time sprays from your sweep counts: after most adults have emerged, and before females start laying eggs two to three weeks later.

## Validation and caveats

- Draft (model version 0.1, beta). Given the same degree days, its ratings match VDIFN's exactly, and its degree days match the calculator VDIFN used. That shows the model was carried over faithfully, not that its timing is right: it hasn't been checked against field counts in Wisconsin, and none are known to us.
- The model was developed for the Pacific Northwest's mint, and its timing runs ahead of Wisconsin's guide. Its window fits the Pacific Northwest's adult emergence in late June and July, but Commercial Vegetable Production in Wisconsin puts emergence here in late July, at about 1,100 degree days above 40 °F counted from soil temperatures 6 inches deep. The model's window ends before or around then.
- The model counts degree days in air, while the beetles develop in the soil; Wisconsin's guide times emergence by soil temperature.
- Oregon State's model caps degree days at 103 °F, and this one doesn't; that matters only on the hottest days.
- The rating is a display of where the season stands in the window, not an estimate of how many beetles there are.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
