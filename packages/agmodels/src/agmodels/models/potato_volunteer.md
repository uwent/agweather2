---
id: potato-volunteer
status: draft
updated: 2026-11-19
summary: Estimates whether potato tubers left in a field are likely to survive the winter, from the hours the soil spent below 27 °F at 2, 4 and 8 inches from November 1 through March 31.
sources:
  - Kirk and Wharton, Michigan State University Extension (the 27 °F and 120-hour rule at 2 and 4 inches, November through March)
  - The Wisconsin potato volunteer tool (the 8-inch depth and the four levels; compared)
  - UW Vegetable Pathology, Deep frost this winter limits risk of potato volunteers, 2025 (snow and Wisconet's station sites)
  - UW Vegetable Pathology, Vegetable Crop Update, April 19, 2026 (earlier late blight management after a field with late blight)
  - Cohen and colleagues, Michigan State University, in Potato Grower, 2024 (tubers deeper than about 4 inches)
  - Wisconet's soil temperature sensors, 2025–2026 (compared)
---

## What it predicts

Tubers left in a field after harvest can survive the winter and come up the next season as volunteers. Volunteers aren't protected by the fungicides a potato crop gets, so they can start a late blight outbreak, and they can carry potato virus Y and Colorado potato beetles into the next crop. Tubers die when the soil around them freezes hard enough for long enough. The model shows:

- **The chance tubers survived the winter**: Low, Moderate, High or Very high.
- **Hours below 27 °F** at 2, 4 and 8 inches deep since November 1.

## How it works

- **The rule** comes from Michigan State University (Kirk and Wharton): count the hours with soil below 27 °F at 2 and 4 inches from November 1 through March 31. Enough hours at a depth kill the tubers there.
- **Three depths.** The Wisconsin potato volunteer tool, which this model replaces, added 8 inches. Each depth with at least 120 hours below 27 °F lowers the risk one level: **Very high** with none, **High** with one, **Moderate** with two and **Low** with all three.
- **Soil temperatures** come from a weather model, not from sensors. The 2- and 4-inch depths are its soil layers at 4 and 10 cm, and 8 inches lies between its layers at 10 and 30 cm. The newest days use a forecast model's soil until the regular data arrive.
- **A seasonal map.** The count runs from November 1 through March 31. A winter's map appears on January 1, and after March 31 it keeps the winter's final count until the next winter's map appears.

## How to read it

- **Low** means the soil froze hard enough at every depth that tubers are unlikely to have survived. **Very high** means none of the depths reached 120 hours, so most tubers left in the field could still be alive.
- Snow insulates the soil: a cold winter with deep snow can leave tubers alive, while an open winter lets frost go deep. Shallow tubers freeze first, and a tuber deeper than about 4 inches is unlikely to get cold enough to die.
- Whatever the model shows, scout fields that grew potatoes last year, and their edges, as volunteers come up. Where risk is high, plan control in the following crop. Where volunteers may come from a field that had late blight the year before, earlier late blight management may be needed. See the [potato volunteers topic page](/topics/potato-volunteers) for control methods.

## Validation and caveats

- Draft (model version 0.2, beta). The rule follows the Wisconsin tool's, checked in tests. It hasn't been run against the tool's own results at Wisconet's stations.
- We compared the hours below 27 °F with Wisconet's soil sensors at 80 stations, November through March, from January 2025 to March 2026. Our soil data count more cold hours than the stations: about 40 % more at 2 inches, 60 % more at 4 inches and twice as many at 8 inches. More cold hours bring a depth to 120 sooner, so our risk may run lower than the stations' would. Wisconet's stations sit in grassy areas where snow insulates the soil, and a field the wind has swept bare can be colder, so neither is exactly your field.
- The 120-hour rule and its depths come from Michigan, and they haven't been checked against tuber survival in Wisconsin fields.
- Michigan State's rule calls for more than 120 hours; the model, like the Wisconsin tool, counts a depth at 120 or more. The difference matters only at exactly 120 hours.
- The count stops on March 31, as Michigan State's rule does. The Wisconsin tool counted from October 1 and kept counting into April, so in a cold April its results could be lower than ours. October soil in Wisconsin doesn't fall below 27 °F, so the earlier start made no difference.
- A day missing any hour of soil temperature adds nothing to the count, which leans the risk high where data are short.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, and the soil temperatures are the cell's average, under the cell's average snow, not those of a particular field.
