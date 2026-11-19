---
id: rye-biomass
status: draft
updated: 2026-11-19
summary: Estimates the spring biomass of a fall-planted cereal rye cover crop from growing degree days since planting, the planting date and fall rain, and compares it with the biomass each cover crop goal needs.
sources:
  - An unpublished fit to Wisconsin data, from the Crop Protection Network's Crop Risk Tool (the biomass equation)
  - Elmquist et al. 2026, UW–Madison Extension, Biomass Thresholds for Cereal Rye Cover Crop Goals (the levels)
  - Chudzik and Werle 2026, UW–Madison, Badger Crop Network (biomass for weed suppression)
---

## What it predicts

The model estimates the above-ground dry biomass of a cereal rye cover crop, in pounds per acre, from its fall planting through the following spring, and rates it against the biomass that cover crop goals need:

- **Low:** below 2,000 lb/acre. Rye may take up some nitrogen that would otherwise leach.
- **Moderate:** from 2,000 lb/acre. Rye may also reduce soil erosion and phosphorus runoff.
- **High:** from 4,500 lb/acre, the upper end of UW–Madison's goal for weed suppression.

## How it works

Rye grows when it's warm enough, so the model follows growing degree days since planting, counted by the single-sine method from a base of 32 °F (0 °C) with a cutoff at 95 °F (35 °C). Biomass follows an S-shaped curve with degree days: slow growth in the fall, then a rapid rise in spring before it levels off.

The height of the curve depends on two things known by the end of the year:

- **Planting date:** later planting gives less biomass in spring.
- **Fall rain:** the rain from planting through December 31; a wetter fall gives less biomass in spring. A very late planting after a very wet fall gives none.

The equation is an unpublished fit to Wisconsin data, carried over from the Crop Protection Network's Crop Risk Tool. The model runs from September through June in Wisconsin, Minnesota, Iowa, Illinois and Michigan. Without your planting date, it assumes October 1; enter your own at a location.

## How to read it

- UW–Madison's goals: 1,000 to 2,000 lb/acre to hold nitrogen, about 1,500 lb/acre to cut erosion and phosphorus runoff, and 3,500 to 4,500 lb/acre to suppress weeds. The model's Moderate level starts at 2,000 lb/acre, above the erosion goal, so a Low estimate near 2,000 may already meet it.
- Use the estimate to judge whether delaying termination might reach your goal: most of rye's biomass comes in spring. Weigh that against the next crop. Before corn, end rye early (Iowa State suggests at least 10 days before planting); before soybean, heavier rye fits better.
- The only way to know your own rye's biomass is to clip, dry and weigh a measured area. Even heavy rye doesn't control weeds by itself, so keep a residual herbicide in the program.

The [cereal rye cover crop topic page](/topics/cereal-rye-cover-crop) explains the goals and termination in more detail.

## Validation and caveats

- Draft (model version 0.2, beta).
- The model reproduces the Crop Risk Tool's biomass in all 1,736 combinations of planting date, fall rain and degree days tested, and over a fall at Eau Claire, Wisconsin. Version 0.2 differs from the tool in one case: where a very late planting follows a very wet fall, the tool's biomass rose again with more rain, and ours stays at zero.
- The fit is unpublished: we don't know its error or the planting dates, rain and degree days its data covered, and it hasn't been compared with biomass measured in fields. Treat its numbers as a rough guide.
- Seeding rate, soil, nitrogen and the date you plan to terminate aren't inputs.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
