---
id: western-flower-thrips
status: draft
updated: 2026-11-21
summary: Retired. Western flower thrips don't survive the winter outdoors in Wisconsin, so degree days from January 1 don't time them here.
sources:
  - VDIFN's western flower thrips model (all of the model's numbers)
  - Oregon State University's western flower thrips degree-day model on USPest.org, listed as under development (the peaks of adults the windows follow)
  - McDonough, Gerace and Ascerno, Western Flower Thrips in Commercial Greenhouses, University of Minnesota (no winter survival outdoors in the Upper Midwest)
  - Williamson, Managing Thrips in Greenhouses (XHT1022), UW–Madison Extension (spread on transplants; development above 50 °F)
  - UMass Extension, Western Flower Thrips, Management and Tospoviruses (monitoring with sticky cards)
  - UW–Madison Vegetable Entomology, thrips (vegento.russell.wisc.edu, 2026) (scouting field edges)
---

This model is retired. Western flower thrips don't survive the winter outdoors in Wisconsin: they breed in greenhouses and reach fields on transplants, so a count of degree days from January 1 doesn't time them in the field. The model's source, Oregon State University's western flower thrips model on USPest.org, is also still listed as under development. Scout transplants and field edges for the thrips themselves (see the [western flower thrips topic](/topics/western-flower-thrips)).

## What it predicts

The western flower thrips is a tiny insect that scars the flowers, leaves and fruit of greenhouse and vegetable crops, among them tomato, pepper and cucurbits, and spreads tomato spotted wilt virus. In Wisconsin it doesn't survive the winter outdoors: it breeds all year in greenhouses and reaches fields on transplants.

The model rates thrips activity on five levels, from Very low to Very high (0 to 4), in four windows through the season, one for each generation. It is not a model of onion thrips, the species that matters most in Wisconsin onion and cabbage fields.

## How it works

Degree days are counted from January 1 by the single-sine method, base 45 °F, with no upper threshold.

- **Four windows**, each with a start, peak and end: 340, 675 and 1,010 degree days; 1,010, 1,350 and 1,685; 1,685, 2,025 and 2,360; and 2,360, 2,700 and 3,375. In each, the rating rises a level at a time to Very high from about two thirds of the way to the peak, and falls back the same way, leaving Very high a third of the way from the peak to the end. Each window ends where the next begins, so the rating dips to Low between peaks.
- **The numbers** come from VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces, and follow Oregon State University's western flower thrips model on USPest.org. The peaks fall on that model's peaks of adults, 675 degree days apart, and the first window runs between its first two peaks of egg hatch (338 and 1,013). The last window runs on to 3,375, the Oregon State model's fifth peak of adults, so it falls more slowly than the others. Oregon State lists its model as still under development.
- **On the calendar**, from AgWeather's long-term averages (degree days for 1996 to 2025), in an average year at Arlington the first window opens in mid-May and the fourth closes in late September. At Rhinelander an average season doesn't reach 3,375, and ends with the rating still High or Very high until fall freezes bring it down.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

## How to read it

- The model counts from January 1 as if thrips had spent the winter in the field. Western flower thrips don't do that here: those in your field came on transplants or from nearby greenhouses, on their own schedule. Read the windows as a sign of how fast thrips can multiply in the season's warmth, not as the date they'll appear.
- Inspect transplants for adults and larvae as soon as they arrive, and keep infested plants apart.
- In the field, set sticky cards along the edges (blue cards catch western flower thrips better than yellow) and check plants on field edges weekly, where thrips are most common early in the season.
- Real generations overlap. Don't relax scouting in the dips between windows.
- The threshold UW–Madison gives for thrips in onions, seven or more per plant, is for onion thrips, which this model doesn't time.

## Validation and caveats

- Draft (model version 0.1, beta). Given the same degree days, its ratings match VDIFN's exactly, including this model's own four windows, and its degree days match the calculator VDIFN used. That shows the model was carried over faithfully, not that its timing is right: it hasn't been checked against thrips counts in Wisconsin.
- VDIFN described this model with text and a link about onion thrips, but its numbers are western flower thrips'. The paper behind Oregon State's model isn't identified.
- The model's base of 45 °F is Oregon State's, and lower than the 50 °F below which UW–Madison says the thrips stop developing. Oregon State's model also caps degree days at 104 °F, which matters only on the hottest days.
- The rating is a display of where the season stands in each window, not an estimate of how many thrips there are, and every generation counts alike.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field. In greenhouses the weather outside doesn't apply.
