---
id: squash-vine-borer
status: draft
updated: 2026-11-19
summary: Rates squash vine borer moth activity from degree days since January 1 in one window from 750 to 1,000 degree days (base 50 °F), peaking at 900, around when the moths begin to emerge.
sources:
  - VDIFN's squash vine borer model (all of the model's numbers; no source is known for them)
  - Liesch and Groves, Squash Vine Borer (XHT1136), UW–Madison Division of Extension, 2026 (emergence at 900 degree days, three weeks of egg laying around 1,000)
  - UW–Madison Vegetable Entomology, squash vine borer (vegento.russell.wisc.edu, 2026) (emergence after about 1,000 degree days)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (spray timing)
  - University of Minnesota Extension, squash vine borers (reviewed 2026) (monitoring)
  - MSU Enviroweather's squash vine borer model (numbers compared)
---

## What it predicts

Squash vine borer moths lay their eggs at the base of squash and pumpkin vines in early summer. The larvae that hatch bore into the stems, where sprays can't reach them, and feed there until the vine wilts and dies. Insecticides work only if they're on the stems while eggs are hatching, so the timing of the moths matters. There is one generation a year in Wisconsin.

The model rates moth activity on five levels, from Very low to Very high (0 to 4), in a single window around the moths' emergence.

## How it works

Degree days are counted from January 1 by the single-sine method, base 50 °F, with no upper threshold.

- **The window** opens at 750 degree days, peaks at 900 and closes at 1,000. The rating rises a level at a time, from Low just after 750 to Very high from about 850, holds there past the peak to about 935, and falls back to Very low at 1,000.
- **The numbers** come from VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces. No source is known for them. The peak at 900 matches UW–Madison's fact sheet, which expects the moths at about 900 degree days, around when chicory is in full bloom along roadsides.
- **On the calendar**, from AgWeather's long-term averages (degree days for 1996 to 2025), an average year's window runs from about June 21 to July 3 at Arlington, peaking about June 28; from June 25 to July 8 at Hancock; and from July 3 to July 18 at Rhinelander.

## How to read it

- Start watching for moths as the rating rises, and by 900 degree days or the last week of June at the latest. Yellow pans of water with a drop of dish soap catch the moths; pheromone traps show when males are flying but also catch related clearwing moths. Neither kind of trap has a treatment threshold.
- UW–Madison recommends treating when moths are first seen, around 900 degree days, especially on plants with runners shorter than 2 feet, and repeating every 5 to 7 days through the three weeks of egg laying. Once larvae are inside the vine, sprays do little.
- **Don't stop when the window closes.** By UW–Madison's timing, egg laying centers on about 1,000 degree days, where the model's window ends, and goes on for about a week and a half after the rating falls to Very low. Keep stems protected for the full three weeks.
- Check the bases of stems for entry holes and sawdust-like droppings (frass), which show where larvae have bored in before plants wilt.

## Validation and caveats

- Draft (model version 0.1, beta). Given the same degree days, its ratings match VDIFN's exactly, and its degree days match the calculator VDIFN used. That shows the model was carried over faithfully, not that its timing is right: it hasn't been checked against a published source or against trap catches in Wisconsin.
- The window is shorter and earlier than UW–Madison's advice. It ends at 1,000 degree days, about the middle of egg laying in UW–Madison's fact sheet, and about when UW Vegetable Entomology's page says the moths begin to emerge. Michigan State's Enviroweather model, also without a cited source, counts from March 1, starts emergence at 800 degree days and has flight and egg laying declining from 1,800 and over at 2,000. AgWeather's model is the likelier to change.
- The rating is a display of where the season stands in the window, not an estimate of how many moths there are: Very high means near the window's peak, in a light year as in a heavy one.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
