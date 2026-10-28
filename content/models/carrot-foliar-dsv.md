---
id: carrot-foliar-dsv
status: draft
sources:
  - Crop Risk Tool docs/alternaria.md
  - VDIFN db/seeds.rb (carrot-foliar)
---

## Model details

This Alternaria model is an implementation of the TOMCAST model described in Pitblado 1992, which builds on the FAST forecaster described by Madden et al 1978. The model generates daily Disease Severity Values (DSVs) based on the mean temperature and duration of leaf wetness periods (eg continuous hours with relative humidity \>90%).
