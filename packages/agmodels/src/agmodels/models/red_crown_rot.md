---
id: red-crown-rot
status: draft
updated: 2026-11-19
summary: Predicts the share of soybean plants in a field with red crown rot from temperature and rain in the month before and the month after beginning flowering (R1), once the month after R1 is complete; it has no risk levels, and it hasn't been tested in the United States.
sources:
  - Ochi, Kishi, Kawaguchi and Akamatsu 2026, Phytopathology 116, 1405–1413 (the three equations, from 242 soybean fields in northern Japan)
  - The Crop Protection Network's 2026 red crown rot algorithm (the weights that combine the equations, and its note that no risk levels can be set yet)
  - Crop Protection Network, Red Crown Rot of Soybean, and University of Kentucky, Red Crown Rot of Soybean (PPFS-AG-S-25) (scouting and management)
  - The Crop Risk Tool's red crown rot model (compared)
---

## What it predicts

Red crown rot is a soilborne disease that rots soybean roots and reddens the lower stem. The model predicts its incidence: the percentage of plants in a field that will show symptoms, from the weather in the month before and the month after beginning flowering (R1). It gives one number for the season. It doesn't say whether the fungus is in your field, and means something only where it is.

## How it works

Ochi and colleagues (2026) analyzed surveys of 242 soybean fields in northern Japan over seven seasons and fitted simple equations, each relating incidence to one weather measure. The model uses three:

- **Average temperature in the 31 days from R1.** Warmer weather means more disease, and this measure explained the most.
- **Rain in the 31 days before R1**, while the crop is still growing leaves. More rain means more disease.
- **Rain in the 31 days from R1.** Less rain means more disease.

The Crop Protection Network's 2026 algorithm, which AgWeather follows, combines them in a weighted average: temperature counts for 66 %, rain before R1 for 16 % and rain after R1 for 18 %, in proportion to how much of the variation in disease each explained. The paper fitted the equations to calendar months (July and August); the algorithm sets the windows by R1 instead.

R1 comes from the [soybean stages model](/models/soybean-stages) for your planting date, or from your own date at a location; without either, the model uses July 1. The prediction appears 30 days after R1 (July 31 for R1 on July 1), when the 31 days from R1 are complete (an earlier value would mean guessing the rain still to come), and stays the same after that. Rain on days without data counts as no rain, and the model reports how many such days there were.

## How to read it

- **Read the number as a comparison, not a forecast for your field.** It is the incidence that fields like those in the Japanese study, where the fungus was nearly everywhere, would have had with your weather. Ochi and colleagues linked incidence above 60 % to yield loss in Japan, but the Crop Protection Network's algorithm sets no risk levels yet, so we show the number without one.
- **In Wisconsin, temperature decides it.** July in Wisconsin averages about 68 to 74 °F (cooler in the north), and the prediction mostly follows that temperature. With 2 to 10 inches of rain in each month, the two rain terms together add only about 17 to 24 percentage points.
- **Use it for awareness and planning.** No fungicide applied during the season controls red crown rot. If the fungus has been found in or near your fields, a high prediction is a reason to scout from late summer: dig up plants in yellowing or dying patches, look for a red lower stem and small red fruiting bodies, and have a laboratory confirm it. Rotation, clean equipment, variety choice and seed treatment are planned for the next crop; the [red crown rot topic page](/topics/red-crown-rot) has the details.

## Validation and caveats

- Draft (model version 0.3, beta). The equations were developed in Japan, and the model hasn't been compared with red crown rot in any United States field. The paper's authors called their equations simplified models and said new survey data are needed to compare predictions with measured incidence.
- We ported the model from the Crop Risk Tool and checked it on the tool's own 2025 weather at Eau Claire, Wisconsin. With R1 on July 1, our prediction matched the tool's from July 31 on, and the rain before R1 and the temperature after it matched on every day of the year. That shows we reproduce the tool, not that it is right. That year, the prediction was 31 to 34 % for each R1 date tried.
- Wisconsin's summers are cooler than those in the study. The surveyed fields' August averages ran from about 72 to 84 °F, most of them above 75 °F, so Wisconsin's usual temperatures fall at or below the coolest fields, where the temperature equation rests on few of them.
- Nearly all of the surveyed fields had the disease, and a field's history of red crown rot was the strongest factor in the study. The model doesn't know a field's history, so it can't tell an infested field from a clean one.
- Red crown rot is new to Wisconsin: it was first confirmed in the state in 2025, in one field in Columbia County.
- The combined prediction has a floor: it can't fall below about 7 %, whatever the weather.
- A day without rain data lowers the prediction if it falls before R1 and raises it if it falls after. Read the result with care when more than about three days are missing.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
