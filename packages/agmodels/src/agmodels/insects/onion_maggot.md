---
id: onion-maggot
status: draft
updated: 2026-11-21
summary: Times the three onion maggot fly flights and the feeding that follows from degree days since January 1, by NEWA's model, and marks when onion plantings should be protected during each flight.
sources:
  - NEWA's onion maggot model, Cornell University (the method and the three flights' timing)
  - Eckenrode, Vea and Stone 1975 (fly trap catches in New York onion fields, 1971–1974; NEWA's source; compared)
  - Liu, McEwen and Ritcey 1982 (development times by stage, Ontario; the timing of egg laying and larvae)
  - UW Vegetable Entomology's onion maggot page (three flights in Wisconsin and their degree days; management)
  - Salgado and Nault, Onion Maggot and Seedcorn Maggot, Cornell University, 2025 (management at planting)
  - Schuh, Hahn and Wold-Burkness, Cabbage and Onion Maggots, University of Minnesota Extension (row covers in gardens)
---

## What it predicts

Onion maggot flies lay eggs at the base of onion plants, and the maggots crawl down under the leaf sheaths into the bulb. Seedlings wilt and collapse, leaving thin stands, and bulbs damaged later in the season are unmarketable and can rot in storage. There are three flights of flies a year in Wisconsin. The model follows each:

- **Adult flight**: how many flies are emerging, compared with the spring flight's peak.
- **Larval feeding**: how many maggots are feeding, timed from the flies that laid their eggs.
- **Protect onion seedlings during fly flight**: the days from the first flies (about 5 % of a flight) until 95 % have emerged, for each flight.

Risk adds the two stages together, and a risk of 1 means as active as the spring flight at its peak.

## How it works

The model is NEWA's onion maggot model, from Cornell University. Degree days are counted from January 1 as the day's average temperature above 40 °F, with no upper limit.

- **The spring flight.** Flies from the overwintering pupae begin emerging at about 390 degree days, half have emerged by 735, and 95 % by about 1,100. These are NEWA's numbers, which rest on trap catches in New York onion fields (Eckenrode, Vea and Stone 1975, and later Cornell work).
- **Larvae.** Females lay eggs after about 185 degree days, and eggs hatch after about 90 more; the maggots then feed for about 520 degree days (laboratory times from Ontario, Liu, McEwen and Ritcey 1982).
- **The summer flights.** Each generation takes about 1,100 degree days from flight to flight, fitted to NEWA's peaks at 1,752 and 2,975. Each later flight is more drawn out than the one before, as in NEWA's table. The model stops at three flights.
- **The end of the season.** After early September, each day at or below 28 °F reduces activity, and four such days within two weeks end the season.

In an average year (AgWeather's degree days for 1996 to 2025), the first flies come about May 8 at Arlington, May 13 at Hancock and May 21 at Rhinelander, and the spring flight peaks about May 27, May 31 and June 8. The second flight peaks in early to mid-July, and the third in mid-August in the south and about September 1 at Rhinelander.

## How to read it

- **Protection comes at planting.** By the time damage shows, it's too late to control the maggots. Seed treatments, transplant tray drenches and in-furrow treatments at planting protect the crop; sprays against the adult flies are usually not successful, because the flies move between fields and avoid exposure.
- **The spring flight matters most.** NEWA calls the spring generation the most destructive, able to cut stands by more than half, and says the later generations rarely damage onions. The model rates every flight alike, so read the first window as the one to plan around.
- **Row covers** should go on before the first window opens and stay on until it closes, about three weeks past the spring peak. Don't use them where onions grew last year, since flies can emerge underneath.
- **Plant new onion fields well away from last year's,** and remove cull onions and volunteers, which carry maggots into the next season.
- **Keep a record of stand loss.** UW Vegetable Entomology treats damage of more than 5 to 10 % in last year's crop as the signal to use a preventive treatment at planting.

The [onion maggot topic page](/topics/onion-maggot) explains the insect and its management in more detail.

## Validation and caveats

- Draft (model version 0.2, beta). Developed from fly trap catches in onion fields in western and central New York.
- On the same weather at 34 Wisconsin NEWA stations in 2024 and 2025, the model's first flies and spring peak fall on NEWA's day, and its summer flights within 2 to 3 days of NEWA's.
- In New York fields the spring flight's midpoint averaged 712 degree days, near the model's 735, but varied from about 500 to 960 between sites and years, so flies can be active outside the model's windows. The New York broods came about 1,190 and 1,260 degree days apart, a little longer than the model's 1,100.
- **The summer flights may be early for Wisconsin.** UW's scouting calendar puts the third flight from late August through September and its peak at about 3,230 degree days; the model's third flight peaks about 300 degree days earlier, 10 to 14 days in an average year. The model hasn't been checked against Wisconsin trap catches.
- Every flight counts alike in the risk, though the spring flight does most of the damage.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your field.
