# All crops

Every crop we have models or data for, with what we have for each: its disease, insect, growth stage and field management models, its degree-day setting, the fall temperature that kills it, and whether we have typical planting dates for it.

Some crops are groups, such as cole crops, which hold cabbage, broccoli and others. A model for a group applies to each of its crops, so a crop's `models` include those for the groups it belongs to. Other requests take a crop's `id` as `crop`, such as `/models?crop=potato`.
