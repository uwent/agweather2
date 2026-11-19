---
id: cotton-stand-establishment
title: Cotton stand establishment
kind: agronomic
crops:
  - cotton
scientific_name: Gossypium hirsutum
summary: Getting enough cotton seedlings up and growing after planting; cold soil and rain in the first days after planting, and the seedling diseases they favor, are the main weather risks to a stand in the southern cotton states.
image: images/cotton-stand-establishment.jpg
image_credit: 'Cotton seedlings in a field in Texas. Photo by USDA Natural Resources Conservation Service, Texas, via Wikimedia Commons (File:Cotton seedlings in the 2010 crop year. (25023825111).jpg), public domain (work of the U.S. government); resized.'
status: draft
updated: 2026-11-19
sources:
  - key: adams-2019
    text: 'Adams, C., S. Thapa and E. Kimura. Determination of a plant population density threshold for optimizing cotton lint yield: a synthesis. Field Crops Research 230:11–16, 2019.'
    url: https://doi.org/10.1016/j.fcr.2018.10.005
  - key: rothrock-2012
    text: 'Rothrock, C. S., S. A. Winters, P. K. Miller and others. Importance of fungicide seed treatment and environment on seedling diseases of cotton. Plant Disease 96:1805–1817, 2012.'
    url: https://doi.org/10.1094/PDIS-01-12-0031-SR
  - key: uga-2023
    text: 'A few reminders for planting cotton. University of Georgia Cooperative Extension, Tift County, 2023.'
    url: https://site.extension.uga.edu/tiftcoag/2023/04/a-few-reminders-for-planting-cotton/
  - key: uga-2016
    text: 'Cotton Preparation and Planting. University of Georgia Cooperative Extension, Plow Points, 2016.'
    url: https://site.extension.uga.edu/plowpoints/2016/04/cotton-preparation-and-planting/
  - key: msstate-soil
    text: 'What should be the soil temperature at planting time? Mississippi State University Extension.'
    url: https://extension.msstate.edu/agriculture/crops/cotton/what-should-be-the-soil-temperature-planting-time
  - key: edmisten-2021
    text: 'Edmisten, K. Thoughts on Cotton Planting: Soil Temperatures. NC State Extension, 2021.'
    url: https://cotton.ces.ncsu.edu/2021/04/thoughts-on-cotton-planting
  - key: faske-2023
    text: 'Faske, T., T. Allen, T. Price and T. Spurlock. Pythium Seedling Disease of Cotton. Crop Protection Network, 2023.'
    url: https://cropprotectionnetwork.org/encyclopedia/pythium-seedling-disease-of-cotton
  - key: whitaker-2019
    text: 'Whitaker, J. and R. Kemerait. Seedling Diseases and Management in Cotton. University of Georgia Cooperative Extension, 2019.'
    url: https://site.extension.uga.edu/benhillcoag/2019/05/seedling-diseases-and-management-in-cotton/
  - key: agweather-cotton-planting
    text: 'AgWeather. Cotton planting stand risk model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/cotton-planting.md
  - key: frac-2026
    text: 'Fungicide Resistance Action Committee. FRAC Code List 2026: Fungal Control Agents Sorted by Cross-Resistance Pattern and Mode of Action. CropLife International, 2026.'
    url: https://www.frac.info/media/s1zfrjqa/frac-code-list-2026.pdf
---

Cotton (_Gossypium hirsutum_) is grown across the southern United States, from Virginia to California, and planted in spring. A field's yield starts with its stand: enough seedlings coming up evenly after planting. Cold soil, rain soon after planting and the seedling diseases they favor are the main weather risks to a stand, and a poor one may have to be replanted.[^msstate-soil][^rothrock-2012] This page explains how weather affects stand establishment and how growers time planting around it. Cotton isn't grown in Wisconsin; AgWeather's model for it serves the cotton states.

## How many plants a field needs

Cotton makes up for thin stands well. A synthesis of population studies found that lint yield holds steady across a wide range of plant densities and falls steeply only below about 35,000 plants per hectare (about 14,000 per acre). The common recommendation, 81,000 plants per hectare (about 33,000 per acre), and the higher seeding rates many growers use leave room for losses.[^adams-2019] A stand that comes up near the low end is the one at risk, which is why the weather in the first days after planting matters.

## How weather affects the stand

- **Cold soon after planting.** In the first three days after planting, temperatures of 41 °F or lower can kill seed that has absorbed water, and chilling temperatures, below 50 °F but above freezing, can kill or badly injure a germinating seedling.[^uga-2016][^uga-2023] Planting into cold soil raises the risk of chilling injury.[^msstate-soil]
- **Slow emergence gives disease a head start.** Cool, wet soil, or a cold rain just after planting, slows germination and growth, which gives seedling disease fungi time to attack seeds and seedlings.[^whitaker-2019]
- **Seedling disease.** _Pythium_ species, _Rhizoctonia solani_ and _Fusarium_ species infect seeds and seedlings, and can kill a seed before it emerges (preemergence damping-off). _Pythium_ thrives in cool, saturated soils, especially heavier clay soils, while _Rhizoctonia_ depends less on the weather and is the most common cause in Georgia.[^faske-2023][^whitaker-2019] In a series of standardized seed treatment trials from 1993 to 2004, stands lost to seedling disease rose sharply as the minimum soil temperature in the first three days after planting fell from about 77 °F (25 °C) to 54 °F (12 °C) and as rain increased, and _Pythium_'s share of the losses grew most.[^rothrock-2012]

## Timing planting and protecting the stand

**Wait for warm soil and a warm forecast.** Guidelines differ by state, but they agree on the idea:

- Georgia: plant when the soil is 65 °F or warmer at 4 inches for three days in a row and the forecast gives at least 50 DD60s in the five days after planting.[^uga-2016][^uga-2023] A DD60 is a degree day above 60 °F: the day's average temperature minus 60.[^uga-2023]
- Mississippi: a seedbed at least 68 °F at 2 inches, with dry weather and at least 50 DD60s expected over the next five days.[^msstate-soil]
- North Carolina: 65 °F or more at 10 a.m. is the target, though there's no hard rule. Knowing your seed's cool germination test result, seed size, planting depth, soil moisture and drainage helps you judge how much risk to take.[^edmisten-2021]

**Use good seed and fungicide seed treatments.** Plant high-quality seed with a strong germination rate.[^faske-2023][^whitaker-2019] In those trials, fungicide seed treatments improved stands in more than half of the trials; metalaxyl (FRAC group 4), which controls _Pythium_, and PCNB (group 14), which controls _Rhizoctonia_, each helped in many of them, and newer azoxystrobin (group 11) and triazole (group 3) treatments improved on the old standard.[^rothrock-2012][^frac-2026] PCNB doesn't control _Pythium_, and metalaxyl, mefenoxam (group 4) and etridiazole (group 14) don't control _Rhizoctonia_, so seed is treated with more than one fungicide. In Georgia, all commercial seed comes with at least two.[^whitaker-2019]

**Add protection where the risk is high.** Extra seed treatments or an in-furrow fungicide are worth considering in fields with a history of seedling disease, when cool, wet weather is likely after planting, with poor seed or low seeding rates, and in conservation tillage, though yield benefits have been hard to show in trials, so they aren't needed in every field.[^whitaker-2019] Raised beds warm and drain the soil, which helps against _Pythium_.[^faske-2023]

For planting dates, seeding rates and products in your area, see your state's cotton production guide and extension cotton team, such as the University of Georgia's, Mississippi State's and NC State's.

## AgWeather's models

The [cotton planting stand risk model](/models/cotton-planting) treats each day as a possible planting date and predicts the stand that emerges, in plants per acre, for a seeding rate of 30,000, 40,000 or 50,000 seeds per acre, with a range for the uncertainty of the prediction. The share of seeds that emerge depends on whether _Pythium_ is present in the field, the rain over the 3 days from planting and the average minimum temperature over the 9 days from planting: more rain lowers emergence and warmer nights raise it. The model compares the predicted stand with a yield-limiting population of 15,000 or 20,000 plants per acre: High below it, Moderate from it to 25 % above it, and Low beyond. For planting dates in the coming days, it uses the forecast for the days after planting.[^agweather-cotton-planting]

The model was developed by Zachary Noel at Auburn University with funding from Cotton Incorporated, and it applies to the 17 cotton-growing states, not to Wisconsin. Our maps don't yet reach the South, so it runs at a location you choose, on weather from Open-Meteo. It reproduces the Crop Risk Tool's results exactly, but the fit is unpublished: we don't know its error or the years, rain and temperatures behind it, and it hasn't been compared with stands counted in fields. Its range shows the uncertainty of an average stand, not how much stands vary between fields, which is far more. It includes a small yearly trend in emergence, which we hold at 2025 until the authors tell us the last year of their data. Apart from whether _Pythium_ is present, it doesn't account for seed quality, seed treatments, soil moisture or crusting, so use it alongside the planting guidelines above.[^agweather-cotton-planting]
