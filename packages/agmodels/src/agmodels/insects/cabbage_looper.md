---
id: cabbage-looper
status: draft
updated: 2026-11-21
summary: Times cabbage looper egg laying and caterpillar feeding from degree days since the first moth caught in a pheromone trap, or July 15 without one, for each generation to the season's end, and marks when to scout for small caterpillars.
sources:
  - USPest.org's cabbage looper model, Oregon State University (the method and each stage's timing)
  - Toba, Kishaba, Pangaldan and Vail 1973 (laboratory development of the cabbage looper; the time from egg to moth)
  - Delahaut, Cabbage Looper, UW–Madison Division of Extension, and UW Vegetable Entomology's cabbage looper page (moths arrive from mid-July; the second generation does the most damage)
  - University of Minnesota Extension, Caterpillars on Cole Crops (moths' arrival in Minnesota; compared)
  - Commercial Vegetable Production in Wisconsin (A3422), 2026 (scouting and thresholds)
---

## What it predicts

Cabbage looper moths don't survive Wisconsin winters. They fly in from the south each summer, and their caterpillars feed on cole crops, lettuce, spinach, celery, potatoes, tomatoes and other crops. Large loopers can bore through the wrapper leaves of cabbage heads. The model follows each generation from the moths' arrival:

- **Egg laying**: moths laying eggs, compared with the first generation's peak.
- **Eggs**: eggs laid and not yet hatched.
- **Larval feeding**: caterpillars feeding on the crop. This is the risk.
- **Scout for small caterpillars**: the days from 10 % to 90 % of each generation's eggs hatched.

A risk of 1 means as many caterpillars feeding as at the first generation's peak.

## How it works

The model is USPest.org's cabbage looper model, from Oregon State University, built on laboratory development times (Toba and others, 1973). Degree days are counted by the single-sine method, base 50 °F with a cutoff at 90 °F, from the start date.

- **The start date** is the first moth caught in a pheromone trap near your field. Enter it if you trap. Without it, the model starts on July 15, when UW–Madison says the moths begin arriving. That date is a typical arrival, not a prediction for this year: the moths ride weather systems north, and in Minnesota they can arrive in early July.
- **Egg laying** begins about 120 degree days after the first catch and peaks at about 200. Because moths keep arriving for weeks, the model spreads egg laying out to about 450.
- **Caterpillars** hatch about 100 degree days after an egg is laid and feed for about 420 degree days, a little over three weeks in August, before they pupate. They are large and feeding heavily from about 210 degree days after hatching.
- **Later generations.** A new generation begins laying eggs every 912 degree days, the time from egg to moth plus the days before a moth lays, until fall freezes end the season.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In an average year (AgWeather's degree days for 1996 to 2025), starting on July 15, egg laying peaks in late July across Wisconsin and the first generation's caterpillars peak from about August 9 at Arlington to August 15 at Rhinelander. The second generation lays its eggs in early to mid-September in southern and central Wisconsin; in the north the season usually ends before it gets far.

## How to read it

- **Trap if you can.** A pheromone trap's first catch makes the model's dates fit your field, rather than an average arrival.
- **Use the scouting window** to look for small caterpillars on the undersides of lower leaves. Insecticides work best on small loopers, which are also harder to control once they are inside heads.
- **Scout cole crops weekly** and treat by the share of infested plants, counting cabbage loopers, imported cabbageworms and diamondback moths together. For cabbage, Commercial Vegetable Production in Wisconsin gives 10 % in the seedbed, 30 % from transplanting to cupping, 20 % from cupping to early head and 10 % at mature head.
- **The second generation does the most damage,** by UW–Madison's account. In southern Wisconsin its eggs come in September, so watch fall cole crops. The model rates every generation alike.

The [cabbage looper topic page](/topics/cabbage-looper) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). Its development times were measured in the laboratory in Riverside, California; USPest.org describes the model as not fully tested.
- **The default start date is an estimate.** We found no Wisconsin or Minnesota records of first trap catches to check July 15 against; Wisconsin's state light-trap network counts other loopers. A grower's own first catch is more reliable.
- **Moths keep arriving.** The model starts from one date, but migrant moths arrive from mid-July through September, so later arrivals can lay eggs outside the model's windows.
- The model's stages match USPest.org's timings, and its generation time matches the laboratory time from egg to moth, but neither has been compared with field counts in Wisconsin.
- Every generation counts alike in the risk, though UW–Madison says the second does the most damage.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
