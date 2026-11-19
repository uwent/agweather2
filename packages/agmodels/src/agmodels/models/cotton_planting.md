---
id: cotton-planting
status: draft
updated: 2026-11-19
summary: For each possible planting date, estimates the probability that the cotton stand that emerges falls below a yield-limiting population, from the rain over the 3 days from planting and the minimum temperatures over the 9 days from planting.
sources:
  - Zachary Noel, Auburn University, with funding from Cotton Incorporated (the emergence model, as given to the Crop Protection Network's Crop Risk Tool)
  - Adams, Thapa and Kimura 2019 (yield-limiting plant populations)
  - Rothrock et al. 2012 (seed treatments, weather and seedling disease)
  - Whitaker and Kemerait 2019, University of Georgia Extension (seed treatment of commercial seed in Georgia)
---

## What it predicts

Cold, wet weather in the first days after planting slows emergence and gives seedling diseases such as _Pythium_ time to kill seeds and seedlings. The model treats each day as a possible planting date and estimates the probability that the stand that emerges falls below a yield-limiting population:

- **Very low:** below 1 %.
- **Low:** from 1 %.
- **Moderate:** from 20 %.
- **High:** from 35 %.

## How it works

The model was developed by Zachary Noel at Auburn University, with funding from Cotton Incorporated. It predicts the share of seed that emerges from:

- **Rain** over the 3 days from planting (the planting day and the two after): more rain lowers emergence.
- **The average minimum temperature** over the 9 days from planting: warmer nights raise emergence.
- **_Pythium_ in the field** (present or absent): its presence lowers emergence.
- **The year:** a small trend in the data that raises emergence a little each year.

The predicted share times your seeding rate (30,000, 40,000 or 50,000 seeds per acre) is the expected stand. From the uncertainty of the fit, the model then gives the probability that the stand falls below your yield-limiting population: 15,000 plants per acre, near where lint yield begins to fall steeply, or 20,000. For planting dates in the coming days, it uses the forecast for the days after planting; where a window reaches past the forecast, or rain is missing in it, there's no value.

The model runs from March 15 to June 30 at locations in 17 cotton-growing states, on weather from Open-Meteo, because AgWeather's own maps don't yet reach the South.

## How to read it

- Prefer planting dates with low risk, and treat a Moderate or High rating as a reason to wait for warmer, drier weather if your schedule allows.
- Use the model alongside your state's planting guidelines, which look for warm soil and a warm forecast: in Georgia, for example, soil at 65 °F or warmer at 4 inches for three days in a row and at least 50 DD60s in the five days after planting.
- Where the risk is high, extra seed treatments or an in-furrow fungicide are worth considering, especially in fields with a history of seedling disease.

The [cotton stand establishment topic page](/topics/cotton-stand-establishment) explains how weather and seedling disease affect the stand.

## Validation and caveats

- Draft (model version 0.1, beta).
- The model reproduces the Crop Risk Tool's probabilities in all 2,704 combinations of rain, temperature, _Pythium_, seeding rate and year tested, and on 357 planting dates through 2025. It hasn't been compared with stands counted in fields.
- The fit is unpublished: we don't know its error or the years, rain and temperatures behind it.
- **Seed treatment:** the model was built assuming untreated seed. Commercial seed is often sold treated with fungicides (in Georgia, all of it is), and in 211 trials reported by Rothrock and colleagues (2012), treated seed gave better stands than untreated seed in 119. For treated seed, the model may overstate the risk.
- **The year term** carries the fit's trend past the years it was fitted on, a trend that may not hold.
- **The levels:** the model's author describes the boundaries between levels as arbitrary for now, to be tied to economic losses later.
- Seed quality, soil moisture and crusting aren't inputs, and Open-Meteo's weather for a location hasn't been compared with stations in the South.
