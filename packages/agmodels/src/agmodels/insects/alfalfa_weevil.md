---
id: alfalfa-weevil
status: draft
updated: 2026-11-21
summary: Times alfalfa weevil egg hatch, larval feeding, pupation and new adults from degree days since January 1 (base 48 °F), on NEWA's model, and marks when to scout stem tips for feeding on the first crop.
sources:
  - NEWA's alfalfa weevil model, Cornell University (the method and the degree days for each stage)
  - Harcourt 1981 (the stage peaks NEWA's table carries and the stage durations, southern Ontario)
  - Litsinger and Apple 1973 (larval development in Wisconsin; compared)
  - Bick, Managing Alfalfa Weevil in Wisconsin Alfalfa Fields, UW–Madison Extension, 2025; Jensen, Alfalfa Weevil, Wisconsin Crop Manager, 2018; and Pest Management in Wisconsin Field Crops (A3646), 2025 (scouting, thresholds and the period of heaviest feeding)
  - Hanson and Potter, University of Minnesota Extension, 2023 (the later-developing western strain)
---

## What it predicts

Alfalfa weevil larvae feed on the stem tips and leaves of the first alfalfa crop in spring, cutting yield and forage quality. There is one generation a year. The model follows the weevil through the season from degree days:

- **Egg hatch**: how many eggs are hatching, compared with the peak of hatch.
- **Larval feeding**: how many larvae are feeding, compared with the season's peak. This is the risk to the crop.
- **Pupae in cocoons** and **new adults**: when feeding is over and the summer adults appear.
- **Scout stem tips for larval feeding**: the days from when half the eggs have hatched until the last have hatched, when tip feeding shows and decisions about spraying or early cutting are made.

## How it works

Degree days are counted from January 1 by the simple average method: the day's average temperature above 48 °F, with no upper limit. This is the method of NEWA's alfalfa weevil model (the Network for Environment and Weather Applications at Cornell University), which this model follows. NEWA's degree days for each stage are those of D. G. Harcourt's 1981 model from southern Ontario, converted to degrees Fahrenheit.

- **Egg hatch.** Half the eggs have hatched by about 280 degree days. Weevils lay eggs over several weeks in spring, so hatch is spread out: about 10 % of the eggs have hatched by 140 degree days and 90 % by 420.
- **Larval feeding.** Each larva feeds for about 320 degree days through its four stages before it spins a cocoon, NEWA's span from hatch to cocooning. Harcourt's development times add up to about 340, and larvae measured in Wisconsin by Litsinger and Apple in 1973 took about 300. The most larvae are feeding at about 440 degree days, and half of them have finished at about 600.
- **Pupae and new adults.** About 215 degree days after spinning its cocoon, a weevil emerges as an adult: half the adults are out by about 815 degree days. New adults feed for a short time, then leave the field for the summer. We found no study giving when they leave; the model has them gone by about 1,000.
- **Scouting window.** The window opens when half the eggs have hatched, about 280 degree days, and closes when the last have hatched, about 530. NEWA's own guide says to scout from 315 to 599.

On the 1996–2025 normals, half the eggs have hatched by about May 22 at Arlington, May 26 at Hancock and June 2 at Rhinelander, and larval feeding peaks about June 2, June 6 and June 14. These are long-term averages, and a given year can differ: at the NEWA station in Verona, near Madison, half the eggs had hatched by about May 12 in 2024 and May 15 in 2025.

## How to read it

- **Start checking fields as the window opens**, or earlier on warm, south-facing slopes and sandy knolls, where feeding usually shows first.
- **How to scout:** pick 50 stems at random across the field and count those with tip feeding. A sweep net shows whether larvae are present, but don't base a decision on sweep counts.
- **First crop:** treat when 40 % of stems show feeding and the field is more than a week from harvest. If it is within 7 to 10 days of harvest, cut it early instead.
- **Keep checking while larvae are feeding**, through the end of the window and after it if larvae are still present.
- **After cutting:** check the stubble 4 to 5 days after harvest. Treat if larvae are still active and 50 % of stems show feeding, or if larvae or adults are present and there is no regrowth 3 to 4 days after harvest.

The [alfalfa weevil topic page](/topics/alfalfa-weevil) explains the insect, its scouting and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). The degree days for each stage come from field counts near the Bay of Quinte in eastern Ontario, 1973–1980. They haven't been compared with weevil counts or tip feeding in Wisconsin fields.
- On historical weather for Harcourt's study area, NEWA's method reached the 36 peak dates he observed in 1977–1980 a median 3 days late. Harcourt's own method, the single-sine method counted from April 1, was a median 2 days late on the same weather.
- On the weather of Wisconsin's NEWA stations in 2024 and 2025, the model's egg hatch, cocooning and adult emergence fall on NEWA's days. On AgWeather's weather at the same places, they usually come within 3 days of NEWA's.
- **Timing differs from some UW–Madison advice.** UW–Madison puts the start of egg hatch and tip feeding at about 300 degree days and the heaviest feeding at about 600 to 800 degree days (base 48 °F). In this model larval feeding peaks earlier, at about 440, and half the larvae have stopped feeding by 600. Other guides count degree days in other ways, so the same number can mean a different date.
- **How spread out hatch is** comes from our choice, not from a study: Harcourt's data suggest an even wider spread, and the true spread varies with when eggs are laid. Some eggs are laid the autumn before, and the model doesn't treat them separately.
- Litsinger and Apple found that eggs develop above 50 °F, not 48 °F; like NEWA, the model uses one base for every stage.
- Minnesota reports a western strain of the weevil that develops 1 to 2 weeks later than the eastern strain on which degree-day models are based.
- You can't enter an observed stage to reset the later ones.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
