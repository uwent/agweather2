---
id: spotted-wing-drosophila
status: draft
updated: 2026-11-25
summary: Estimates how active spotted wing drosophila adults are through the season from degree days, using a curve fitted to weekly trap catches in Wisconsin tart cherry orchards.
sources:
  - Kamiyama, Bradford, Groves and Guédot 2020, PLOS ONE 15:e0227726 (trap counts from Door County tart cherry orchards, 2015–2018), refitted 2026
  - Tochen et al. 2014, Environmental Entomology 43:501–510 (development thresholds)
  - VDIFN's spotted wing drosophila model (compared)
---

## What it predicts

Spotted wing drosophila is an invasive fruit fly that lays its eggs in ripening soft fruit. The model estimates how many adult flies a typical Wisconsin season has at each point, as a share of the season's peak. It describes the fly population, not the risk to a particular crop: fruit is at risk only once it begins to ripen.

## How it works

Degree days are counted from January 1 by the single-sine method, base 45 °F (7.2 °C, the lowest temperature at which the fly develops) with a cutoff at 86 °F (30 °C). The curve comes from weekly catches in 13 traps in four Door County tart cherry orchards from 2015 to 2018, studied by UW–Madison (Kamiyama et al. 2020). We fitted a smooth curve of the catches by degree days on AgWeather's weather, allowing for differences between years, orchards and traps.

- Traps catch the first few flies at about 800 to 1,100 degree days (late June to mid-July in Door County), and activity reaches Low at about 1,130.
- Numbers climb through July and August. Activity is Moderate from about 1,790 degree days, High from 2,090 and near its peak from 2,250 to 2,420, peaking at about 2,330: in Door County, usually the last days of August, and in southern Wisconsin around August 10.
- After the peak, activity falls slowly. The traps were checked into late October in only one year, so the model holds activity at about a third of the peak after 3,050 degree days, until hard fall freezes end the season, or October 31 at the latest. Where the season runs longer than in Door County, as in southern Wisconsin, the decline after the peak is less certain: a model fitted to seven years of catches in Michigan blueberries puts the peak in late September or early October.

## How to read it

- Activity levels compare the day's value with the season's peak. Very high means fly numbers are near their usual peak.
- Seasons differ: in single years, numbers peaked between about 2,290 and 2,370 degree days, but how many flies were caught at the peak varied about fivefold from year to year.
- Don't wait for the model to show activity before you start monitoring. Hang traps when green fruit appears and act on what they catch: in the study, single traps first caught flies at very different times, from early June to late July.

## Validation and caveats

- Draft (model version 0.2, beta). The curve describes the trap catches it was fitted to: tart cherry orchards in one county, sprayed four to five times a season. It hasn't been tested on other years, other crops or other parts of Wisconsin.
- Version 0.1 of this model, carried over from VDIFN, used the study's published numbers (1,276, 3,180 and 4,000 degree days). The study computed its degree days with a lower base temperature than its methods state, so those numbers run about one and a half times AgWeather's. Its peak at 3,180 is about 2,340 of AgWeather's degree days, where the refitted curve peaks too.
- Weather data come from a grid of cells about 1.5 miles (2.5 km) across, not from a station in your planting.
