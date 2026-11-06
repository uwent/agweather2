# Yearly data files

Every daily weather variable as one NetCDF file per year, for downloading the archive in bulk. Each past year has a complete file, and the current year has a file covering the year to date, updated weekly. A file is rebuilt whenever the data behind it are revised, so check `built_at` to see whether you have the newest copy.

Each entry gives the variable (as named in `/variables`), the year, the file's address and size, the first and last days it holds, and whether it covers the whole year. `time_zones` is the address of a small file giving each grid cell's time zone, since each day in the files is the cell's local calendar day.

The files hold the National Weather Service's 2.5 km grid in its native Lambert conformal projection, which GIS software, R's terra and Python's xarray read and place correctly. Values are in metric units (°C, mm and so on). Missing values are left missing.
