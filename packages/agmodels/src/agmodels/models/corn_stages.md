---
id: corn-stages
status: draft
updated: 2026-11-19
summary: Estimates a corn field's growth stage, from emergence through the leaf stages to silking and black layer, from growing degree days since planting and the hybrid's degree-day rating.
sources:
  - Nielsen, Purdue University, on leaf stages (emergence at 100–120 GDD, a leaf collar every 82 GDD to V10, then every 50)
  - Yang et al. 2004, Hybrid-Maize (silking from the hybrid's GDD rating)
  - Neild and Newman 1987, National Corn Handbook NCH-40 (the grain fill stages and the hybrid maturity classes)
  - Nielsen, Purdue University, on grain fill stages (the milk stage; yield lost when plants die before black layer)
  - Abendroth et al. 2011, Iowa State University PMR 1009 (stage definitions and leaf numbers)
---

## What it predicts

The model estimates which growth stage a corn field has reached each day, from planting to physiological maturity:

- **Emergence (VE)** and the **leaf stages** (V1, V2 …), counted by visible leaf collars.
- **Tasseling (VT)** and **silking (R1)**.
- **Grain fill:** blister (R2), milk (R3), dough (R4), dent (R5), half milk line (R5.5) and black layer (R6).

AgWeather's corn disease models (tar spot, gray leaf spot and Gibberella ear rot) take their stages from this model.

## How it works

Growing degree days (GDD) are counted from planting by the modified average method used for corn: the day's low is raised to 50 °F if it's below, both the low and high are capped at 86 °F, and the average less 50 °F is the day's total. Each stage starts at a GDD total set by the hybrid's rating, its GDD from planting to black layer, as printed on the seed bag.

- **Emergence** comes at 110 GDD, within the 100 to 120 that Purdue's Bob Nielsen gives.
- **Leaf stages:** a new leaf collar appears every 82 GDD until V10, then every 50, also from Nielsen.
- **Silking** follows the Hybrid-Maize model of Yang and colleagues (2004), fitted to 107 hybrids, so it moves with the hybrid's rating: about 1,440 GDD for a 2,700 GDD hybrid.
- **Tasseling** is placed one leaf interval (50 GDD) before silking. This is an assumption, so the stage is marked as an estimate, and it sets the hybrid's last leaf stage: about 17 leaves for a 2,500 GDD hybrid and 19 for a 2,700.
- **Grain fill:** the stages from blister to black layer keep the proportions of the time from silking to black layer in Purdue's National Corn Handbook (Neild and Newman 1987), so they stretch or shrink with the hybrid. Milk is placed from Nielsen's figure of about 900 GDD before black layer. Black layer comes at the hybrid's rating.

You choose a rating from 2,100 to 3,100 GDD (early, mid- and full season, the handbook's classes) or enter your own. Without your planting date, the model assumes May 10; maps use a 2,500 GDD hybrid everywhere.

## How to read it

- Use the stages to plan field visits, and check them against the field: a field is at a stage when half its plants have reached it, and leaves are counted by their collars, not their tips.
- **Planting to V7:** watch for seedcorn maggot, cutworms and stalk borer, which do most of their harm to young plants.
- **Tasseling to milk:** leaf diseases such as tar spot and gray leaf spot cost the most yield when they build up now, and this is when a fungicide is most likely to pay. Scout fields weekly through this window.
- **Silking:** Gibberella ear rot infects through the silks, mostly in the first days after they appear.
- **Black layer:** kernels have reached their greatest dry weight and are safe from frost. Before then, a frost that kills the whole plant costs yield, more the earlier it comes: Purdue estimates about 40 % at full dent and about 12 % at half milk line.

The [corn topic page](/topics/corn) describes each stage and its pests in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- For a 2,700 GDD hybrid, the stages from blister to black layer fall within 2.1 % of the National Corn Handbook's degree days, and V9 within 10 GDD of Ohio State's figure. Silking, from Yang and colleagues' equation rather than the handbook, comes about 3 % later than the handbook's 1,400 GDD.
- On four Nebraska and Iowa seasons published by Yang and colleagues, run on reanalysis weather for each site, emergence and silking came within 3 days of the observed dates. Those seasons were published with the silking equation the model uses, so they confirm the method rather than test it on new fields.
- The model hasn't been compared with corn stages observed in Wisconsin fields.
- The model's dates are only as good as the hybrid's rating, and seed companies calculate their ratings differently.
- The placement of tasseling, and the leaf numbers it implies, still have to be checked against Iowa State's guide, which says most hybrids have 18 to 21 leaves.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
