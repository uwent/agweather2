---
id: cotton-planting
status: draft
updated: 2026-11-19
summary: For each possible planting date, predicts the cotton stand that emerges, in plants per acre, from the rain over the 3 days from planting and the minimum temperatures over the 9 days from planting, and compares it with a yield-limiting stand.
sources:
  - Zachary Noel, Auburn University, with funding from Cotton Incorporated (the emergence model, as given to the Crop Protection Network's Crop Risk Tool)
  - Adams, Thapa and Kimura 2019 (yield-limiting plant populations)
  - Rothrock et al. 2012 (seed treatments, weather and seedling disease)
  - Whitaker and Kemerait 2019, University of Georgia Extension (seed treatment of commercial seed in Georgia)
---

## What it predicts

Cold, wet weather in the first days after planting slows emergence and gives seedling diseases such as _Pythium_ time to kill seeds and seedlings. The model treats each day as a possible planting date and predicts the **stand**, the number of plants per acre that emerge, with a range around it. It rates each date by how the predicted stand compares with your yield-limiting stand:

- **Low:** the predicted stand is at least 25 % above the limit.
- **Moderate:** the predicted stand is at the limit or less than 25 % above it.
- **High:** the predicted stand is below the limit.

## How it works

The model was developed by Zachary Noel at Auburn University, with funding from Cotton Incorporated. It predicts the share of seed that emerges from:

- **Rain** over the 3 days from planting (the planting day and the two after): more rain lowers emergence.
- **The average minimum temperature** over the 9 days from planting: warmer nights raise emergence.
- **_Pythium_ in the field** (present or absent): its presence lowers emergence.
- **The year:** a small trend in the fit's data that raises emergence a little each year. We hold it at 2025, so it doesn't keep rising in later years.

The predicted share times your seeding rate (30,000, 40,000 or 50,000 seeds per acre) is the predicted stand. The range shown with it is the fit's 95 % confidence interval: where the average stand of many fields planted in the same weather is likely to fall. Your yield-limiting stand is 15,000 plants per acre, near where lint yield begins to fall steeply, or 20,000.

For planting dates in the coming days, the model uses the forecast for the days after planting. Where a window reaches past the forecast, rain is missing in it, or more than 2 of the 9 minimum temperatures are missing, there's no value.

The model runs from March 15 to June 30 at locations in 17 cotton-growing states, on weather from Open-Meteo, because AgWeather's own maps don't yet reach the South.

## How to read it

- Prefer planting dates with a Low rating, and treat a Moderate or High rating as a reason to wait for warmer, drier weather if your schedule allows.
- The range around the predicted stand is the uncertainty of an average, not the spread you'd see between fields. Stands in single fields vary much more than the range shows, so leave a margin above your yield-limiting stand.
- Use the model alongside your state's planting guidelines, which look for warm soil and a warm forecast: in Georgia, for example, soil at 65 °F or warmer at 4 inches for three days in a row and at least 50 DD60s in the five days after planting.
- Where the rating is Moderate or High, extra seed treatments or an in-furrow fungicide are worth considering, especially in fields with a history of seedling disease.

The [cotton stand establishment topic page](/topics/cotton-stand-establishment) explains how weather and seedling disease affect the stand.

## Validation and caveats

- Draft (model version 0.2, beta).
- The model reproduces the Crop Risk Tool's emergence model and its uncertainty in all 2,704 combinations of rain, temperature, _Pythium_, seeding rate and year tested, and on 357 planting dates through 2025. It hasn't been compared with stands counted in fields.
- **What changed in version 0.2:** the Crop Risk Tool, and our version 0.1, showed the probability that the stand falls below the limit. That probability measured how sure the fit is of the average stand, not how much stands vary from field to field, so it was nearly always close to 0 or 100 % and depended more on the seeding rate and limit than on the weather. Until the model's authors give us the measure of field-to-field spread from their fit, we show the predicted stand and its range instead, and rate it against the limit.
- The fit is unpublished: we don't know its error or the years, rain and temperatures behind it.
- **Seed treatment:** the model was built assuming untreated seed. Commercial seed is often sold treated with fungicides (in Georgia, all of it is), and in 211 trials reported by Rothrock and colleagues (2012), treated seed gave better stands than untreated seed in 119. For treated seed, the model may underestimate the stand.
- **The year term:** we hold it at 2025 until the authors tell us the last year of their data.
- **The levels:** the 25 % margin for Moderate is our choice, not the authors'; they describe their own risk boundaries as arbitrary for now, to be tied to economic losses later.
- Seed quality, soil moisture and crusting aren't inputs, and Open-Meteo's weather for a location hasn't been compared with stations in the South.
