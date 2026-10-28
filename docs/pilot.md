# Phase 1 pilot: archive size and layout

PLAN.md Phase 1 D, run 2026-10-27. All 744 hours of URMA analyses for July 2025 over the `wisconsin` box (245 × 236 = 57,820 cells, 8 variables), stored in a dozen Zarr layouts to choose the archive's chunking, codec and precision and to size the server.

Scripts: `scripts/pilot_download.py` (download), `scripts/pilot_measure.py` (build each layout and time it), `scripts/pilot_report.py` (the tables). The raw hours are in `data/pilot/raw` (660 MB, packed at URMA's own precision by `scripts/pilot_encoding.py`).

## Decisions it led to

1. **Hourly store: int16 packed by the catalog's scale, pcodec level 8, chunks of 720 hours × 32 × 32 cells** (now `agdata.store`'s defaults). One cell's month reads in under 4 ms, so a season of every variable stays far inside the 300 ms target. Tile-shaped chunks (24 × 256 × 256) are 15% smaller but take over 10× longer for a point series, the hourly archive's main use; daily and cumulative stores keep tile-shaped chunks for maps (PLAN.md §5.3).
2. **pcodec over zstd**: about 28% smaller than plain zstd and 11% smaller than zstd with a shuffle filter, at the same read speed. A delta along time makes zstd worse; most fields change more from hour to hour than from cell to cell at 2.5 km.
3. **Coarse precision (D21)**: 0.1 °C, 0.1 m/s, 1 % cloud, 1° direction, 0.1 mm precip, 0.1 kPa pressure. URMA carries 0.01, mostly noise at the analysis's accuracy of about 1 °C, and noise doesn't compress. Coarse precision makes the archive 1.85× smaller (pcodec: 2.5× → 4.6× vs raw int16).
4. **Hourly ingest writes straight into the archive.** Rewriting one hour of every variable costs 3–4 s for Wisconsin with month-long chunks, roughly 40 s for the Upper Midwest (it scales with the number of chunks). That's acceptable once an hour; a staging store compacted monthly is only worth it at CONUS scale.
5. **A 1 TB data volume covers the Upper Midwest.** See below.

## Size

The chosen layout at D21's precision, extrapolated to a year (× 8766 / 744 hours), to the archive's 12 hourly variables (the pilot stored URMA's 8; the archive adds RH, shortwave, ET0 and soil temperature) and to each preset by cell count:

| Hourly store | Per year | 11 years |
|---|---|---|
| Wisconsin (57,820 cells) | 2.7 GB | 30 GB |
| Upper Midwest (675,962 cells) | 31 GB | **342 GB** |
| CONUS (3,744,965 cells) | 172 GB | 1.9 TB (an upper bound) |

- July is likely the hardest month to compress (convective precipitation and cloud), so a year may come in smaller.
- CONUS is overstated: its ocean, Canada and Mexico cells compress to almost nothing.
- Daily, cumulative and climatology cubes add roughly 15 GB a year for the Upper Midwest (project-plan.md), about 165 GB over 11 years.
- **Upper Midwest total: about 510 GB**, so 1 TB holds it with room for scratch and growth. CONUS needs 2–3 TB, or older years moved to S3.
- At URMA's own precision the Upper Midwest hourly store would have been 633 GB (about 800 GB in all).

## Download and decode

- Every message is a whole CONUS field (about 5 MB) whatever the window, so an hour of URMA (8 fields) is about 40 MB; the window changes only the decode and the storage.
- From this WSL machine (about 80 Mbit/s down): one hour in 11–16 s on one connection; 12 parallel connections reached 820 hours of data per hour of wall time, limited by the downlink. The month took about an hour.
- **The 11-year backfill is about 96,000 hours, roughly 4 TB of downloads**: about 5 days from here, hours on the server in AWS. Decoding is cheap (eccodes takes about 21 ms per CONUS field, and cropping to the window 4 ms), so with the network fast, store writes in month blocks are the main cost; parallelize by month.
- 2016–2017 files have no `.idx`; reading their GRIB2 headers costs two small requests per message and about 1.7 s per file, then only the wanted messages download.

## Measurements

Write all = the month in one block; Write 1 h = rewriting one hour of all 8 variables in place; Point read = one cell's month; Hour read = one hour over the whole window. Local WSL disk.

URMA's own precision (0.01):

| Layout | MB | × vs int16 | Write all | Write 1 h | Point read | Hour read |
|---|---|---|---|---|---|---|
| int16 pcodec8 24×256×256 | 247.9 | 2.8 | 2.5 s | 0.33 s | 47.1 ms | 5 ms |
| int16 pcodec8 168×64×64 | 270.1 | 2.5 | 3.1 s | 0.74 s | 8.0 ms | 17 ms |
| int16 pcodec8 720×32×32 | 278.6 | 2.5 | 4.1 s | 3.22 s | 3.8 ms | 70 ms |
| int16 delta-x zstd3 720×32×32 | 307.5 | 2.2 | 2.9 s | 2.58 s | 6.2 ms | 113 ms |
| int16 blosc-zstd5-shuffle 720×32×32 | 313.9 | 2.2 | 3.8 s | 3.13 s | 2.8 ms | 65 ms |
| int16 blosc-zstd5-bitshuffle 720×32×32 | 316.3 | 2.2 | 3.8 s | 2.20 s | 3.7 ms | 72 ms |
| int16 zstd9 720×32×32 | 363.8 | 1.9 | 6.6 s | 5.57 s | 4.4 ms | 76 ms |
| int16 zstd3 168×64×64 | 380.7 | 1.8 | 2.2 s | 0.56 s | 9.0 ms | 21 ms |
| int16 zstd3 24×256×256 | 384.3 | 1.8 | 1.6 s | 0.21 s | 50.6 ms | 5 ms |
| int16 zstd3 720×32×32 | 386.3 | 1.8 | 3.0 s | 2.45 s | 3.9 ms | 87 ms |
| int16 delta-time zstd3 720×32×32 | 410.4 | 1.7 | 4.3 s | 3.02 s | 6.0 ms | 112 ms |
| float32 zstd3 720×32×32 | 490.7 | 1.4 | 10.4 s | 3.46 s | 5.8 ms | 94 ms |

D21's precision:

| Layout | MB | × vs int16 | Write all | Write 1 h | Point read | Hour read |
|---|---|---|---|---|---|---|
| int16 pcodec8 24×256×256 | 128.9 | 5.3 | 3.3 s | 0.30 s | 54.7 ms | 5 ms |
| int16 pcodec8 720×32×32 | 150.3 | 4.6 | 5.0 s | 3.72 s | 3.5 ms | 68 ms |

Coarse precision except pressure (kept at 0.01 kPa), for the other layouts: pcodec8 168×64×64 160.2 MB, blosc-zstd5-bitshuffle 188.9 MB, zstd3 217.3 MB, float32 269.6 MB; the order is the same as at full precision.

Per variable for the month (pcodec8 24×256×256, URMA precision → D21): wind direction 42.8 → 25.4 MB, dew point 36.1 → 18.4, air temperature 35.6 → 17.9, wind speed 34.9 → 17.7, cloud cover 32.7 → 15.7, surface pressure 30.7 → 14.7, gust 30.5 → 16.5, precipitation 4.5 → 2.5.

## Not measured

- Daily and cumulative cubes (built in Phase 2 from the hourly store; small next to it).
- A winter month, to check July is the worst case.
- Reads from the server's EBS gp3 volume instead of a local disk.
- HRRR (shortwave from the 15-minute file, soil temperature): different files and a regrid, timed when Phase 2 adds them.
