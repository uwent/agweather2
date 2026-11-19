---
id: tar-spot
status: draft
updated: 2026-11-18
sources:
  - Webster et al. 2023, Scientific Reports 13, 17064 (the model's equations)
  - The Crop Risk Tool's tar spot model (compared)
---

## What it predicts

The model gives the probability that the past month's weather has favored tar spot increasing in a corn field, from 0 to 100 %. It doesn't say whether the fungus is present: tar spot has to be in the area for the weather to matter.

## How it works

The model averages two equations from Webster and colleagues (2023), fitted to whether tar spot severity increased between two ratings of the same field in Midwest plots and fields. One uses the 30-day average temperature and daily maximum humidity, the other the 30-day average temperature and the 14-day average of humid night hours. In both, warmer weather and long humid nights lower the probability, as the authors found. Risk is shown while corn is from V10 to R3.

## How to read it

- Higher values mean recent weather has been more like the weather when tar spot increased in the study.
- Scout fields when the risk is Moderate or higher during the susceptible stages, and use the [tar spot topic page](/topics/tar-spot) for management.

## Validation and caveats

- Draft (model version 0.3, beta). The equations come from the paper; AgWeather's version reproduces the Crop Risk Tool's, and hasn't been compared with tar spot in Wisconsin fields.
- Humid hours are estimated from gridded humidity, which reads slightly low, so an hour counts at 88 % rather than 90 %; how that changes this model hasn't been measured.
