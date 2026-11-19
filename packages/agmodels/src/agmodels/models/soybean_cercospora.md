---
id: soybean-cercospora
status: draft
updated: 2026-11-19
summary: Gives the probability that spores of each of three Cercospora species that cause Cercospora leaf blight are present, from recent temperature, humidity and wind, and shows the highest of their three risk levels, provisionally from beginning pod (R3) to full seed (R6).
sources:
  - Webster's 2026 soybean Cercospora leaf blight algorithms for the Crop Risk Tool (the equations, their accuracy and risk levels, unpublished)
  - Crop Protection Network, An Overview of Cercospora Leaf Blight (Price et al. 2025) (symptoms, scouting and fungicide timing)
  - The Crop Risk Tool's soybean Cercospora model (compared)
---

## What it predicts

Cercospora leaf blight of soybean, and purple seed stain, are caused by several closely related _Cercospora_ species. The model gives the probability, from 0 to 100 %, that spores of each of three species are present, from the past few days' to two weeks' weather: _C. flagellaris_, _C._ cf. _sigesbeckiae_ and _C. kikuchii_. The risk shown is the highest of the three species' levels. Spores being present doesn't mean the crop will be damaged.

## How it works

The equations are Richard Webster's (North Dakota State University), written out in his 2026 algorithms for the Crop Protection Network's Crop Risk Tool. The fits haven't been published. For each species his document gives four candidate equations; the algorithm uses the first, and so do we.

- **_C. flagellaris_:** the 5-day averages of the daily low temperature and of the dew point depression (the gap between the temperature and the dew point). Warmer nights and drier air raise the probability. Risk is Moderate from 10 % and High from 15 %.
- **_C._ cf. _sigesbeckiae_:** the 14-day average of the day's highest wind speed and the 10-day average of the hours each day with relative humidity of 90 % or more. Calmer, more humid weather raises the probability. Risk is Moderate from 5 % and High from 10 %.
- **_C. kikuchii_:** the 14-day average of the hours at 90 % humidity or more and the 5-day average of the day's largest dew point depression. More humid hours, together with drier afternoons, raise the probability. Risk is Moderate from 5 % and High from 10 %.

For all three, Low starts at 1 %. The thresholds are the author's. In the author's own figures for these equations, each sorted about 78 to 84 % of samples correctly at its High threshold, but the _C. kikuchii_ equation flagged only about 3 in 10 of the samples where its spores were found.

The author gave no crop stages for the risk. We show it from beginning pod (R3) to full seed (R6), as our own provisional choice, since symptoms usually appear from beginning seed (R5) on; the stages come from the [soybean stages model](/models/soybean-stages) or your own dates.

## How to read it

- A higher probability means the recent weather has been more like the weather when that species' spores were found. Read it as a sign of when to look, not as a reason to spray.
- Scout the upper canopy from beginning pod through seed fill, and watch for purple and bronze leaves in full sun. Rule out sunburn, chloride toxicity and frogeye leaf spot before deciding on a fungicide.
- Strobilurin (QoI, FRAC group 11) fungicides are likely no longer effective against Cercospora leaf blight. Some mixtures of an SDHI (group 7) and a DMI (group 3), applied from beginning pod (R3) to beginning seed (R5), remain effective.
- See the [Cercospora leaf blight topic page](/topics/soybean-cercospora-leaf-blight) for identification and management.

## Validation and caveats

- Draft (model version 0.1, beta). We ported the model from the Crop Risk Tool, and on the tool's own 2025 weather at Eau Claire, Wisconsin, each species' probability matched the tool's on all 365 days. That shows we reproduce the tool, not that its predictions are right. The model hasn't been compared with Cercospora leaf blight or spore catches in fields.
- **Wind's unit is in doubt.** The author's document gives the _C._ cf. _sigesbeckiae_ equation's wind in meters per second, but the Crop Risk Tool passes it kilometers per hour, and so do we. The arithmetic favors kilometers per hour: read in meters per second, the summer winds at Eau Claire in 2025 would have put this species at 82 to 92 %, High on every day, which doesn't fit an equation whose High threshold is 10 %. Read in kilometers per hour, they gave 3 to 26 %, around its thresholds, as they should. For example, with a 14-day average highest wind of 11 mph (5 m/s) and 6 humid hours a day, it gives 6 % in kilometers per hour and 86 % in meters per second. We'll keep kilometers per hour until the author confirms.
- We don't know where, in which years or on what weather the equations were fitted, or whether "spores present" was measured in traps or on leaves. The crop stages are our own choice.
- Humid hours are counted from gridded humidity, which reads slightly low near saturation, so an hour counts at 88 % rather than 90 %; how that changes this model hasn't been measured.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
