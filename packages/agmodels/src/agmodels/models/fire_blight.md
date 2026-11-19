---
id: fire-blight
status: draft
updated: 2026-11-18
sources:
  - Smith and Pusey 2011 (Cougarblight 2010)
  - WSU's Cougarblight tables and Decision Aid System (the hourly values in °F, the risk thresholds)
  - Steiner 1990 (MaryBlyt)
  - Turechek and Biggs 2015; Biggs and Turechek 2018 (MaryBlyt 7.1 and its manual)
  - Jones 1992 (MaryBlyt in Michigan orchards)
  - NEWA's fire blight model (bloom dates, risk thresholds; compared)
  - Leaf wetness sensors at NEWA's Wisconsin orchard stations, 2024–2026 (the wetness estimate)
  - Enviroweather's fire blight model (compared)
---

## What it predicts

Fire blight bacteria infect apple blossoms, and warm weather during bloom lets them build up quickly. Growers time blossom protection by that risk. During bloom, the model runs the two methods NEWA uses:

- **Cougarblight risk**: Low, High or Extreme, from the warmth of the last four days and the fire blight history near your orchard, which you choose: none in the neighborhood last year, in the neighborhood last year (the default) or active in the neighborhood now. This risk sets the map's colors.
- **Infection possible**: days when the blossoms were wet while Cougarblight's risk was High or Extreme.
- **Blossoms wet**: days with rain, or with two or more hours of estimated wetness such as dew.
- **MaryBlyt's infection potential (EIP)**: an index of how much warmth the open blossoms have had for bacteria to multiply on them, which reaches 100 when there has been enough.
- **MaryBlyt's risk**: Low, Moderate, High or Infection. An Infection day is one on which all four of its conditions (below) are met.
- **Expected symptoms**: the degree days since MaryBlyt's latest infection day, with blossom blight symptoms expected from 103.
- **Bloom**: whether the blossoms are before, in or past bloom.

## How it works

- **Bloom.** The model starts at first blossom, 230 degree days (base 43 °F) from January 1, and ends at petal fall, 578 degree days or June 15, whichever comes first. These are NEWA's fire blight model's defaults. The start comes before the apple stages model's bloom (346 degree days) and a few days before full pink in Steiner's Maryland orchards; the days before the blossoms open add little, since cool days cut MaryBlyt's total. If you enter the date your orchard's first blossoms opened, petal fall comes 348 degree days later or on June 15.
- **Cougarblight** (Smith and Pusey 2011). Each hour scores a value by its temperature, from 0.05 at 51 °F through 4 at 70 °F and 30 at 80 °F to 52 at 88–89 °F, falling to 0 from 96 °F. The day's values are summed, and the risk is the total for today and the three days before, about a blossom's susceptible life. With blight in the neighborhood last year, risk is High from 150 and Extreme from 350; with none, High from 300 and Extreme from 800; with blight active now, High from 80 and Extreme from 200.
- **Wetting.** The 2010 version of Cougarblight requires two hours of wetting for infection. We have no leaf wetness sensors, so blossoms count as wet on a day with 0.01 inch of rain or more, or with two or more hours when the relative humidity is 90 % or more or rain falls. We chose this estimate by comparing several with the leaf wetness sensors at NEWA's Wisconsin orchard stations, and the apple scab model uses it too.
- **MaryBlyt** (Steiner 1990; version 7.1, Turechek and Biggs 2015). The model adds up degree hours above 65 °F, hour by hour, over the open blossoms' life: a day's warmth stops counting once 80 degree days above 40 °F have passed since. While the total is under 400 degree hours, a day with a high under 65 °F cuts it by a third, a second in a row by half of what's left and a third in a row to nothing, and a low at or below 32 °F clears it. A low at or below 24 °F starts the blossoms' life over. EIP is 100 at 198 degree hours above 65 °F (110 above 18.3 °C).
- **MaryBlyt's four conditions** are open blossoms; EIP of 100 or more; wetting, which is rain of 0.01 inch that day, 0.10 inch the day before, or dew; and a mean temperature above 60 °F. Risk is Low with the blossoms alone, Moderate with one more condition, High with two and Infection with all four. Symptoms are expected 103 degree days above 55 °F (with a 90 °F upper limit) after an infection day.

This follows NEWA's fire blight model, the Cornell system many Wisconsin growers use, with these differences. Cougarblight counts hours from 51 °F, as its 2010 version does; NEWA counts none below 60 °F, as the model did before 2010. This puts our four-day totals a few points above NEWA's, which changes the risk level only on days near a threshold. We use NEWA's thresholds; the published model and WSU's version start High at 500 and 400 when there's no blight nearby. NEWA shows neither wetting nor "infection possible", and its MaryBlyt wetting comes from each station's leaf wetness sensor or dew point. For MaryBlyt we follow version 7.1's rules where NEWA's differ slightly, including symptoms after 103 degree days, where NEWA uses 90.

## How to read it

- Set the fire blight history to match your orchard and its neighbors. The thresholds drop as blight comes closer.
- Blossoms wet while risk is High or Extreme is the condition under which infection is possible; follow your fruit pest management guide for products and timing.
- After a MaryBlyt infection day, watch for blossom blight as the degree days approach 103.
- An EIP under 100 doesn't mean no bacteria are present: in Michigan, bacteria were found on blossoms at EIP values from 12 to 59 (Jones 1992).
- Enter the date your first blossoms opened at your location. The model then times bloom from your orchard instead of the degree-day estimate.
- The model ends at petal fall, but late and straggling blossoms stay at risk after it, as Jones found in Michigan.
- Blossoms wet is shown so you can judge a fog or dew morning yourself. A severe Michigan epidemic in 1991 came on days above 80 °F with morning fog and no rain, which an estimate from the weather can miss.
- The model doesn't cover blight after hail or storms (trauma blight), canker or shoot blight, or the effect of sprays.

## Validation and caveats

- Draft (model version 0.1, beta). Cougarblight's thresholds come from outbreaks studied mostly in the Pacific Northwest and MaryBlyt's from Maryland and West Virginia. Neither has been tested against fire blight infections in Wisconsin orchards. The nearest field test is of an early version of MaryBlyt in 11 Michigan orchard-years (Jones 1992), which predicted when symptoms would appear better than when infections occurred.
- Our MaryBlyt reproduces the published program's worked examples, and on the weather of Wisconsin orchard stations our Cougarblight risk matched NEWA's on 95 % of bloom days.
- On the map's weather, Cougarblight's totals at some places run well above those at nearby orchard stations on warm days, likely because the map's spring afternoon temperatures differ from the orchards' sensors; we haven't yet checked this hour by hour. Until we have, the map can show a risk level one higher than a nearby station.
- Wetting is estimated, not measured, and agrees with orchard leaf wetness sensors less well for fire blight's wetting than for apple scab's infection periods.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your orchard.
