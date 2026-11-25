# Map tile description

A TileJSON 3.0 description of a layer's tiles, which most web map libraries read directly: the tile address with your settings, the area covered, and the zoom levels.

For data tiles, `encoding` gives the layer's stored unit and the factors that turn a pixel's red, green and blue values into a value: value = (red × 65,536 + green × 256 + blue) × step − 8,388,608 × step. These match MapLibre's `raster-dem` custom encoding.

For colored tiles (`style=default`), `palette` names the palette, and `domain` gives the values its two ends stand for, in `domain_unit`. With a middle value in `scale`, `domain_middle` gives the value at the palette's middle color.

The description also carries the text a map image (`/maps/{layer}.png`) prints with the same settings, so a page can show a map's title, notes and legend without another request:

- `name`: the map's title, such as "Precipitation, cumulative total".
- `subtitle`: when the map is for, and a model's planting dates and options, such as "Jul 1 – Jul 7, 2025 (7 days)" or "Nov 6, 2026, 7 a.m. CST (13:00 UTC)".
- `caption`: lines of text naming the data sources (and the forecast, where the map includes forecast days) and, for a range of days combined, the most days estimated or missing at any location.
- `warnings`: notes about the map, each a sentence, as `meta.warnings` gives them for the same map from `/grids`: days with no data yet, a forecast that is out of date, or model results that rest on days of missing weather. Empty when there are none.
- `categories`: for a map of levels rather than amounts, each level's `value` (the number the tiles hold), `name` and `code`. A risk level's code is the name `first=` and `last=` take, such as `high`; a crop stage's is its code, such as `R1`, and the value −1 stands for the days before the first stage. Null for every other map.

The response has an `ETag`, so a client that sends it back in `If-None-Match` gets a 304 until the map's data change.
