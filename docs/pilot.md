# Phase 1 pilot: archive size and layout

PLAN.md Phase 1 D. One summer month of URMA hourly analyses over the `wisconsin` box (245 × 236 cells), stored in several Zarr layouts, to choose the archive's chunking, codec and precision and to size the server. **Draft:** the numbers below are from the first 9 days (216 hours) and will be replaced by the full month of July 2025.

Scripts: `scripts/pilot_download.py` (download), `scripts/pilot_measure.py` (build each layout and time it), `scripts/pilot_report.py` (these tables).

## Recommendations

1. **Hourly store: int16 packed by the catalog's scale, pcodec level 8, chunks of 720 hours × 32 × 32 cells.** One cell's month reads in about 2 ms (a season of all variables well under the 300 ms target), and it is the smallest layout among those fast for point reads. The tile-shaped chunks (24 × 256 × 256) are 10–15% smaller still but take 10× longer for a point series, the archive's main use; daily and cumulative stores keep tile-shaped chunks for maps (PLAN.md §5.3).
2. **pcodec over zstd**: 25–45% smaller for the same reads and writes. Shuffle filters help zstd but not as much; a delta along time makes zstd worse (most fields change more hour to hour than cell to cell at 2.5 km).
3. **Precision is the bigger lever (a decision for Ben, PLAN.md Q6).** URMA carries 0.01 for temperature, dew point, wind and cloud cover; the analysis is good to around 1 °C, so the last digit is mostly noise that doesn't compress. Rounding to 0.1 °C, 0.1 m/s, 1 % cloud, 1° direction and 0.1 mm precip makes the archive 1.7× smaller (pcodec: 2.4× → 4.1× vs raw int16). Degree days, DSVs and ET0 don't change at that precision. Surface pressure (0.01 kPa) then becomes the largest variable; 0.1 kPa would be enough for ET0.
4. **Hourly ingest writes straight into the archive.** Rewriting one hour of every variable costs about 2 s for Wisconsin with month-long chunks, roughly 25 s for the Upper Midwest (it scales with the number of chunks). That's acceptable once an hour; a staging store compacted monthly is only worth it at CONUS scale.
5. **Size the volume for coarse precision, or 1 TB is tight.** See below.

## Size

Extrapolated to a year (× 8766 / measured hours), to 12 hourly variables (the pilot stored URMA's 8; the archive adds RH, shortwave radiation, ET0 and soil temperature), and to each preset by cell count. July is likely the hardest month to compress (convective precipitation and cloud), so a year may come in smaller. CONUS is overstated: its ocean, Canada and Mexico cells compress to almost nothing.

| Hourly store, 11 years | URMA precision | Coarse precision |
|---|---|---|
| Wisconsin (57,820 cells) | 55 GB | 33 GB |
| Upper Midwest (675,962 cells) | 640 GB | 380 GB |
| CONUS (3,744,965 cells) | 3.5 TB (less in practice) | 2.1 TB (less in practice) |

Daily, cumulative and climatology cubes add roughly 15 GB a year for the Upper Midwest (project-plan.md), about 165 GB over 11 years. With coarse precision the Upper Midwest totals about 550 GB, which fits the 1 TB volume with room for the backfill's scratch files; at URMA precision it is about 800 GB.

## Download

- Every message is a whole CONUS field (about 5 MB) whatever the window, so an hour of URMA (8 fields) is about 40 MB. The window doesn't change the download, only the decode and storage.
- From this WSL machine: one hour in 11–16 s on one connection; 8–16 parallel connections reach about 700 hours of data per hour of wall time, limited by the downlink (about 80 Mbit/s).
- **The 11-year backfill is about 96,000 hours, roughly 4 TB of downloads.** From here that would be about 6 days; on the server in AWS (from the same region as the bucket, or any region at no charge) at several Gbit/s, expect hours rather than days. Decoding is cheap (eccodes takes about 21 ms per CONUS field, and cropping to the window 4 ms), so even 16 cores of decode keep up with a fast network; the store writes, a month per block, are the other cost.
- 2016–2017 files have no `.idx`; reading their GRIB2 headers costs two small requests per message and about 1.7 s per file, then only the wanted messages download.

## Measurements (9 days, draft)

Write all = the 9 days in one block; Write 1 h = rewriting one hour of all 8 variables in place; Point read = one cell's series over the measured hours; Hour read = one hour over the whole window. Local WSL disk.

URMA precision:

| Layout | MB | × vs int16 | Write all | Write 1 h | Point read | Hour read |
|---|---|---|---|---|---|---|
| int16 pcodec8 24×256×256 | 72.3 | 2.8 | 0.8 s | 0.37 s | 19.9 ms | 5 ms |
| int16 pcodec8 720×32×32 | 81.7 | 2.4 | 1.6 s | 1.92 s | 2.2 ms | 63 ms |
| int16 pcodec8 168×64×64 | 82.3 | 2.4 | 1.3 s | 0.91 s | 4.6 ms | 21 ms |
| int16 blosc-zstd5-bitshuffle 720×32×32 | 90.8 | 2.2 | 1.3 s | 1.61 s | 2.7 ms | 71 ms |
| int16 zstd3 720×32×32 | 112.7 | 1.8 | 1.5 s | 1.77 s | 2.7 ms | 71 ms |
| int16 delta-time zstd3 720×32×32 | 120.9 | 1.7 | 1.8 s | 2.46 s | 4.4 ms | 116 ms |
| float32 zstd3 720×32×32 | 144.5 | 1.4 | 2.8 s | 2.03 s | 3.3 ms | 76 ms |

Coarse precision:

| Layout | MB | × vs int16 | Write all | Write 1 h | Point read | Hour read |
|---|---|---|---|---|---|---|
| int16 pcodec8 24×256×256 | 42.4 | 4.7 | 0.6 s | 0.26 s | 17.6 ms | 5 ms |
| int16 pcodec8 720×32×32 | 48.8 | 4.1 | 1.4 s | 1.73 s | 2.2 ms | 66 ms |
| int16 blosc-zstd5-bitshuffle 720×32×32 | 54.0 | 3.7 | 1.3 s | 1.63 s | 2.9 ms | 77 ms |
| int16 zstd3 720×32×32 | 63.7 | 3.1 | 1.1 s | 1.50 s | 2.5 ms | 70 ms |

Per variable (pcodec, URMA precision → coarse), MB for 9 days: wind direction 12.5 → 7.4, dew point 10.6 → 5.4, air temperature 10.5 → 5.3, wind speed 10.2 → 5.2, cloud cover 9.5 → 4.5, gust 8.9 → 4.9, surface pressure 8.9 → 8.9, precipitation 1.2 → 0.7.

## Not measured yet

- Daily and cumulative cubes (built in Phase 2 from the hourly store; their size is small next to it).
- A winter month, to check July is the worst case.
- Reads from the server's EBS gp3 volume instead of a local disk.
