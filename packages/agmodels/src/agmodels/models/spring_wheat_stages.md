---
id: spring-wheat-stages
status: draft
updated: 2026-11-19
summary: Estimates a spring wheat field's Haun stage, from emergence through flowering to watery-ripe kernels, from growing degree days since planting.
sources:
  - Bauer, Fanning, Enz and Eberlein 1984, NDSU Extension EB-37 (Haun stages from growing degree days, base 32 °F)
  - North Dakota Agricultural Weather Network, wheat growing degree days (the daily rule and the stage table)
---

## What it predicts

The model estimates spring wheat's stage on the Haun scale, which counts leaves on the main stem, from emergence through tillering, the flag leaf, boot, heading and flowering, to watery-ripe kernels (Haun 12.0). It doesn't yet cover grain fill, maturity or winter wheat.

## How it works

The model follows the method of Bauer and colleagues (1984) at North Dakota State University, as the North Dakota Agricultural Weather Network (NDAWN) runs it.

- **Degree days:** each day's growing degree days are the average of the high and low less 32 °F, with temperatures below 32 °F raised to 32. Until the second leaf is out (Haun 2.0, at 395 degree days), the high is capped at 70 °F; after that, at 95 °F.
- **Stages:** emergence (Haun 0.5) comes at 180 degree days from planting, the first leaf is fully out at 252, and a new leaf follows every 143 or so. The flag leaf is visible at 1,181, heading begins at 1,567, flowering runs from 1,739 to 1,768, and kernels are watery ripe at 1,825.

Without your planting date, the model assumes April 25. Enter your own, since planting dates vary widely and stages count from planting.

## How to read it

- Use the leaf stages to time herbicide applications to the labels' leaf stages, and check them in the field: stress can leave plants with fewer leaves on the main stem than the table assumes.
- **Flag leaf to boot:** fungicides for Septoria leaf blotch go on now to protect the flag leaf, and rusts cost the most yield when they infect before the head emerges.
- **Flowering to about 7 days after:** wheat is most susceptible to Fusarium head blight (scab), and fungicides for it work best in this window. Confirm flowering by looking at heads in several places in the field rather than relying on a date. The [wheat scab model](/models/wheat-scab) doesn't yet take its flowering date from this model.

The [spring wheat topic page](/topics/spring-wheat) describes the stages and their pests in more detail.

## Validation and caveats

- Draft (model version 0.2, beta).
- The model reproduces NDAWN's stage table exactly, and its daily degree days follow NDAWN's rule. It hasn't been compared with stages observed in fields, and no published error is available for the dates.
- The table was developed in North Dakota; how well it fits the varieties grown in Wisconsin and Minnesota isn't known.
- Emergence is the least certain step, because planting depth, soil moisture and residue all change it.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
