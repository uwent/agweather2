# Map tile

A 256-pixel map tile of a layer, for web maps such as MapLibre, Leaflet and OpenLayers, and for GIS software. Tiles use the standard web map grid of zoom levels 0 to 8; beyond zoom 8, enlarge the zoom 8 tiles. The layer's settings are the same parameters as for `/grids/{layer}`.

By default, each pixel's color encodes the value of the grid cell beneath it, for a map program to read and color. `/tiles/{layer}.json` explains how to decode it. Add `style=default` for tiles colored with the layer's palette, ready to display. Cells without data are transparent.
