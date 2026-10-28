---
id: botrytis-onion-botcast
status: draft
sources:
  - Crop Risk Tool docs/botrytis.md
  - VDIFN db/seeds.rb (botrytis-leaf-blight)
---

## Model details

The Botrytis leaf blight model is based on the BOTCAST algorithm described in Sutton et al 1986. The model describes a two-step algorithm, where the first determies if inoculum is likely to be present or not, and the second estimates the risk of infection when potentially present.
