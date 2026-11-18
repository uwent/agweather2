# Wisconsin apple bud and bloom stages, 2023–2026

Apple stages reported on a stated date in Wisconsin, from UW–Madison's fruit program, the Peninsular Agricultural Research Station's weekly updates, growers' posts and DATCP's weekly field notes. We use them to check `apple-stages` ([report](../../models/apple-stages.md)).

## File

`observations.csv`, one row per observation (a site, a date and the cultivars a stage was given for):

- `site`: where we place it, with `lat` and `lon` (approximate, about 0.01°: the research station, or the farm's town). Empty for a regional report.
- `site_as_written`: the place as the source names it. "Southern Wisconsin" in UW's 2024–2026 phenology updates and scouting reports is placed at the West Madison Agricultural Research Station (WMARS, Verona): the June 2025 and 2026 reports caption the same series of photos "WMARS"; the earlier ones don't name the site. One 2023 row is placed there because the article was written after a visit to WMARS that day.
- `date`: the day observed. Where the source gives a scouting date or a photo date, that date; where it gives only the report's date (PARS's weekly updates, articles), the day the report was written, and the stage is the week's (about ±3 days).
- `cultivars`, `stage_as_written`: as the source gives them, quoted or closely paraphrased.
- `codes`: the stages it can be in on NEWA's list, as the model names them (ST silver tip, GT green tip, HIG half-inch green, TC tight cluster, P pink, B bloom, PF petal fall, FS fruit set, which is NEWA's "post petal fall"; `-` before silver tip), space-separated. A range ("tight cluster to pink") takes every stage in it; "no blossoms open" takes every stage before bloom; "entering king bloom" and "a few blossoms open" take pink or bloom; "early petal fall" bloom or petal fall; popcorn (balloon) is pink. A fruit size of 10 mm or less is petal fall or fruit set (UW's reports give 5–10 mm at petal fall), a larger one fruit set. Empty where the row isn't used in the check: regional reports, a forecast, a statement not specific to apples, and one range across four stages.
- `reliability`: A, observed that day at a named site; B, at a named site within the week before the report, or a dated photo caption; C, regional or not specific to apples; F, a forecast.
- `source`: the page it came from. `note`: how the row was read.

Farms are named as their public posts name them; growers' and staff names are left out.

## Sources

Gathered on 2026-11-18 by reading every post since March 2023 on these sites (through their WordPress JSON listings, then the posts themselves):

- UW Fruit Program, [fruit.wisc.edu](https://fruit.wisc.edu/): Wisconsin Fruit News, including the fruit phenology updates (April 2024, April 2025), the Wisconsin fruit crop scouting reports (2025), "Notes from the Field" grower chats and topic articles.
- UW–Madison Extension Crops and Soils, [cropsandsoils.extension.wisc.edu](https://cropsandsoils.extension.wisc.edu/): Wisconsin Fruit News from spring 2026 (scouting reports, grower chats).
- Peninsular Agricultural Research Station, [peninsular.ars.wisc.edu](https://peninsular.ars.wisc.edu/): weekly updates with a growth stage line for Door County's apples, 2024–2026 (none on the site for 2023).
- Sunrise Orchards, Gays Mills ([sunriseapples.com/blog](https://www.sunriseapples.com/blog/)): the orchard's bloom posts, found by search (the blog's index lists only recent posts).
- DATCP's weekly "Field Notes" bulletins (content.govdelivery.com): regional summaries from apple growers.

## Caveats

- Most observations are of bloom and pink; green tip, tight cluster and petal fall have only a few each, and silver tip and half-inch green fewer.
- UW's and PARS's reports give stages by cultivar or as a range across cultivars and the county; Sunrise Orchards gives the percent of blossoms open across the orchard, with no cultivar. The model's stages are McIntosh's timing, so early cultivars (Zestar, Paula Red) are expected ahead of it.
- Placing "southern Wisconsin" at WMARS is our reading, not the source's statement (see `site_as_written`).
- One page disagrees with itself (Ida Red, May 7, 2025: "early petal fall" in the text, "full bloom" in the photo caption); the row takes both.
- Degree days printed in the same reports (NEWA's DD43 at a nearby station) are not copied here: the reports don't tie them to the observation, and the check computes its own from the archive.
- No observations were found for Bayfield, Eau Claire or southeastern Wisconsin's orchards.
