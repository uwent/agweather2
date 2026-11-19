---
id: corn
title: Corn
kind: crop
crops:
  - corn
scientific_name: Zea mays
summary: A major Wisconsin field crop, grown for grain and for the silage that feeds its dairy herds; its leaf and silking stages time the season's work against leaf diseases, ear rots and insects.
image: images/corn.jpg
image_credit: 'A cornfield in Wisconsin in late September. Photo by Wikideas1, via Wikimedia Commons (File:Corn field in Wisconsin.jpg), CC0 1.0 (public domain dedication); resized.'
status: draft
updated: 2026-11-18
sources:
  - key: datcp-stats
    text: 'Wisconsin Agricultural Statistics. Wisconsin Department of Agriculture, Trade and Consumer Protection.'
    url: https://datcp.wi.gov/Pages/Publications/WIAgStatistics.aspx
  - key: pbs-2025
    text: 'A big corn crop in 2025 creates a tricky price situation for Wisconsin corn growers. PBS Wisconsin, 2025.'
    url: https://pbswisconsin.org/news-item/a-big-corn-crop-in-2025-creates-a-tricky-price-situation-for-wisconsin-corn-growers/
  - key: uw-late-planting
    text: 'Corn Late-Planting. UW–Madison Corn Agronomy, updated 2019.'
    url: https://corn.agronomy.wisc.edu/Management/L010.aspx
  - key: lauer-2022
    text: 'Lauer, J. Planting date effects on corn grain and forage yield. UW–Madison Integrated Pest and Crop Management, 2022.'
    url: https://ipcm.wisc.edu/blog/2022/04/planting-date-effects-on-corn-grain-and-forage-yield/
  - key: licht-2026
    text: 'Licht, M. Corn Growth Stages. Iowa State University Extension and Outreach, reviewed 2026.'
    url: https://crops.extension.iastate.edu/encyclopedia/corn-growth-stages
  - key: nielsen-vstages
    text: 'Nielsen, R. L. Use Thermal Time to Predict Leaf Stage Development in Corn. Purdue University, 2019.'
    url: https://www.agry.purdue.edu/ext/corn/news/timeless/VStagePrediction.html
  - key: nielsen-grainfill
    text: 'Nielsen, R. L. Grain Fill Stages in Corn. Purdue University, 2021.'
    url: https://www.agry.purdue.edu/ext/corn/news/timeless/GrainFill.html
  - key: a3646-2025
    text: 'Dewerff, R., E. Bick, P. J. Liesch, G. Nice, M. Renz, D. Smith, R. Werle and J. Kampa. Pest Management in Wisconsin Field Crops (A3646). UW–Madison Division of Extension, 2025.'
    url: https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf
  - key: cpn-overview-2026
    text: 'Telenko, D., M. Bish, B. Camiletti, M. Chilvers, T. Jackson-Ziems, D. Plewa, A. Robertson, M. Shires, D. Smith, A. Tenuta, K. Wise and Y. Zeng. An Overview of Tar Spot (CPN-2012). Crop Protection Network, revised 2026.'
    url: https://cropprotectionnetwork.org/publications/an-overview-of-tar-spot
  - key: hartschuh-2026
    text: 'Hartschuh, J., P. Paul and S. Karhoff. Vomitoxin management and corn fungicide decisions. C.O.R.N. Newsletter 2026-23, Ohio State University Extension, 2026.'
    url: https://agcrops.osu.edu/newsletter/corn-newsletter/2026-23/vomitoxin-management-and-corn-fungicide-decisions-during
  - key: agweather-corn-stages
    text: 'AgWeather. Corn stages model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/corn-stages.md
---

Corn (_Zea mays_) is grown across Wisconsin for grain and for silage. Wisconsin grows more corn for silage than any other state, and silage is a mainstay of feed for the state's dairy herds.[^datcp-stats][^pbs-2025] Much of the season's pest and disease work is timed by the crop's growth stage, because leaf diseases, ear rots and insects each matter most at particular stages. This page describes those stages and links to the pests and diseases AgWeather models.

## Corn in Wisconsin

The best time to plant corn for grain is around May 1 in southern Wisconsin and May 7 in the north, and at Arlington planting around May 1 also gives the most silage. Yields hold up well into May, then fall faster: at Arlington, grain yield drops about half a bushel per acre per day for planting around May 15, and 2.5 bushels per day by June 1, when the loss reaches about 30 %.[^uw-late-planting][^lauer-2022]

Hybrids are rated by relative maturity (RM) or by the growing degree days they need from planting to black layer.[^uw-late-planting][^agweather-corn-stages] When planting runs late, UW–Madison suggests switching to earlier hybrids around May 20 in most of the state, and again around June 1 in the south: about 5 RM units earlier than full season for planting on May 20, and about 15 units earlier for June 1.[^uw-late-planting]

## Growth stages

Corn is staged by counting visible leaf collars, and a field is at a stage when at least half its plants have reached it.[^licht-2026]

- **VE (emergence):** the shoot breaks the soil surface, typically 100 to 120 growing degree days after planting.[^licht-2026][^nielsen-vstages]
- **V1, V2 … V(n):** each stage is a new leaf with a visible collar. Leaves appear about every 82 degree days until V10, then about every 50. Most hybrids have 18 to 21 leaves.[^licht-2026][^nielsen-vstages]
- **VT (tasseling):** the lowest branch of the tassel is visible.[^licht-2026]
- **R1 (silking):** silks show outside the husks and pollination begins. Silks stay receptive for up to 10 days but decline after about 5.[^licht-2026][^nielsen-grainfill]
- **R2 (blister) to R5 (dent):** kernels fill, from watery blisters through milk (R3) and dough (R4) to dent, about 31 to 33 days after silking.[^licht-2026][^nielsen-grainfill]
- **R6 (physiological maturity):** kernels reach their greatest dry weight, about 55 to 65 days after silking, and are safe from frost. A black layer forms at the base of the kernel soon after.[^licht-2026][^nielsen-grainfill]

Stages follow warmth, so [degree days](/topics/degree-days) predict them better than the calendar. Corn's degree days count from a base of 50 °F, with highs capped at 86 °F.[^agweather-corn-stages]

## What the stages mean for pests and diseases

- **Planting and emergence:** [seedcorn maggot](/topics/seedcorn-maggot) attacks seed in the soil, especially where sod has been broken for corn; insecticidal seed treatments control it. Watch emerging fields for leaf feeding by young [black cutworms](/topics/black-cutworm), which comes before the larger larvae start cutting plants.[^a3646-2025]
- **V1 to V7:** [stalk borer](/topics/stalk-borer) larvae move in from grassy edges and weeds; once plants reach V7, they are unlikely to be killed.[^a3646-2025]
- **Whorl stage, from mid-June:** the first generation of [European corn borer](/topics/european-corn-borer) feeds in the whorls of early-planted corn, and the second generation is drawn to late-planted fields.[^a3646-2025]
- **Mid-June to August:** [corn rootworm](/topics/corn-rootworm) larvae feed on roots from mid-June, and the beetles feed on silks and pollen from early July. In most of the state, rotating away from corn controls them, because their larvae starve in other crops.[^a3646-2025]
- **Silking to grain fill:** [corn earworm](/topics/corn-earworm) lays eggs on fresh silks, and [western bean cutworm](/topics/western-bean-cutworm) larvae feed in the ears.[^a3646-2025]
- **Silking:** [Gibberella ear rot](/topics/gibberella-ear-rot) infects through wet silks, mostly in the first days of silking, and produces the toxin DON.[^hartschuh-2026]
- **Tasseling to milk:** leaf diseases such as [tar spot](/topics/tar-spot) and [gray leaf spot](/topics/gray-leaf-spot) cost the most yield when they build up now, and this is when a fungicide is most likely to pay.[^a3646-2025][^cpn-overview-2026]

## Monitoring

- Record each field's planting date and hybrid, with its relative maturity or degree-day rating. Stage and disease models count from planting.[^agweather-corn-stages]
- Scout weekly, with extra care at emergence and from tasseling to milk, and check your stages against the field, since a hybrid's degree-day rating is the seed company's own figure.[^a3646-2025][^agweather-corn-stages]
- Read UW–Madison's [Pest Management in Wisconsin Field Crops (A3646)](https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf) for thresholds and scouting methods for each pest.

## Management

Many problems are settled before planting. Crop rotation and residue management reduce the diseases that overwinter in corn residue and the corn rootworms that need corn roots. Hybrids differ widely in their resistance to leaf diseases, ear rots and stalk rots, so choose by your fields' history and local hybrid trials.[^a3646-2025] Late-planted corn often runs a higher risk of yield-reducing leaf disease, so plant on time where you can, with a hybrid suited to the planting date.[^a3646-2025][^uw-late-planting] For products, see [A3646](https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf); for planting dates and hybrid choice, see UW–Madison Corn Agronomy's [late-planting guide](https://corn.agronomy.wisc.edu/Management/L010.aspx) and Iowa State's [Corn Growth Stages](https://crops.extension.iastate.edu/encyclopedia/corn-growth-stages).

## AgWeather's models

- The [corn stages model](/models/corn-stages) estimates each field's stage, from emergence through the leaf stages to silking and black layer, from degree days after planting and the hybrid's degree-day rating. It matches its published sources closely, and came within 3 days of observed emergence and silking in four Nebraska and Iowa seasons, though those seasons were published with the silking equation it uses, so they confirm the method rather than test it on new fields. It hasn't been checked against Wisconsin fields. Maps use a 2,500 degree-day hybrid everywhere.[^agweather-corn-stages]
- The [tar spot model](/models/tar-spot) and the [gray leaf spot model](/models/gray-leaf-spot) show leaf disease risk from V10 to milk, and the [Gibberella ear rot DON model](/models/gibberella-ear-rot-don) shows the risk of DON at silking. All three take their stages from the corn stages model.
- Degree-day models follow [European corn borer](/models/european-corn-borer), [corn earworm](/models/corn-earworm), [western bean cutworm](/models/western-bean-cutworm), [corn rootworm](/models/corn-rootworm), [black cutworm](/models/black-cutworm), [variegated cutworm](/models/variegated-cutworm), [stalk borer](/models/stalk-borer) and [seedcorn maggot](/models/seedcorn-maggot). Each insect's page explains what its model does and its limits.

At a location, you can enter your own planting date and hybrid, and the stages and disease risks follow them.
