---
id: gray-leaf-spot
status: draft
updated: 2026-11-19
summary: Gives a probability of gray leaf spot in corn from three weeks of nightly lows and a month of dew points, from V10 to milk; in a Wisconsin summer it reads High almost every day, so its risk level isn't meaningful yet.
sources:
  - Smith and Webster's 2024 gray leaf spot algorithm (the equation, unpublished)
  - UW–Madison's Pest Management in Wisconsin Field Crops (A3646), Ohio State's Gray Leaf Spot of Corn (Salgado, Schoenhals and Paul 2016) and Minnesota Extension (scouting and fungicide timing)
  - The Crop Risk Tool's gray leaf spot model (compared)
---

## What it predicts

The model gives a probability, from 0 to 100 %, that gray leaf spot is present, from the recent weather. Its authors' document calls it the probability of "gray leaf spot presence" and doesn't say whether that was measured as spores caught in traps or as disease in fields. **At present its risk level isn't meaningful:** in a normal Wisconsin summer it reads High on nearly every day, for the reasons below.

## How it works

The model is one equation, which the Crop Protection Network's Crop Risk Tool credits to Damon Smith (UW–Madison) and Richard Webster (North Dakota State University). A 2024 algorithm document gives the equation and its risk levels; we haven't found the fit itself published. It uses two averages:

- the 21-day average of the daily low temperature, and
- the 30-day average of the daily lowest dew point.

A higher dew point raises the probability steeply. A warmer low lowers it slightly, though warm weather favors the disease. Risk is Low from 1 %, Moderate from 40 % and High from 60 %, the authors' default action threshold. The risk is shown from V10 (ten leaf collars) to milk (R3), taken from the [corn stages model](/models/corn-stages) or your own planting date, between July 1 and August 15.

The authors' document says to average the probabilities of "two models", but gives only one equation, which is the one we use.

## How to read it

- Don't use this model's risk level to decide on a fungicide. Time decisions by scouting: look at susceptible hybrids weekly from about V10 to V14, and again from tasseling to milk.
- A fungicide is most likely to pay on a susceptible hybrid with high yield potential, in humid weather, with lesions already present. Applications from tasseling (VT) to brown silk (R2) have given the best control; if the disease already covers much of the leaf area above the ear, a fungicide will do little.
- A reading below High in midsummer would mean an unusually dry month, which is worth knowing; a High reading tells you little, because summer dew points are almost always well above the level at which it turns High.
- See the [gray leaf spot topic page](/topics/gray-leaf-spot) for identification and management.

## Validation and caveats

- Draft (model version 0.1, beta). We ported the model from the Crop Risk Tool, and on the tool's own 2025 weather at Eau Claire, Wisconsin, our probability matched the tool's on all 365 days. That shows we reproduce the tool, not that its predictions are right.
- **The equation saturates in summer.** With nightly lows averaging 59 °F (15 °C), the probability passes 60 % (High) once the month's average lowest dew point is above about 43 °F (6 °C). In July and August it is usually much higher: at Eau Claire from July 1 to August 15, 2025, it ran from about 54 to 61 °F, and the probability from 99.0 to 99.9 %, High on all 46 days. A model that is High every summer day can't tell one week, field or year from another.
- We have checked the port against the authors' document term by term, so the cause isn't a slip in copying it. A coefficient or unit may have been stated wrongly, the second equation may be missing, or the fit may have been made over a whole season, so that it separates spring from summer rather than one summer week from another. These are questions for the authors, and we'll update the model when they answer.
- We don't know where, in which years or on what weather the equation was fitted. The model hasn't been compared with gray leaf spot in Wisconsin fields.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
