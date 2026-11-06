# Map data

A layer's values over an area, for one day or hour, each step of a range, or a range combined into one map (`stat`). The area is everything the service covers unless you choose a box (`bbox`), a state or a county (`region`).

JSON and CSV give one row per grid cell (and step), with the cell's center as `lat` and `lng`, which reads directly into a table. NetCDF and GeoTIFF files keep the native grid and its projection, which GIS software and xarray place correctly. Cells with no data are `null` or empty.

A model layer shows each location's result using that location's typical planting date and the model's default settings. To use your own planting or biofix date, run the model at your location with `/models/{model_id}/run`. Model layers cover land only.

When a range is combined with `stat=sum`, each cell also reports how many of its days were estimated or missing, in JSON, CSV and GeoTIFF (as extra bands). A NetCDF file holds the map's values only, so that GIS software opens it as a single layer. Degree days can be mapped by any method and thresholds with the `degree_days` layer (`/grids/degree_days?dd=sine_50_86&start=2026-03-01&stat=sum`).
