# Degree-day presets

The usual growing degree-day setting for common crops: the method, the base temperature and the upper threshold, when the count usually starts, and the sources they come from. Each preset also gives the setting written ready to use as `dd` in other requests, in both unit systems, and, where one is known, the fall temperature that kills the crop.

Growing degree days measure the heat a crop has received: each day adds the degrees its temperatures were above the crop's base temperature, and an upper threshold limits how much a hot day can add. Where we run a crop's growth stage model, its preset is the setting that model uses, so a degree-day total for the crop agrees with the model's stages. Where sources disagree, `notes` says how and which one we follow.

A preset is a starting point. If your seed company, crop advisor or a local study uses a different setting, give that setting as `dd` instead.
