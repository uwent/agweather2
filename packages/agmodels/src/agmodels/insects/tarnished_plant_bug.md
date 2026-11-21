---
id: tarnished-plant-bug
status: draft
updated: 2026-11-21
summary: Follows tarnished plant bug nymphs and adults through overlapping generations from degree days since January 1 (base 52 °F), with generation times from a laboratory study of the species; the timing of the spring generation has no source for this species.
sources:
  - Ugine 2012 (development of Lygus lineolaris at constant temperatures; the nymphs, adults and generation time)
  - Groves, vegetable insect update, UW–Madison Vegetable Pathology's crop updates, June 5, 2021 (the base of 52 °F from January 1, and 275 degree days for the spring nymphs)
  - Simko 2000, lygus bug model for alfalfa grown for seed in eastern Oregon and southwestern Idaho, on USPest.org (the source of the 275)
  - van Zoeren and Guédot, Tarnished plant bug – a strawberry menace, UW–Madison Fruit Program, 2018 (spring nymphs; generations; scouting)
  - UW–Madison Vegetable Entomology, tarnished plant bug (sweep threshold for beans)
---

## What it predicts

The tarnished plant bug (_Lygus lineolaris_) feeds on the buds, flowers, young fruit and stems of more than 50 crops, injecting a toxic saliva as it feeds. The damage includes misshapen strawberries, crumbly raspberries, brown spots on celery stalks and blemished bean pods. Adults spend the winter in leaf litter and become active early in spring, and the generations overlap, so adults and nymphs are present from spring to fall. The model gives:

- **Egg hatch**: how fast eggs are hatching, in each generation.
- **Nymphs** and **Adults**: how many are present, compared with the spring nymphs' peak.

Risk adds nymphs and adults together, since both feed on the crop. Nymphs do more damage than adults in strawberries, and insecticides work better on them.

## How it works

Degree days are counted from January 1 by the single-sine method, base 52 °F with no upper limit, as in UW–Madison's vegetable newsletter.

- **Development.** A laboratory study of the tarnished plant bug at constant temperatures (Ugine 2012) gives the time from hatch to adult, how long adults live and the time from one generation to the next. Converted to this base on Wisconsin's summer weather, nymphs take about 390 degree days, adults live about 540, and a generation takes about 640.
- **The spring generation.** UW–Madison's vegetable newsletter has the bugs active after the early-season nymphs develop, starting at 275 degree days. The model places the spring hatch so that young nymphs peak at 275. That number comes from a lygus bug model for alfalfa grown for seed in Oregon and Idaho, likely made for the western species, so the timing of the spring generation isn't supported for Wisconsin's tarnished plant bug.
- **Later generations** follow every 640 degree days until fall freezes end the season.

In AgWeather's long-term averages (1996–2025), the first nymphs appear around May 5 at Arlington, May 8 at Hancock and May 16 at Rhinelander, and young nymphs peak around May 26, May 29 and June 5. The first summer adults are half out around June 19 at Arlington. An average season has about four generations at Arlington and three at Rhinelander.

## How to read it

- **Scout from early spring, whatever the model shows.** Overwintered adults are active early, and the model doesn't follow them.
- **Strawberries:** tap plants over a white surface and count the bugs, from before the first flowers open until harvest, twice a week. UW–Madison suggests acting at an average of one bug per four plants.
- **Beans and potatoes:** take 25 sweeps with an insect net at each of at least 10 sites per 100 acres. UW–Madison suggests treating when the field averages more than one bug per sweep.
- **Raspberries:** sprays go on before bloom and again after petal fall, not during bloom.
- **Near alfalfa:** cutting hay, or mowing weedy borders, drives large numbers of adults into nearby crops. Scout the parts of a field closest to alfalfa, especially after it is cut. The model can't show this.

The [tarnished plant bug topic page](/topics/tarnished-plant-bug) explains the insect and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The development times are those of a laboratory colony from Mississippi reared on green beans at constant temperatures, converted to degree days above 52 °F; field development in Wisconsin may differ.
- **The spring timing has no source for this species.** We found no study or extension source that times the tarnished plant bug's spring generation by degree days. The model's first nymphs appear in mid-May at Arlington, as UW–Madison's fruit program reports in strawberries, but the 275 that places them comes from a model of a different lygus bug, and every later generation follows from it.
- The overwintered adults and the sudden influx when alfalfa is cut aren't in the model.
- The model hasn't been compared with field counts in Wisconsin.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
