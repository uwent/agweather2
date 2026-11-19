---
id: soybean-stages
status: draft
updated: 2026-11-19
summary: Estimates a soybean field's growth stage, from emergence to beginning maturity, from temperature and day length since planting, for any maturity group.
sources:
  - Setiyono et al. 2007, the SOYDEV model (development rates from temperature and day length, by maturity group)
  - Fehr and Caviness 1977 (the soybean stages)
---

## What it predicts

The model estimates which growth stage a soybean field has reached each day, from planting to beginning maturity:

- **Emergence (VE)**, the **cotyledon stage (VC)** and the **node stages** (V1, V2 …).
- **The reproductive stages** from beginning bloom (R1) to beginning maturity (R7).

AgWeather's soybean disease models (white mold, frogeye leaf spot, soybean Cercospora and red crown rot) take their stages from this model.

## How it works

The model is SOYDEV, published by Setiyono and colleagues in 2007 from soybean trials at Lincoln, Nebraska. Each day adds to the progress of the current phase at a rate set by the day's mean temperature and, for flowering and pod fill, the day length at your latitude. A phase is complete when its progress reaches 1. The rates depend on the maturity group through the authors' general equations, fitted to 21 varieties of maturity groups 0.8 to 4.2.

- **Emergence** comes when the seedling, growing with warmth above 41 °F (5 °C), reaches the soil surface from your seeding depth (1, 1¼ or 1½ inches). You can instead enter your emergence date.
- **Leaves and nodes** follow temperature, fastest near 88 °F (31 °C). As in indeterminate varieties, node production slows late in pod set, between full pod (R4) and beginning seed (R5), and stops about 3 to 4 weeks later; semi-determinate varieties aren't offered.
- **Flowering:** after VC, soybeans need short enough days to start flowering, and the day length that triggers it depends on the maturity group. Then temperature sets the time to R1.
- **Pod and seed fill:** from R1, temperature and day length set the time to beginning seed (R5) and beginning maturity (R7).

The model predicts R1, R3.5 (halfway through pod set), R5 and R7 directly. R2, R3, R4 and R6 are placed evenly between them and marked as estimates. Full maturity (R8) isn't predicted.

You choose a maturity group from 0 to 4 (or enter your own). Groups below 0.8 extend the authors' equations beyond the varieties they tested. Without your planting date, the model assumes May 17; maps use maturity group 2.0 everywhere.

## How to read it

- Use the stages to plan field visits, and confirm them in the field: R1 is one open flower anywhere on the main stem, and R3 a pod 3/16 inch long at one of the four uppermost nodes.
- **Beginning bloom to beginning pod (R1 to R3):** white mold infects through the flowers, so fungicide decisions for it are made in this window.
- **Beginning bloom to beginning seed (R1 to R5):** scout for soybean aphids; treatments in this window give the best yield response, and by full seed (R6) it's too late to protect yield.
- **Pod development (R3 to R4):** fungicides for frogeye leaf spot work best now.

The [soybean topic page](/topics/soybean) describes each stage and its pests in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- On six seasons at Lincoln, Nebraska, published with the model, started from the observed emergence and run on reanalysis weather for the site, beginning bloom came within 6 days of the observed date and beginning maturity within 3 days, with a typical error of 2.9 days for beginning bloom. The authors report a typical error of 3.6 days for this form of the model. These seasons were probably among the data the model was built from, so they confirm AgWeather's version of it rather than test it on new fields.
- Emergence from planting hasn't been checked against observed dates, and the model hasn't been compared with soybean stages in Wisconsin fields.
- The node rates were read from the paper's figures, since the paper gives points rather than an equation.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
