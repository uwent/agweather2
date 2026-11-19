---
id: mint-root-borer
status: draft
updated: 2026-11-19
summary: Rates mint root borer activity from degree days since April 1 (base 50 °F) in one window, from the first moths at 430 degree days through the peak of egg hatch at 1,280 to 2,150, when half the larvae have made their winter chambers.
sources:
  - VDIFN's mint root borer model (all of the model's numbers)
  - Berry and others, Oregon State University's mint root borer degree-day model on USPest.org, partly validated for the Pacific Northwest (the start date and the three events the window follows)
  - Pacific Northwest Insect Management Handbook, mint root borer (2026) (life cycle, sampling, threshold)
---

## What it predicts

The mint root borer has one generation a year. It spends the winter as a full-grown larva in a cocoon in the soil, and the moths fly from May through July. The larvae that hatch from their eggs tunnel in mint rhizomes and feed on the roots from late July through September, and into early October in some years, which can severely thin the stand.

The model rates activity on five levels, from Very low to Very high (0 to 4), in one long window that covers moth flight, egg laying and the larvae's feeding until they settle for the winter.

## How it works

Degree days are counted from April 1 by the single-sine method, base 50 °F, with no upper threshold.

- **The window** opens at 430 degree days, peaks at 1,280 and closes at 2,150. The rating rises a level at a time, from Low just after 430 to Very high from about 1,000, holds there past the peak to about 1,570, and falls back to Very low at 2,150.
- **The numbers** come from VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, and all three are events in Oregon State University's mint root borer model on USPest.org (Berry and others), which also counts from April 1 at 50 °F: the first moths caught at 430 degree days, the peak of egg hatch at 1,280, and half the larvae in the chambers in which they spend the winter (hibernacula) at 2,150. Oregon State's model also puts the peak of moth catches at 910 and of egg laying at 1,130, and has 5 percent of the larvae forming their chambers at 1,850; the rating doesn't mark these.
- **On the calendar**, from AgWeather's long-term averages (degree days for 1996 to 2025), in an average year at Arlington the window opens about June 4, peaks about July 18 and closes about August 29. At Rhinelander it opens about June 13 and peaks in early August, and an average season doesn't reach 2,150.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C). Where the season doesn't reach 2,150, the rating is still Low in the fall, and freezes bring it to Very low.

## How to read it

- From the window's opening, use pheromone-baited sticky traps or a sweep net to see when moths are flying. There is no threshold for moths, but catches, together with a field's history, help plan control of eggs and young larvae before damage is done.
- Decide on treatment from the larvae. Sample after harvest, from late August through mid-September, when most larvae are big enough to find but haven't yet done much damage: dig square-foot samples of soil to the depth of the rhizomes, sift them and count the larvae. The Pacific Northwest handbook suggests treating at two to four larvae per square foot, depending on the age and vigor of the stand, other pests and stresses, and the price of mint oil.
- Commercial Vegetable Production in Wisconsin doesn't cover this insect. Check that any product is registered for mint in Wisconsin before you use it.

## Validation and caveats

- Draft (model version 0.1, beta). Given the same degree days, its ratings match VDIFN's exactly, and its degree days match the calculator VDIFN used. That shows the model was carried over faithfully, not that its timing is right: it hasn't been checked against trap catches or larval counts in Wisconsin, and none are known to us.
- Oregon State's model was developed for the Pacific Northwest and is listed as partly validated; the research behind it isn't identified.
- The window closes when half the larvae have formed their winter chambers, not when all have. VDIFN's earlier description said risk ended when the larvae had formed their winter chambers; some larvae are still feeding after the rating falls to Very low.
- The rating is a display of where the season stands in the window, not an estimate of how many borers there are.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
