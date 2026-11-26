---
id: about
title: About AgWeather
summary: AgWeather gives growers, consultants and researchers in the Midwest free weather data and crop, disease and insect models, from the University of Wisconsin–Madison.
status: draft
updated: 2026-11-25
---

AgWeather is a free weather service for agriculture from the University of Wisconsin–Madison. It keeps hourly weather for every 2.5 km (1.6 mile) square across the Midwest and Kentucky, and runs models of crop growth, plant diseases and insect pests on that weather. You can see the results on maps, follow your own fields as saved sites, and download the data or use it through our public API.

## Who it is for

We build AgWeather for growers, crop consultants, extension educators, agency staff and researchers. Most of its models were developed for vegetable, field and fruit crops in Wisconsin and nearby states, and each model's page says where it was developed and tested. AgWeather's results are guidance based on weather data, not a guarantee: check them against what you see in your fields and with your local extension office.

## Who runs it

AgWeather is a service of the University of Wisconsin–Madison's College of Agricultural and Life Sciences (CALS) and UW–Madison Extension. It is developed and maintained in the Department of Entomology, with the Department of Plant Pathology.

> **For Ben:** confirm how AgWeather relates to UW–Madison Extension (a program, a partner, or a host) and whether to name a program or unit within it. Add any funding acknowledgment here; none is listed yet.

## Credits

- **Coding and development:** Allen Ballman, Ken Frost and Ben Bradford.
- **Academic leadership:** Russ Groves (Vegetable Entomology, UW–Madison) and Amanda Gevens (Vegetable Pathology, UW–Madison).

> **For Ben:** add titles and links for each person if you want them, and any others to thank (hosting, IT, reviewers of the models).

## History

AgWeather began in the mid-1980s in UW–Madison's Department of Soil Science, where Bill Bland, now emeritus professor, and Rick Wayne, software developer, built weather grids and tools to help Wisconsin growers raise yields, keep costs down and care for the land. John Panuska, Extension specialist in Biological Systems Engineering, coordinated the service for a time, until he retired in 2021. The Department of Entomology took over its care, along with the Vegetable Disease and Insect Forecasting Network (VDIFN) and the Wisconsin Irrigation Scheduling Program (WISP).

> **For Ben:** check this history and add dates (when the Department of Entomology took over, when VDIFN began).

## What this version replaced

This version of AgWeather brings several older tools together in one place:

- The earlier AgWeather website and its weather data service, which kept daily weather grids for the Upper Midwest.
- The Vegetable Disease and Insect Forecasting Network (VDIFN), with its disease severity and insect degree-day maps.
- The Crop Risk Tool, which ran field and vegetable crop disease models for your own sites.
- The alfalfa growth and cutting tool and the potato volunteer survival model.

AgWeather now keeps the weather hour by hour rather than as daily summaries, which lets every model run from the same weather on the same grid. Links to the old pages lead to their new places. The [changelog](/changelog) lists what has changed since launch.

## Where the data come from

The hourly weather comes from NOAA's weather analyses (URMA and RTMA), which combine weather station readings with radar and a short-range forecast, on NOAA's 2.5 km grid. Solar radiation comes from NOAA's HRRR weather model, soil temperature and moisture from ECMWF's ERA5-Land, and the forecast from NOAA's National Blend of Models. For locations outside the area our maps cover, we read the weather from Open-Meteo. Where a source reads consistently high or low against measurements, we correct it.

The [methods page](/methods) describes each source, our corrections and how we handle missing data, and the [status page](/status) shows how current each source is. You can download the data from the [data page](/data) or use the [API](/api/v2/docs).

## Privacy

- **Your sites stay in your browser.** The sites you save are kept in your browser's storage on your own device, not on our server. To see a site's weather, your browser asks our server for that location's data, as any web page asks for what it shows.
- **We don't use analytics or advertising.** AgWeather doesn't track visitors and has no advertising.
- **Outside services.** A place search sends what you type to OpenStreetMap's Nominatim service to find the place. The map's background and its optional layers, such as radar, load from the outside services named in the map's credits.
- **Server logs.** Like any website, our server keeps a record of the requests it receives, including the address they came from, to keep the service running and secure.
- **Accounts.** AgWeather has no accounts yet. When we add them for email alerts, an account will keep your email address and the sites and alerts you choose to save to it, and we will update this page first.

> **For Ben:** confirm how long the server's logs are kept, and what the API use form's replies are kept for, so this section can say so.

## How to cite AgWeather

If you use AgWeather's data or models in a report or paper, please cite it as:

AgWeather. University of Wisconsin–Madison. https://agweather.cals.wisc.edu (accessed on the date you used it).

Name the models you used too: each model's page lists the research it is based on, and the API returns the same citations with its results.

> **For Ben:** add a DOI or a paper to cite here if AgWeather gets one.

## Contact

Questions, comments and problem reports are welcome. See [Contact us](/contact).
