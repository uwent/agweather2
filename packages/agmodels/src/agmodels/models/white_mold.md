---
id: white-mold
status: draft
updated: 2026-11-19
summary: Estimates the probability that white mold's spore-releasing cups (apothecia) are present in a soybean field, from 30-day averages of the weather, for non-irrigated or irrigated fields, while soybean flowers from R1 to R3.
sources:
  - Willbur et al. 2018, Plant Disease 102, 73–84 (the equations, from apothecia counts in Iowa, Michigan and Wisconsin)
  - Smith, Willbur and Webster's 2025 soybean white mold algorithm (the corrected coefficient, the 50 °F gate and the risk levels)
  - Crop Protection Network, An Overview of White Mold, and UW–Madison's Pest Management in Wisconsin Field Crops (A3646) (fungicide timing)
  - UW–Madison's Sporecaster app (its 40 % spray threshold)
  - The Crop Risk Tool's white mold model (compared)
---

## What it predicts

White mold infects soybean through its flowers. The spores come from small, mushroom-like cups called apothecia, which sprout from the fungus's resting bodies (sclerotia) in moist, shaded soil. The model gives the probability, from 0 to 100 %, that apothecia are present in a field, from the past month's weather. It predicts apothecia, not disease: the fungus has to be in the field, and the crop has to be flowering, for the weather to matter.

## How it works

The equations go back to Willbur and colleagues (2018), who related whether apothecia were found in soybean fields in Iowa, Michigan and Wisconsin to 30-day averages of the weather. Their best models used the daily high temperature and wind speed for non-irrigated fields, and the daily high temperature, highest humidity and row spacing for irrigated fields. In the paper's tests on new data, the models were right about 67 to 70 % of the time. We use the equations as the 2025 soybean white mold algorithm of Smith (UW–Madison), Willbur and Webster sets them out; we haven't confirmed which study the second and third non-irrigated equations come from. You choose the field's setting:

- **Non-irrigated fields** (the default): the average of three equations, using the 30-day averages of the daily high temperature, the daily highest wind speed and the daily highest relative humidity. Cooler highs and calmer air raise the probability, and so, in one of the three, does higher humidity. Risk is Low from 1 %, Moderate from 20 % and High from 35 %.
- **Irrigated fields:** one equation, using the 30-day averages of the daily high temperature and the daily highest humidity, and the row spacing (15- or 30-inch rows). Here warmer, more humid weather raises the probability, and 15-inch rows give a higher probability than 30-inch rows. Risk is Low from 1 %, Moderate from 5 % and High from 10 %.

Following the 2025 algorithm, the model is inactive, and shows 0 %, while the 30-day average daily high is 50 °F (10 °C) or lower. The risk is shown from beginning bloom (R1) to beginning pod (R3), taken from the [soybean stages model](/models/soybean-stages) or your own dates, between June 15 and August 7.

## How to read it

- A higher probability means the past month has been more like the weather when apothecia were found in the study fields.
- Fungicides work only from beginning bloom (R1) to beginning pod (R3), while flowers are on the lower half of the stem; sprays at R4 or later, or after symptoms appear, don't. Weigh a High risk during that window together with the field's history of white mold, the variety's resistance and how closed the canopy is. UW–Madison's Sporecaster app suggested a fungicide when the risk passed 40 %, a little above our non-irrigated High.
- In fields that have never had white mold, or where the canopy is still open, a high probability matters less: the model doesn't know either.
- See the [white mold topic page](/topics/white-mold) for management.

## Validation and caveats

- Draft (model version 0.2, beta). The equations were developed in Iowa, Michigan and Wisconsin soybean fields. We haven't compared the model with apothecia or white mold in Wisconsin fields.
- We ported the model from the Crop Risk Tool and checked it on the tool's own 2025 weather at Eau Claire, Wisconsin. For irrigated fields our probability matched the tool's on every day the model was active. For non-irrigated fields it runs about 1.5 times the tool's in summer, by design: the tool had copied one coefficient of the third equation wrongly (−0.86 for the algorithm's −0.56), which kept that equation near 0 % all summer. The 2025 algorithm is unambiguous, but its authors haven't yet confirmed the correction to us.
- The 50 °F gate replaces the tool's own adjustment for cold weather. The algorithm says the model is "inactive" below it; we show that as 0 % until the authors say whether they mean 0 % or no value. In a Wisconsin summer the 30-day average high is well above 50 °F (at Eau Claire in 2025 it ran from 68 to 82 °F during the season), so the gate matters only in spring and fall, outside the season.
- The 2025 algorithm also runs the model only when flowers are present and the rows are more than 40 % closed. We take flowering from the crop stage and don't ask about the canopy, so the model can show risk before the canopy closes.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field. Low spots and dense canopies stay cooler and more humid than the cell's average.
