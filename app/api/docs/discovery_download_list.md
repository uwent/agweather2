# Yearly data files

Every daily weather variable as one NetCDF file per year, for downloading the archive in bulk. Each past year has a complete file, and the current year has a file covering the year to date, updated weekly. A file is rebuilt whenever the data behind it are revised, so check `built_at` to see whether you have the newest copy.

Each entry gives the variable (as named in `/variables`), the year, the file's address and size, the first and last days it holds, and whether it covers the whole year.

**What a file holds.** Each yearly file holds one variable, one layer per day, on the National Weather Service's 2.5 km grid in its native Lambert conformal projection. GIS software, R's terra and Python's xarray read the projection and place the data correctly. Values are in metric units (°C, mm and so on). They are stored as whole numbers with a scale factor, which these programs apply automatically when they read the file. Missing values are left missing, never set to zero.

**The grid file.** `grid` is the address of one small file, `grid.nc`, that goes with every yearly file. It gives each grid cell's latitude and longitude (its center) and its local time zone. You need it only to plot the data on latitude and longitude without a projection library, or to show a cell's hours on its own clock. Every day in the files runs from midnight to midnight Central Standard Time all year (06:00 to 06:00 UTC), in every cell. It is kept apart from the yearly files because each yearly file opens more reliably in GIS software when it holds only one variable.

In R, terra reads the projection from the yearly file itself:

```r
library(terra)
tmax <- rast("air_temperature_max_2025.nc")  # 365 layers in °C
july15 <- tmax[[196]]
plot(project(july15, "EPSG:4326"))           # on latitude and longitude
```

In Python, add the grid file's latitude and longitude to plot without a projection library:

```python
import xarray as xr

tmax = xr.open_dataset("air_temperature_max_2025.nc")
grid = xr.open_dataset("grid.nc")
tmax = tmax.assign_coords(lat=grid.lat, lon=grid.lon)
tmax.air_temperature_max.sel(time="2025-07-15").plot(x="lon", y="lat")
```
