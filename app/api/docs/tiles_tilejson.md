# Map tile description

A TileJSON 3.0 description of a layer's tiles, which most web map libraries read directly: the tile address with your settings, the area covered, and the zoom levels.

For data tiles, `encoding` gives the layer's stored unit and the factors that turn a pixel's red, green and blue values into a value: value = (red × 65,536 + green × 256 + blue) × step − 8,388,608 × step. These match MapLibre's `raster-dem` custom encoding.

For colored tiles (`style=default`), `palette` names the palette, and `domain` gives the values its two ends stand for, in `domain_unit`. With a middle value in `scale`, `domain_middle` gives the value at the palette's middle color.
