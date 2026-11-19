---
id: alfalfa-growth
status: draft
updated: 2026-11-19
summary: Counts growing degree days (base 41 °F) since spring or your last cutting, and marks when alfalfa is in the 900 to 1,100 degree-day window for cutting.
sources:
  - UW–Madison's alfalfa cutting tool (the degree days and the 900–1,100 cutting window)
  - Newell, UW–Madison Extension, Managing fall alfalfa cutting for persistence (the fall rest period)
  - Gruss and Michel 2024, Iowa State University Extension (the fall rest period)
  - UW–Madison Extension, Seven Unique Factors of First-Cut Alfalfa (judging first-cut quality)
---

## What it predicts

The model follows alfalfa's regrowth by growing degree days and marks three stages:

- **Growing:** fewer than 900 degree days since spring or the last cutting.
- **Ready to cut:** 900 to 1,100 degree days, the window for cutting.
- **Past the cut window:** more than 1,100 degree days, when forage quality declines as the crop matures.

## How it works

Degree days are counted by the single-sine method, base 41 °F with a cutoff at 86 °F. In spring the count starts on January 1; after a cutting, enter its date and the count starts again from that day. The degree days and the cutting window are those of UW–Madison's alfalfa cutting tool, which this model replaces.

## How to read it

- Treat the window as a reminder to check fields, not as a cutting date. The calendar alone is a poor guide to first-cut quality: UW–Madison suggests judging fields by scissors-cut samples sent for analysis, by PEAQ (stem height and stage) or by degree days, and checking one method against another.
- Enter each cutting date so that the count starts again from it.
- **The fall rest period:** to go into winter with full root reserves, the last cutting should leave about 900 degree days (base 41 °F), roughly 5 to 6 weeks, before a killing freeze, or fewer than 360. The model doesn't yet apply this rule, so compare the degree days left in a typical fall at your location with it yourself.
- Alfalfa weevil larvae feed on the first crop; see the [alfalfa weevil model](/models/alfalfa-weevil) for its timing.

The [alfalfa topic page](/topics/alfalfa) explains cutting schedules and the fall rest period in more detail.

## Validation and caveats

- Draft (model version 0.1, beta).
- The model's daily degree days are the old tool's formula, and its window is the tool's 900 to 1,100. This shows that it reproduces the tool, not that the window is right for every field.
- The 900 to 1,100 window is a rule of thumb from the old UW–Madison tool. We haven't found a published source for it, and it hasn't been compared with forage quality or stage measured in Wisconsin fields. UW–Madison Extension's article on fall cutting gives only the fall rule.
- Counting from January 1 includes warm winter days before the crop greens up.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
