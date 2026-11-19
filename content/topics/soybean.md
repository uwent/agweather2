---
id: soybean
title: Soybean
kind: crop
crops:
  - soybean
scientific_name: Glycine max
summary: One of Wisconsin's major field crops, grown on about 2 million acres a year; its growth stages, from emergence through flowering and pod fill, time the decisions on white mold, leaf diseases and soybean aphid.
image: images/soybean.jpg
image_credit: 'A soybean field in Clark County, Wisconsin. Photo by Jeff the quiet, via Wikimedia Commons (File:Grant Clark County Wisc soybeans.jpg), CC0 (public domain dedication); resized.'
status: draft
updated: 2026-11-18
sources:
  - key: nass-wi-stats
    text: 'Wisconsin 2026 Agricultural Statistics (annual bulletin; field crops 2021–2025 and usual planting dates). USDA National Agricultural Statistics Service, Wisconsin Field Office, and Wisconsin Department of Agriculture, Trade and Consumer Protection, 2026.'
    url: https://www.nass.usda.gov/Statistics_by_State/Wisconsin/Publications/Annual_Statistical_Bulletin/
  - key: conley-2018
    text: 'Conley, S. Soybean Planting Date and Maturity Group Considerations. UW–Madison Integrated Pest and Crop Management, Wisconsin Crop Manager, 2018.'
    url: https://ipcm.wisc.edu/blog/2018/04/soybean-planting-date-and-maturity-group-considerations
  - key: conley-pivot
    text: 'Conley, S. Agronomic Pivot Points for Mid-May Planted Soybeans (Badger Crop Connect). UW–Madison Division of Extension, Crops and Soils.'
    url: https://cropsandsoils.extension.wisc.edu/articles/agronomic-pivot-points-for-mid-may-planted-soybeans/
  - key: isu-stages
    text: 'Soybean Growth Stages (after Soybean Growth and Development, PM 1945). Iowa State University Extension and Outreach, Integrated Crop Management, reviewed 2026.'
    url: https://crops.extension.iastate.edu/encyclopedia/soybean-growth-stages
  - key: uw-soy-development
    text: 'Soybean Growth and Development (adapted from Iowa State University Special Report 53, How a Soybean Plant Develops). UW–Madison Corn Agronomy, 2015.'
    url: https://corn.aae.wisc.edu/Crops/Soybean/L004.aspx
  - key: a3646-2025
    text: 'Dewerff, R., E. Bick, P. J. Liesch, G. Nice, M. Renz, D. Smith, R. Werle and J. Kampa. Pest Management in Wisconsin Field Crops (A3646). UW–Madison Division of Extension, 2025.'
    url: https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf
  - key: watson-smith-2026
    text: 'Watson, Q. and D. Smith. Sclerotinia Stem Rot of Soybean (UW Plant Disease Facts D0099). UW–Madison Plant Pathology, revised 2026.'
    url: https://pddc.wisc.edu/2015/08/16/sclerotinia-stem-rot-of-soybean/
  - key: bradley-2016
    text: 'Bradley, C., M. Chilvers, A. Freije and others. An Overview of Frogeye Leaf Spot (CPN-1017). Crop Protection Network, 2016.'
    url: https://cropprotectionnetwork.org/publications/an-overview-of-frogeye-leaf-spot
  - key: price-2025
    text: 'Price, T., T. Allen, V. Doyle and others. An Overview of Cercospora Leaf Blight (CPN-1030). Crop Protection Network, 2025.'
    url: https://cropprotectionnetwork.org/publications/an-overview-of-cercospora-leaf-blight-of-soybean
  - key: wcm
    text: 'Wisconsin Crop Manager archive. UW–Madison Integrated Pest and Crop Management.'
    url: https://ipcm.wisc.edu/wcm/
  - key: smith-rcr-2026
    text: 'Smith, D. 2026 Mid-Season Wisconsin Field Crop Disease Update (video and transcript). UW–Madison Division of Extension, Crops and Soils, 2026.'
    url: https://cropsandsoils.extension.wisc.edu/articles/2026-mid-season-wisconsin-field-crop-disease-update/
  - key: agweather-soybean-stages
    text: 'AgWeather. Soybean growth stages model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/soybean-stages.md
  - key: agweather-red-crown-rot
    text: 'AgWeather. Red crown rot model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/red-crown-rot.md
---

The soybean (_Glycine max_) is one of Wisconsin's major field crops: the state's farmers plant about 2 million acres a year, most of it between early May and mid-June, and Dane, Rock, Dodge and Grant counties grow the most.[^nass-wi-stats] Many of the crop's diseases and pests strike at particular growth stages, so a grower's decisions on fungicides and insecticides are timed by the crop's stage rather than the calendar. This page describes those stages and links to the diseases AgWeather models.

## Soybeans in Wisconsin

Planting early pays in Wisconsin. Early May planting has been shown to raise yields, partly because early-planted soybeans spend longer in their reproductive stages during the longest days of the year: in UW–Madison's research, a May 1 planting spent about 60 days from beginning bloom (R1) to full seed (R6), against about 45 days for a June 1 planting.[^conley-2018] In southern Wisconsin, yield potential falls by about 2 bushels per acre for each week planting is delayed past about April 10.[^conley-pivot]

In UW–Madison trials planted in mid-May, varieties from maturity group 1 through 2.9 yielded about the same, and UW–Madison advises against switching to an earlier group when planting is delayed into early June.[^conley-pivot] Thirty-inch rows suit soybeans planted in April, while narrower rows of 15 to 20 inches suit mid-May and later plantings; UW–Madison's usual suggestion is about 140,000 seeds per acre.[^conley-pivot] Narrow rows and high populations also raise the risk of white mold, so fields with a history of it may need wider rows and fewer seeds.[^a3646-2025]

## Growth stages

A field is at a stage when at least half its plants have reached it.[^isu-stages]

- **VE, emergence:** the cotyledons have been pulled through the soil surface, usually 1 to 2 weeks after planting, depending on soil moisture, soil temperature and planting depth.[^isu-stages][^uw-soy-development]
- **VC, unifoliate leaves:** the first pair of single leaves has unfolded.[^isu-stages]
- **V1, V2 and on:** each stage adds a fully unfolded trifoliolate leaf. New V-stages appear about every 5 days up to V5, then about every 3 days.[^isu-stages][^uw-soy-development]
- **R1, beginning bloom:** at least one open flower on any node.
- **R2, full bloom:** an open flower at one of the two uppermost nodes.
- **R3, beginning pod:** a pod 3/16 inch long at one of the four uppermost nodes.
- **R4, full pod:** a pod ¾ inch long at one of the four uppermost nodes.
- **R5, beginning seed:** a seed ⅛ inch long in a pod at one of the four uppermost nodes on the main stem.
- **R6, full seed:** a pod with a green seed that fills its cavity at one of the four uppermost nodes.
- **R7, beginning maturity:** one normal pod on the main stem has reached its mature color.
- **R8, full maturity:** 95 % of the pods have reached their mature color.[^isu-stages]

## What the stages mean for pests and diseases

- **Beginning bloom to beginning pod (R1 to R3):** [white mold](/topics/white-mold) infects through the flowers, so fungicide decisions for it are made in this window.[^watson-smith-2026]
- **Beginning bloom to beginning seed (R1 to R5):** soybean aphids, which spend the winter on buckthorn, are worth treating when about 80 % of the field averages 250 aphids per plant and the numbers are rising. Treatments in this window give the best yield response; by full seed (R6) it is too late to protect yield. UW–Madison advises intensive scouting from the mid-vegetative stages, usually mid- to late June.[^a3646-2025]
- **Pod development (R3 to R4):** fungicides for [frogeye leaf spot](/topics/frogeye-leaf-spot) work best now.[^bradley-2016]
- **Beginning seed (R5) on:** [Cercospora leaf blight](/topics/soybean-cercospora-leaf-blight) usually shows on the upper leaves.[^price-2025]
- **Around beginning bloom (R1):** [red crown rot](/topics/red-crown-rot), a root and stem rot long known in the South, has spread through the Midwest and was first confirmed in Wisconsin in 2025, in one field in Columbia County.[^smith-rcr-2026] AgWeather's model links it to the weather in the month before and the month after R1.[^agweather-red-crown-rot]

Late planting raises the risk from leaf diseases: yield losses from them are more frequent in soybeans planted after June 1.[^a3646-2025]

## Monitoring

- Record each field's planting date, variety and maturity group, and the dates it reaches beginning bloom (R1) and beginning pod (R3). AgWeather's disease models use these stages.
- Read UW–Madison's [Wisconsin Crop Manager](https://ipcm.wisc.edu/wcm/) in season for research and scouting updates.[^a3646-2025][^wcm]
- Scout for soybean aphids weekly from the mid-vegetative stages, usually mid- to late June, counting aphids on 20 to 30 plants across each field.[^a3646-2025]

## Management

Many problems are settled before planting. Rotating with corn, small grains or most forages deprives soybean pathogens of a host, since few of them infect other crops, and residue that breaks down before the next soybean crop carries fewer diseases.[^a3646-2025] Balanced phosphorus and potash help, too: shortages raise losses to several diseases and to soybean cyst nematode.[^a3646-2025] Varieties differ widely in their resistance to white mold and other diseases; UW–Madison's Wisconsin Soybean Variety Tests (A3654) compare them.[^a3646-2025] For products, see UW–Madison's [Pest Management in Wisconsin Field Crops (A3646)](https://cropsandsoils.extension.wisc.edu/files/2025/01/A3646_2025_web.pdf); for planting dates, row widths and seeding rates, see UW–Madison's [Agronomic Pivot Points for Mid-May Planted Soybeans](https://cropsandsoils.extension.wisc.edu/articles/agronomic-pivot-points-for-mid-may-planted-soybeans/).

## AgWeather's models

- The [soybean stages model](/models/soybean-stages) estimates each day's stage, from emergence to beginning maturity (R7), from planting date, maturity group, seeding depth, temperature and day length. It follows the SOYDEV model published by Setiyono and others in 2007. On six published seasons at Lincoln, Nebraska, it put beginning bloom within 6 days of the observed date and beginning maturity within 3 days; those seasons were probably among the data the model was built from, and it hasn't yet been checked against Wisconsin fields. It places R2, R3, R4 and R6 between the stages it predicts, marked as estimates, and doesn't predict R8. Maps assume maturity group 2.0 everywhere.[^agweather-soybean-stages]
- The [white mold model](/models/white-mold) gives the chance that the fungus's spore cups are present, from R1 to R3.
- The [frogeye leaf spot model](/models/frogeye-leaf-spot) gives the chance its spores are present, from R1 to R5.
- The [soybean Cercospora model](/models/soybean-cercospora) gives the chance of spores of three Cercospora species, from R3 to R6.
- The [red crown rot model](/models/red-crown-rot) predicts the share of plants with symptoms from the weather around R1. It was developed in Japan and hasn't been tested in the United States.[^agweather-red-crown-rot]

The three leaf and stem disease models were copied from the Crop Protection Network's Crop Risk Tool and haven't yet been compared with disease in Wisconsin fields; their pages explain their limits. At a location, you can enter your own planting or emergence date and maturity group in place of the typical dates, and the disease models follow the stages they give.
