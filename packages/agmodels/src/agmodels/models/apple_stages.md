---
id: apple-stages
status: draft
sources:
  - NEWA's apple stage table (degree days base 43 °F from January 1)
  - Agnello (ed.) 2015, Scaffolds Fruit Journal (McIntosh stages at Geneva, New York, over about 26 years)
  - Baskerville and Emin 1969 (the single-sine degree-day method)
  - UW–Madison Fruit Program 2024 (degree days and bud break after a warm winter)
  - Apple stages observed in Wisconsin, 2023–2026 (UW–Madison's fruit program, the Peninsular Agricultural Research Station, growers)
  - Enviroweather's apple stage model (compared)
---

## What it predicts

Many orchard decisions are timed by the trees' stage: when to start scouting, when apple scab's season opens, and when blossoms are open to fire blight. The model estimates the stage of apple buds and flowers each day from degree days, from silver tip to fruit set:

- **Silver tip**: bud scales separate and the silvery leaf tissue shows at the tip.
- **Green tip**: green leaf tissue shows at the bud tip.
- **Half-inch green**: leaves stand out about half an inch from the bud.
- **Tight cluster**: the flower buds are visible, still tightly grouped.
- **Pink**: the flower buds have separated and show pink before opening.
- **Bloom**: flowers open, from the first king blossoms to full bloom.
- **Petal fall**: most petals have fallen.
- **Fruit set**: fruitlets are set and growing.

It also shows the degree days since January 1 behind each stage. The apple scab model starts its season at this model's green tip.

## How it works

Growing degree days (degree days for short) measure the warmth that drives the trees' development. Each day adds the degrees by which its temperature runs above a base of 43 °F, estimated through the day from its high and low by the single-sine method (Baskerville and Emin 1969), with no upper limit. The model adds them up from January 1.

Each stage begins when the total reaches its threshold:

- Silver tip: 75 degree days
- Green tip: 101
- Half-inch green: 165
- Tight cluster: 199
- Pink: 290
- Bloom: 346
- Petal fall: 454
- Fruit set: 580

These are the thresholds NEWA (the Network for Environment and Weather Applications, Cornell University) uses for its apple stages, which many Wisconsin growers and UW–Madison's fruit updates follow. NEWA calls the last stage post petal fall. Each threshold falls inside the range of degree days at which McIntosh reached that stage at Geneva, New York, over about 26 years (Cornell's Scaffolds Fruit Journal, 2015). The thresholds mark when a stage begins, so most sit below the middle of Geneva's range.

NEWA computes its degree days with a slightly different formula from the published single-sine method we use. On the same weather, a stage begins on the same day as NEWA's in nearly every orchard and season, and never more than 2 days apart.

## How to read it

- Use the predicted stages to plan when to walk the orchard and look, not in place of looking. The stages follow McIntosh. Early cultivars such as Zestar and Paula Red run a few days ahead of the model, and later cultivars run behind it.
- Even for McIntosh, a stage's timing at Geneva varied from year to year by two or three days of Wisconsin spring warmth, so treat a predicted date as the start of the days to watch for that stage.
- Record the date your own trees reach green tip and first bloom. At a location, you can enter your green tip date in the apple scab model and your first bloom date in the fire blight model, and they replace the estimates from degree days.
- After a warm late winter, degree days can reach silver tip and green tip weeks before buds move (UW–Madison Fruit Program, 2024). In 2024, 101 degree days, the model's green tip, came on March 14 at Eau Claire. In such a spring, the early stages say only that warmth has accumulated; check the buds.

## Validation and caveats

- Draft (model version 0.1, beta). The thresholds were checked against McIntosh records from Geneva, New York, compared with NEWA's stages on the weather of Wisconsin orchard stations, and tested against 57 stages observed at six Wisconsin sites from 2023 to 2026. No published table of apple stages by degree days for Wisconsin or Michigan was found.
- Against the Wisconsin observations, the model gave the observed stage on most dates, with no lean early or late overall. Early cultivars ran a mean of about 3 days ahead of it.
- Only 9 of the 57 observations name silver tip, green tip or half-inch green, so the early stages are checked mainly against the Geneva records and NEWA rather than Wisconsin orchards. There were no observations from Bayfield, Eau Claire or southeastern Wisconsin.
- The model counts warmth from January 1 alone; it doesn't account for the winter chilling the trees received.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your orchard; a block in a frost pocket or on a warm slope may run behind or ahead.
