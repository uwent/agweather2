# AgWeather v2 server sizing

2026-11-02. A recommendation for the production server, for Ben and CALS IT. It updates `project-plan.md`'s "Server requirements" (2026-10-26) with sizes measured on the development archive and the products planned since (model maps, climatology, downloads, static maps).

## Recommendation

|             | At launch (Upper Midwest box)                                                     | Later: CONUS                                   |
| ----------- | --------------------------------------------------------------------------------- | ---------------------------------------------- |
| Instance    | **r7i.2xlarge** (8 vCPU, 64 GB), x86                                              | r7i.4xlarge (16 vCPU, 128 GB)                  |
| Data volume | **1.5 TB gp3**, 500 MB/s throughput                                               | 5 TB gp3, or 1.5 TB hot plus older years on S3 |
| Root volume | 100 GB gp3                                                                        | same                                           |
| Scratch     | 200 GB gp3 (GRIB downloads, deleted after decode)                                 | same                                           |
| Database    | RDS PostgreSQL, db.t4g.medium, 50 GB                                              | db.t4g.large                                   |
| Region      | us-east-1 (NOAA's open-data buckets are there: free, fastest transfers)           | same                                           |
| Backfill    | resize to 16–32 vCPU for the 2–4 days of the one-time 11-year backfill, then back | same, longer                                   |

Rough on-demand cost in us-east-1: about $0.53/hour for the r7i.2xlarge (~$390/month), ~$140/month for the volumes, and ~$50/month for RDS. That's about **$580/month**, or roughly $400 with a one-year savings plan. These are list prices from memory, so check them in the AWS calculator.

## Why not a t3 like WISP

WISP serves a small app. AgWeather v2 has steady background work all day:

- **Hourly ingest:** URMA, RTMA and HRRR decoding, QC, and rollups into the daily and cumulative stores.
- **Forecast:** an NBM run every hour (about 7 GB a day of reads), then rebuilding the forecast's stores and model maps.
- **Model maps** (D47): after each daily rollup, all 49 models over the grid, about 676,000 cells in the Upper Midwest.
- **API traffic:** grids, tiles and on-the-fly degree-day maps (a season of daily min/max is ~2 GB in memory for the Upper Midwest).

A t3 runs on CPU credits, and this load would use them up within hours. After that it runs at a fraction of a core. The r7i family gives steady CPU. The 64 GB of memory gives room for the web workers, two or three job workers and a model-map rebuild running together, plus the operating system's file cache, which is what keeps reads of the Zarr archive fast. An m7i.2xlarge (8 vCPU, 32 GB) is the minimum that would work, but it leaves little room for that cache. Graviton (r8g) is about 20% cheaper; it needs a test build first, because we use the system ecCodes library and a few compiled wheels.

## Storage

Scaled from the development archive (Wisconsin, 57,820 cells, measured 2026-11-02) to the Upper Midwest (675,962 cells, ×11.7), for the 11-year rolling window (2016 onward). The window keeps the total steady: each January the oldest year is dropped.

| Product                                                                                                                 | Wisconsin, per year (measured) | Upper Midwest, 11 years |
| ----------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ----------------------- |
| Hourly archive (18 variables)                                                                                           | 3.0 GB                         | 386 GB                  |
| Daily store (49 variables)                                                                                              | 0.42 GB                        | 53 GB                   |
| Running totals (degree days, precip, ET0)                                                                               | 0.27 GB                        | 35 GB                   |
| Model output maps and their ingredients (D47; 49 models × ~3 arrays, est.)                                              | ~1.3 GB                        | ~165 GB                 |
| Climatology (D61: 1991–2020 daily nClimGrid and gridMET, 1951–1990 nClimGrid for history, day-of-year statistics; est.) | —                              | ~60 GB                  |
| Forecast runs and IFS soil (current and previous)                                                                       | 0.4 GB                         | ~7 GB                   |
| Yearly NetCDF downloads (daily variables)                                                                               | —                              | ~55 GB                  |
| Tile and static map cache (capped)                                                                                      | —                              | 50 GB                   |
| Open-Meteo per-cell cache, logs, misc                                                                                   | —                              | ~10 GB                  |
| **Total**                                                                                                               |                                | **~820 GB**             |

With 25% headroom that's about 1 TB. 1.5 TB leaves room for the station data (D59) and for products not planned yet. gp3 volumes can grow without a reboot, so starting smaller and growing is also fine.

The archive could be rebuilt from public sources, but the backfill takes days. Take weekly EBS snapshots of the data volume (incremental, so cheap after the first), and keep RDS's automated backups for the app's database.

**CONUS** is ×5.5 the Upper Midwest's cells: about 4.5 TB, and twice the CPU and memory. That's the Phase 9 decision, with older years on S3 as the cheaper option for storage.

## What runs on it

One Docker Compose stack (`infra/`): `web` (Django on uvicorn), `worker` (Procrastinate jobs: ingest, forecast, model maps, alerts), and `caddy` (TLS, caching, the v1 redirect to `legacy.agweather.cals.wisc.edu`, D62). Postgres is on RDS. Outbound traffic: HTTPS to AWS S3 (NOAA buckets, Open-Meteo's open data), the Open-Meteo API, Copernicus CDS, and the campus email relay. Inbound: 80 and 443.
