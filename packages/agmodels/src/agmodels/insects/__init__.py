"""The insects (PLAN.md Phase 3 D, D35): one module per insect, each an `INSECT = Insect(...)` with its page beside it.

The Crop Risk Tool's three have life-stage keys; VDIFN's others are its seeds. Degree days are °F and thresholds as
each source set them. Seedcorn maggot, alfalfa weevil and Colorado potato beetle come from the Crop Risk Tool (newer,
with stage labels), replacing VDIFN's versions; VDIFN's adult and larval CPB abundance models stay; its old CPB model
(base 52) is dropped (docs/project-plan.md). VDIFN's entries and crops were generated from `../ag-vdifn/db/seeds.rb`;
their criteria are VDIFN's severity texts. The engine that runs them is `agmodels.phenology`.
"""

CRT = "the Crop Risk Tool"
