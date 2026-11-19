---
id: wheat-scab
status: draft
updated: 2026-11-19
summary: Gives the probability of a severe Fusarium head blight (scab) epidemic for wheat flowering on the day shown, from the average humidity of the 14 days before, for your variety's resistance class.
sources:
  - Shah, Molineros, Paul, Willyerd, Madden and De Wolf 2013, Phytopathology 103 (the model's form; a severe epidemic as 10 % severity or more)
  - Shah, De Wolf, Paul and Madden 2021, PLOS Computational Biology 17 (the model, numbered M6 among the U.S. scab models)
  - The U.S. Fusarium head blight prediction model team, Wheat Scab Models Deployment 2026 (model M6's 2026 coefficients and the risk levels; unpublished)
  - Friskop et al. 2021, Crop Protection Network, An Overview of Fusarium Head Blight (fungicide timing)
  - Smith 2022, Wisconsin Crop Manager (fungicide timing in Wisconsin research)
  - Bauer, Fanning, Enz and Eberlein 1984, NDSU Extension EB-37, as NDAWN runs it (spring wheat's stages, through the spring wheat stages model)
  - The Crop Risk Tool's wheat scab model (compared)
---

## What it predicts

Fusarium head blight, or scab, infects wheat heads mainly at flowering, in warm, humid weather. The model gives the probability, from 0 to 100 %, of a severe scab epidemic for wheat that flowers on the day shown. A severe epidemic is one where, averaged over the heads, 10 % or more of the head's surface shows symptoms. It gives a probability for each of four classes of variety resistance: very susceptible, susceptible, moderately susceptible and moderately resistant. It doesn't predict DON (vomitoxin) in the grain.

## How it works

The model is one of the U.S. Fusarium head blight prediction models developed by Shah, Paul, De Wolf and Madden: the one based on the average relative humidity of the 14 days before flowering (Shah and colleagues 2013; numbered M6 in their 2021 paper). For 2026 the model team gave it new coefficients, which aren't published. We use that equation, as the Crop Risk Tool does; we copied it from the tool and checked it against the team's 2026 document.

- **The weather it reads:** the average of the daily mean relative humidity over the 14 days before the day shown, not counting the day itself. If more than 2 of those 14 days have no data, the model gives no value for that day.
- **Resistance:** the more resistant the variety, the lower the probability for the same weather. Choose the class that matches your variety's rating; susceptible is the default.
- **Risk levels:** Low below 24 %, Moderate from 24 % and High from 32 %, the levels the model team set for the national risk tool.

The resistance class often sets the level more than the weather does. A susceptible variety turns Moderate when the two-week average humidity reaches about 65 % and High at about 72 % (70 % gives it about 30 %, 80 % about 41 %). A very susceptible variety is High from about 56 %, a moderately resistant one only from about 92 %.

Values are shown from May 1 to July 31, which covers wheat's flowering in Wisconsin.

- **The map:** each day's map shows the risk for wheat that flowers on that day, for winter and spring wheat alike, as the national risk tool's map does. It doesn't know which fields are flowering.
- **At your location, with a flowering date:** if you enter the date your wheat began flowering (Feekes 10.5.1), we mark that day through 7 days after as the period that matters, the window for a fungicide spray. This works for winter and spring wheat.
- **At your location, for spring wheat:** if you enter a spring wheat planting date instead, the [spring wheat stages model](/models/spring-wheat-stages) estimates when your wheat heads and flowers from growing degree days, and we mark the days from the start of heading (Haun 10.2) through the end of flowering (Haun 11.6). A flowering date you enter replaces this estimate.
- Outside that period the values are still shown, greyed, and for 3 days on either side of it they are shown lighter, since the dates may be a few days off. We don't assume a typical planting date, because we can't tell winter wheat from spring wheat.

## How to read it

- Read the value for the days around each field's flowering; other days' values describe fields flowering on other dates. Enter your flowering date (or, for spring wheat, your planting date) to have those days marked.
- A Moderate or High value at flowering is a reason to consider a fungicide. Spray the heads from the start of flowering (Feekes 10.5.1) to about 7 days after; in Wisconsin research, spraying about 5 days after flowering began cut DON the most.
- Compare the result with the national Fusarium head blight risk tool, which also asks for your wheat's flowering date and shows forecasts for the days ahead.
- Whatever the model shows, have grain from fields with scab tested for DON before you feed or sell it. See the [wheat scab topic page](/topics/wheat-scab) for management.

## Validation and caveats

- Draft (model version 0.3, beta). The equation and risk levels match the model team's 2026 document term for term. Given the Crop Risk Tool's 2025 weather at Eau Claire, Wisconsin, our probability matched the tool's for all four resistance classes on every day from mid-January, a day later because our 14 days end the day before. That shows we reproduce the tool, not that its predictions are right.
- **Flowering dates.** The map can't know when your field flowers. At a location, winter wheat needs the flowering date you enter, because we have no model of winter wheat's stages yet. Spring wheat's estimated dates haven't been compared with observed heading and flowering dates, so check your field and enter the date it began flowering when you know it.
- **High values in ordinary weather.** On 2025's weather at Eau Claire, from mid-May to July, a very susceptible variety was High every day, a susceptible one Moderate or High on most days and a moderately resistant one Low every day. The 2013 paper's dividing line for its version of this model was 31 %; where the 24 % and 32 % levels come from is a question for the model team.
- **Unpublished coefficients.** The 2026 coefficients aren't published. Other questions for the model team: whether the window is 14 or 15 days (some extension articles say 15), and whether a day runs from midnight to midnight, as ours do, or from 8 a.m. to 8 a.m., as in the 2013 paper.
- The model was developed on data from wheat fields in many U.S. states (15 in the 2013 paper), not fitted to Wisconsin, and hasn't been compared with scab in Wisconsin fields or with the national risk tool on the same days and places.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field; the Crop Risk Tool's cells are about 6 miles (9 km) across, and the two haven't been compared on the same places and days.
