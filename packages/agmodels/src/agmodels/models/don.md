---
id: gibberella-ear-rot-don
status: draft
updated: 2026-11-19
summary: Gives the probability that corn grain will hold 1 ppm or more of DON (vomitoxin) at harvest, from the weather in the three weeks before silking, shown at silking (R1).
sources:
  - Paul and Nesi's DON model, Ohio State (the equation and its weather windows, unpublished; fitted on Ohio data)
  - Dalla Lana, Madden and Paul 2021, Phytopathology 111 (Ohio State's DON models; dry weather before silking went with more DON)
  - Hartschuh, Paul and Karhoff 2026, Ohio State C.O.R.N. Newsletter (fungicide timing at silking, and what a DON forecast says)
  - Crop Protection Network, Corn Grain and Silage Sampling and Mycotoxin Testing (testing grain)
  - The Crop Risk Tool's DON model (compared)
---

## What it predicts

Gibberella ear rot is a fungal disease of corn ears that can leave deoxynivalenol (DON, also called vomitoxin) in the grain. The fungus infects through the silks, so the weather around silking matters most. The model gives the probability, from 0 to 100 %, that grain will contain 1 ppm of DON or more at harvest, from the weather in the three weeks before silking. It doesn't say how much DON to expect.

## How it works

The equation was developed by Paul and Nesi at Ohio State University from Ohio data only, with daily weather from NASA's POWER data, which come on a grid about 30 miles (50 km) across. We haven't found it published. It reads two windows before silking:

- **The 14 days ending a week before silking:** the average daily high and low temperatures, the number of days with a mean temperature of 77 °F (25 °C) or more, and the number of days with any rain.
- **The 14 days ending at silking:** the average relative humidity and the number of days with a mean humidity of 80 % or more.

Warmer highs and lows raise the probability, but more days averaging 77 °F or more lower it. A higher average humidity raises it, but more very humid days lower it. More rainy days lower it too. Each extra rainy day in the earlier window, or very humid day in the later one, cuts the odds by more than half, so the model is very sensitive to these counts.

That moisture runs the opposite way to the usual advice, which says wet weather after silking favors DON. The signs are the authors' own, not a slip in copying, and they agree with Ohio State's published work, in which moisture in the weeks before silking went with less DON, and moisture after silking with more. This model reads only the weeks before.

A day with no rain data counts as a day without rain, and the model reports how many such days there were. Risk is Low from 1 %, Moderate from 20 % and High from 40 %; these are the Crop Risk Tool's levels, since the authors gave none. The model is worked out each day as if that day were silking, and the risk is shown at silking (R1), taken from the [corn stages model](/models/corn-stages) or your own planting date, between July 1 and August 7. If your field silks on a different day, read the value for that day.

## How to read it

- The model's value is ready at silking, when a fungicide decision is made. Fungicides lower DON somewhat if applied in early to mid R1, before the silks turn brown; they do little after that.
- A higher probability is a reason to scout before harvest: peel back the husks of at least 10 ears in several parts of each field, look for pink mold at the tips, and plan to harvest affected fields first.
- Whatever the model shows, test grain and silage before you feed or sell them. Looking at grain can't confirm mycotoxins.
- See the [Gibberella ear rot topic page](/topics/gibberella-ear-rot) for management and testing.

## Validation and caveats

- Draft (model version 0.2, beta). We ported the model from the Crop Risk Tool and checked it on the tool's own 2025 weather at Eau Claire, Wisconsin. It matched the tool's probability on 344 of 358 days; on the other 14, where we count a day at exactly 80 % humidity as humid, as the authors do and the tool doesn't, the difference was negligible. That shows we reproduce the tool, not that its predictions are right.
- On that weather, the probability stayed at or below 2.3 % from July 1 to August 7, 2025. The model hasn't been compared with DON in Wisconsin grain.
- It was fitted on Ohio data with coarse daily weather. We count a rainy day from any measurable rain on a much finer grid, which may find fewer rainy days than the coarse data did, and so give higher probabilities; we haven't measured this. Whether the authors' windows are 14 or 15 days, and whether the model carries over to Wisconsin, are questions for them.
- The silking date comes from a model unless you give your own planting date, and a day or two of error shifts both windows.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
