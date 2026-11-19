---
id: frogeye-leaf-spot
status: draft
updated: 2026-11-19
summary: Gives the probability that frogeye leaf spot is present in soybean from 30-day averages of the daily high temperature and humid hours, from beginning bloom (R1) to beginning seed (R5).
sources:
  - Smith and Webster's 2024 frogeye leaf spot algorithm (the equation and risk levels, unpublished)
  - Crop Protection Network, An Overview of Frogeye Leaf Spot (Bradley et al. 2016), and Iowa State Extension (Stoetzer 2018) (scouting and fungicide timing)
  - The Crop Risk Tool's frogeye leaf spot model (compared)
---

## What it predicts

Frogeye leaf spot is a fungal leaf disease of soybean favored by warm, humid weather. The model gives a probability, from 0 to 100 %, that the disease is present, from the past month's weather. Its authors' document calls it the probability of "frogeye leaf spot presence"; the Crop Risk Tool describes it as the probability of spores being present. Neither says whether the equation was fitted to spores caught in traps or to disease in fields. The fungus has to be in the area, which usually means soybean residue from an infected crop, for the weather to matter.

## How it works

The model is one equation, which the Crop Protection Network's Crop Risk Tool credits to Damon Smith (UW–Madison) and Wade Webster (North Dakota State University). A 2024 algorithm document gives the equation and its risk levels; we haven't found the fit itself published. It uses two 30-day averages:

- the daily high temperature, and
- the hours each day with relative humidity of 80 % or more.

Both raise the probability: a warmer, more humid month gives a higher risk. Risk is Low from 1 %, Moderate from 40 % and High from 50 %, the authors' default action threshold. The risk is shown from beginning bloom (R1) to beginning seed (R5), taken from the [soybean stages model](/models/soybean-stages) or your own dates, between June 15 and September 7.

## How to read it

- A rising probability means the weather is becoming more favorable to the fungus. Don't decide on a fungicide from the model alone: weigh the risk together with the crop's stage, the field's history and the variety's resistance.
- Scout the upper canopy from flowering on, starting with susceptible varieties and fields where frogeye leaf spot has been found before.
- Fungicides applied from beginning pod (R3) to full pod (R4) work best. Don't rely on strobilurin (QoI, FRAC group 11) fungicides alone: strains of the fungus that resist them have been found in North America, and a survey found them in nearly every field sampled across Iowa. Scout again about two weeks after spraying to see whether the fungicide worked.
- See the [frogeye leaf spot topic page](/topics/frogeye-leaf-spot) for identification and management.

## Validation and caveats

- Draft (model version 0.1, beta). We ported the model from the Crop Risk Tool, and on the tool's own 2025 weather at Eau Claire, Wisconsin, our probability matched the tool's on all 365 days. That shows we reproduce the tool, not that its predictions are right.
- On that weather, from June 15 to September 7, 2025, the probability ran from 12 to 41 %: Low on 80 days and Moderate on 5, never High. Unlike the [gray leaf spot model](/models/gray-leaf-spot), it moves with the weather across a Wisconsin summer.
- We don't know where, in which years or on what weather the equation was fitted. Only its authors can tell us. The model hasn't been compared with frogeye leaf spot in Wisconsin fields.
- Humid hours are counted from gridded humidity, which reads slightly low near saturation; for models that count hours at 90 %, we count them at 88 % to make up for it. We count this model's hours at 80 % as a station would, and haven't measured whether gridded humidity misses some of them.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
