# Degree-day presets

The usual degree-day setting for common crops and for each insect we model: the method, the base temperature and the upper threshold, when the count usually starts, and the sources they come from. Each preset also gives the setting written ready to use as `dd` in other requests, in both unit systems, and, for a crop where one is known, the fall temperature that kills it.

Growing degree days measure the heat a crop or insect has received: each day adds the degrees its temperatures were above the base temperature, and an upper threshold limits how much a hot day can add. Where we run a crop's growth stage model, its preset is the setting that model uses, so a degree-day total for the crop agrees with the model's stages. An insect's preset is its model's setting and start date, so a total you compute with it matches the model's. Where sources disagree, `notes` says how and which one we follow.

A preset is a starting point. If your seed company, crop advisor or a local study uses a different setting, give that setting as `dd` instead.
