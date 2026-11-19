---
id: rye-biomass
status: draft
updated: 2026-11-19
summary: Estimates the spring biomass of a fall-planted cereal rye cover crop from growing degree days since planting, and compares it with the biomass each cover crop goal needs.
sources:
  - Colet et al. 2026, UW–Madison, Crop, Forage & Turfgrass Management (the Wisconsin biomass data the model was fitted on)
  - Crespo et al. 2024, USDA-ARS, Field Crops Research (the limit on fall degree days)
  - Elmquist et al. 2026, UW–Madison Extension, Biomass Thresholds for Cereal Rye Cover Crop Goals (the levels)
  - Chudzik and Werle 2026, UW–Madison, Badger Crop Network (biomass for weed suppression)
---

## What it predicts

The model estimates the above-ground dry biomass of a cereal rye cover crop, in pounds per acre, in the spring after a fall planting, and rates it against the biomass that cover crop goals need:

- **Low:** below 2,000 lb/acre. Rye may take up some nitrogen that would otherwise leach.
- **Moderate:** from 2,000 lb/acre. Rye may also reduce soil erosion and phosphorus runoff.
- **High:** from 4,500 lb/acre, the upper end of UW–Madison's goal for weed suppression.

The model is for winter-sown cereal rye: planted in late summer or fall, growing through the winter and terminated in spring. It predicts spring biomass, not fall growth: the measurements it was fitted to were all taken at spring termination, from April 10 to June 17, so it says nothing reliable about how much rye there is in the fall. For that reason the estimate is blank from planting until March 1 and starts on March 1. Growing degree days since planting show from the planting date.

## How it works

Rye grows when it's warm enough, so the model follows growing degree days since planting, counted by the single-sine method from a base of 32 °F (0 °C). Biomass follows an S-shaped curve with degree days: slow growth in the fall and winter, then a rapid rise in spring that levels off toward 12,000 lb/acre.

Fall warmth helps rye only up to a point. In a 13-year Iowa study by Crespo and colleagues (2024), rye's final biomass stopped depending on fall warmth once the fall passed about 1,440 °F-days (800 °C-days). So the model counts degree days from planting through December 31 up to 1,440 °F-days, and all of them after that. On that count, the estimate reaches 2,000 lb/acre at about 1,820 °F-days (1,010 °C-days) and 4,500 lb/acre at about 2,280 °F-days (1,270 °C-days).

We fitted the curve to rye biomass that UW–Madison researchers and their partners clipped in Wisconsin fields and research plots, 138 sites and years in all from falls 2015 through 2024, using AgWeather's weather at each site (Colet and colleagues, 2026). The researchers' published model also uses fall rain, the planting date and latitude. Ours is modified from theirs: it uses degree days alone, because rain and the planting date didn't improve its predictions for fields left out of the fit. It also stays between zero and its ceiling and never falls from one day to the next, which matters when you follow it through a spring. The planting date still counts, through the degree days since planting.

The model runs in Wisconsin, Minnesota, Iowa, Illinois and Michigan. Without your planting date, it assumes October 1; enter your own at a location.

## How to read it

- UW–Madison's goals: 1,000 to 2,000 lb/acre to hold nitrogen, about 1,500 lb/acre to cut erosion and phosphorus runoff, and 3,500 to 4,500 lb/acre to suppress weeds. The model's Moderate level starts at 2,000 lb/acre, above the erosion goal, so a Low estimate near 2,000 may already meet it.
- Use the estimate to judge whether delaying termination might reach your goal: most of rye's biomass comes in spring. Weigh that against the next crop. Before corn, end rye early (Iowa State suggests at least 10 days before planting); before soybean, heavier rye fits better.
- Read the estimate as a range, not an exact number (see below). Near a level's boundary, the rye could be on either side of it.
- The only way to know your own rye's biomass is to clip, dry and weigh a measured area. Even heavy rye doesn't control weeds by itself, so keep a residual herbicide in the program.

The [cereal rye cover crop topic page](/topics/cereal-rye-cover-crop) explains the goals and termination in more detail.

## Validation and caveats

- Draft (model version 0.3, beta).
- **How far off it can be:** we refitted the model leaving out one location, one year or one data source at a time and compared it with the biomass measured there. A typical miss was about 1,200 lb/acre. Misses were smaller for light stands (about 600 lb/acre below 2,000) than for heavier ones (about 1,300 lb/acre from 2,000 to 4,500, and 2,000 or more above 4,500, where the model tends to estimate too low). About 7 in 10 of them landed in the right level.
- **Where it was fitted:** nearly all the data came from southern and central Wisconsin; only 7 of the 144 sites and years in the researchers' data were north of 44° N (about the latitude of Oshkosh), and none were outside Wisconsin. Elsewhere in Wisconsin and in neighbouring states, treat the estimate with more caution.
- **Planting dates:** the data's plantings ran from August 27 to November 10. For a planting before August 25 or after November 10, the model flags the estimate as outside its data.
- **Late spring:** the data's terminations ran from April 10 to June 17, so the model's season ends June 15; later days are flagged as outside it.
- In one group of research plots, measured biomass ran 3,400 to 4,000 lb/acre above the model's estimate and above other plots at the same site, likely because of how those plots were managed. Management the model doesn't know can move biomass a long way.
- Seeding rate, soil, nitrogen and the previous crop aren't inputs.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
- **What changed in version 0.3:** earlier versions used the Crop Risk Tool's equation, an unpublished fit that also used the planting date and fall rain. Fitted again on the researchers' data, those terms didn't improve its predictions, and the tool's equation had been given all fall precipitation where it was likely fitted on rain on days above freezing, which made its estimates too low.
