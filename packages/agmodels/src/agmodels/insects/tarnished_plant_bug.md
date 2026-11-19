---
id: tarnished-plant-bug
status: draft
updated: 2026-11-19
summary: Rates tarnished plant bug activity from degree days since January 1 (base 52 °F) in one broad window from 275 to 2,000 degree days, peaking at 1,000; its base, start and first number match a lygus bug model made for seed alfalfa in the Northwest.
sources:
  - VDIFN's tarnished plant bug model (all of the model's numbers)
  - Simko 2000, Oregon State University's lygus bug degree-day model for alfalfa grown for seed in eastern Oregon and southwestern Idaho, on USPest.org (base 52 °F from January 1, and 275 degree days, the peak of first- and second-stage nymphs)
  - Groves, vegetable insect update, UW–Madison Vegetable Pathology's crop updates, June 5, 2021 (activity after 275 degree days; sweep threshold for potatoes)
  - UW–Madison Vegetable Entomology, tarnished plant bug (vegento.russell.wisc.edu, 2026) (sweep threshold for beans; alfalfa)
  - van Zoeren and Guédot, Tarnished plant bug – a strawberry menace, UW–Madison Fruit Program, 2018 (spring nymphs; generations; scouting near alfalfa)
  - Penn State Extension, tarnished plant bug (2026) (development above about 50 °F)
  - UMass Extension, tarnished plant bug and New England Small Fruit Management Guide (thresholds in vegetables; raspberry spray timing)
---

## What it predicts

The tarnished plant bug (_Lygus lineolaris_) feeds on the buds, flowers, young fruit and stems of more than 50 crops, injecting a toxic saliva as it feeds. The damage includes misshapen strawberries, crumbly raspberries, brown spots on celery stalks and scarred lettuce ribs. Adults spend the winter in leaf litter and become active early in spring, and the generations overlap, so adults and nymphs are present from spring to fall.

The model rates activity on five levels, from Very low to Very high (0 to 4), in one broad window, treating the overlapping generations as a single season of activity.

## How it works

Degree days are counted from January 1 by the single-sine method, base 52 °F, with no upper threshold.

- **The window** opens at 275 degree days, peaks at 1,000 and closes at 2,000. The rating rises a level at a time, from Low just after 275 to Very high from about 760, holds there past the peak to about 1,330, and falls back to Very low at 2,000.
- **The numbers** come from VDIFN, the vegetable disease and insect forecasting tool AgWeather replaces. The base, the January 1 start and the opening at 275 match Simko's (2000) lygus bug model on USPest.org, developed for alfalfa grown for seed in eastern Oregon and southwestern Idaho, where 275 degree days marks the peak of first- and second-stage nymphs. That model has no events at 1,000 or 2,000, so where those come from isn't known. USPest doesn't name the species; in that region it is likely the western tarnished plant bug (_Lygus hesperus_), not Wisconsin's _L. lineolaris_. UW–Madison's vegetable newsletter has described the bugs as active most of the summer after the nymphs' early-season development, from 275 degree days at this base.
- **On the calendar**, from AgWeather's long-term averages (degree days for 1996 to 2025), in an average year the window opens about May 26 at Arlington and June 5 at Rhinelander. At Arlington it peaks about July 10 and closes about September 3. An average season at Rhinelander reaches about 1,840 degree days, short of 2,000, so the window stays open there until fall freezes.
- **The end of the season.** After early September, the rating drops by one level for each day in the last two weeks at or below about 28 °F (−2 °C).

## How to read it

- Scout from early spring, whatever the model shows. Overwintered adults are active early, and in strawberries nymphs often appear by mid-May, once temperatures reach about 68 °F, before the window opens.
- **Beans and potatoes:** take 25 sweeps with an insect net at each of at least 10 sites per 100 acres. UW–Madison suggests treating when the field averages more than one bug per sweep.
- **Raspberries:** sprays go on before bloom and again after petal fall, not during bloom.
- **Celery and leafy greens:** no thresholds have been set for most vegetables.
- **Near alfalfa:** cutting hay, or mowing weedy borders, drives large numbers of adults into nearby crops. Scout the parts of a field closest to alfalfa, especially after it is cut. The model can't show this.
- Insecticides work better on nymphs than on adults, and none reach the eggs inside the plant.

## Validation and caveats

- Draft (model version 0.1, beta). Given the same degree days, its ratings match VDIFN's exactly, and its degree days match the calculator VDIFN used. That shows the model was carried over faithfully, not that its timing is right: it hasn't been checked against field counts in Wisconsin.
- The numbers are likely the wrong species' and region's for Wisconsin. Wisconsin's pest is _L. lineolaris_, which develops above about 50 °F; the model uses the 52 °F base and the first event of a model made for the Northwest's seed alfalfa, likely for the western species. We keep it until a model of _L. lineolaris_ replaces it.
- The window opens later than the bugs appear in Wisconsin: adults are active from early spring and nymphs by mid-May, while the window opens in late May in the south and early June in the north.
- One broad window can't show the four to five overlapping generations UW–Madison counts in the Midwest, or the sudden influx when alfalfa is cut.
- The rating is a display of where the season stands in the window, not an estimate of how many bugs there are.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
