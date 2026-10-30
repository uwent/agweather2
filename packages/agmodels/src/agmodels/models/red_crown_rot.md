---
id: red-crown-rot
status: draft
sources:
  - Crop Risk Tool docs/red-crown-rot.md
---

## Model details

This model predicts the field-level incidence of red crown rot (percent of plants showing symptoms) from weather around the beginning of flowering (R1). It is based on logistic regression models developed by Ochi et al. (2026) from surveys of 242 soybean fields in northern Japan. Three weather variables are used:

- **Mean air temperature** during the 31 days beginning on R1. Higher temperatures (above about 26°C / 79°F) are associated with higher incidence.
- **Total precipitation** during the 31 days before R1 (vegetative stage). Wetter conditions (above about 200 mm / 8 in) are associated with higher incidence.
- **Total precipitation** during the 31 days beginning on R1 (reproductive stage). Drier conditions (below about 100 mm / 4 in) are associated with higher incidence.

Each variable predicts incidence separately, and the three predictions are combined into a weighted average based on how well each variable explained disease incidence (temperature 66%, vegetative precipitation 16%, reproductive precipitation 18%). Use the R1 date slider in the model options to set the flowering date, which applies to all sites. Because the prediction is sensitive to the R1 date, try a range of dates to see how timing affects risk. Until 31 days after R1, the prediction uses the mean temperature so far and projects precipitation to a full 31 days based on the average daily rainfall so far. Days without precipitation data count as no rain, and the page says how many there were.

Provisional risk categories: Very low (less than 5% incidence), Low (5-30%), Moderate (30-60%), and High (60% or greater). Incidence above 60% has been associated with considerable yield loss. These thresholds have not been validated in the United States. Past history of red crown rot in a field was the strongest predictor of disease in the original study, and is not included in this model.
