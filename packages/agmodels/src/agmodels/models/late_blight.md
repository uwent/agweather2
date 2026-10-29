---
id: late-blight-dsv
status: draft
sources:
  - Crop Risk Tool docs/late-blight.md
  - VDIFN db/seeds.rb (late-blight)
---

## Model details

Late blight daily disease severity values (DSVs) are calculated based on the BLITECAST algorithm described by Krause, Massie, and Hyre in 1975 and based on work previously conducted by Wallins. The risk of late blight is then based on the season total and rolling 14-day accumulated DSVs.
