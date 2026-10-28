"""Phase 1 D pilot, step 2: build hourly stores from the downloaded hours in several layouts and measure them.

uv run python scripts/pilot_measure.py --raw data/pilot/raw --out data/pilot/stores
Prints a table and writes <out>/results.json. Each layout is a chunk shape plus a codec; sizes are on disk.
"""

import argparse
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import zarr
from zarr.codecs import BloscCodec, BytesCodec, TransposeCodec, ZstdCodec
from zarr.codecs.numcodecs import Delta, PCodec

from agdata.catalog import FILL
from agdata.grid import service_window
from agdata.store import steps_in_year
from pilot_encoding import pilot_variable

LAYOUTS = {
    # name: (chunks (time, y, x), compressors, dtype, filters)
    "int16 zstd3 720x32x32": ((720, 32, 32), [ZstdCodec(level=3)], "int16"),
    "int16 zstd9 720x32x32": ((720, 32, 32), [ZstdCodec(level=9)], "int16"),
    "int16 blosc-zstd5-shuffle 720x32x32": (
        (720, 32, 32),
        [BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")],
        "int16",
    ),
    "int16 blosc-zstd5-bitshuffle 720x32x32": (
        (720, 32, 32),
        [BloscCodec(cname="zstd", clevel=5, shuffle="bitshuffle")],
        "int16",
    ),
    "int16 zstd3 168x64x64": ((168, 64, 64), [ZstdCodec(level=3)], "int16"),
    "int16 zstd3 24x256x256": ((24, 256, 256), [ZstdCodec(level=3)], "int16"),
    "float32 zstd3 720x32x32": ((720, 32, 32), [ZstdCodec(level=3)], "float32"),
    # Deltas between neighbors: along x (C order), or along time (transposed so time is innermost)
    "int16 delta-x zstd3 720x32x32": ((720, 32, 32), [ZstdCodec(level=3)], "int16", [Delta(dtype="<i2")]),
    "int16 delta-time zstd3 720x32x32": (
        (720, 32, 32),
        [ZstdCodec(level=3)],
        "int16",
        [TransposeCodec(order=(1, 2, 0)), Delta(dtype="<i2")],
    ),
    # pcodec picks its own delta order per chunk; it serializes the array itself
    "int16 pcodec8 720x32x32": ((720, 32, 32), None, "int16", None, PCodec(level=8)),
    "int16 pcodec8 168x64x64": ((168, 64, 64), None, "int16", None, PCodec(level=8)),
    "int16 pcodec8 24x256x256": ((24, 256, 256), None, "int16", None, PCodec(level=8)),
}


# --coarse: what the archive would cost at coarser precision than URMA's own (0.01 for most fields); the factor
# divides the catalog's packed int16 values (e.g. 0.01 °C x 10 = 0.1 °C)
COARSE = {
    "air_temperature": 10,
    "dew_point": 10,
    "wind_speed": 10,
    "wind_gust": 10,
    "cloud_cover": 100,
    "wind_direction": 10,
    "precipitation": 10,
}


def coarsen(name: str, block: np.ndarray) -> np.ndarray:
    factor = COARSE.get(name)
    if not factor:
        return block
    return np.where(block == FILL, FILL, np.round(block / factor)).astype(np.int16)


def du(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/pilot/raw")
    parser.add_argument("--out", default="data/pilot/stores")
    parser.add_argument("--box", default="wisconsin")
    parser.add_argument("--layouts", nargs="*", default=list(LAYOUTS))
    parser.add_argument("--coarse", action="store_true", help="quantize to the COARSE precision first")
    args = parser.parse_args()

    raw, out = Path(args.raw), Path(args.out)
    files = sorted(raw.glob("*.npz"))
    hours = [datetime.strptime(f.stem, "%Y%m%d%H").replace(tzinfo=UTC) for f in files]
    if not hours:
        raise SystemExit(f"no hours in {raw}")
    year = hours[0].year
    t0 = int((hours[0] - datetime(year, 1, 1, tzinfo=UTC)).total_seconds() // 3600)
    if any(int((h - hours[0]).total_seconds() // 3600) != n for n, h in enumerate(hours)):
        raise SystemExit("the downloaded hours have gaps; rerun the download")
    window = service_window(args.box)

    # Every variable as one (hours, y, x) int16 block
    names = sorted({name for f in files[:1] for name in np.load(f).files})
    blocks = {name: np.stack([np.load(f)[name] for f in files]) for name in names}
    if args.coarse:
        blocks = {name: coarsen(name, block) for name, block in blocks.items()}
    n_hours = len(hours)
    print(f"{n_hours} hours from {hours[0]:%Y-%m-%d %H}Z, window {window.shape}, variables {', '.join(names)}")

    rng = np.random.default_rng(0)
    cells = [
        (int(j), int(i))
        for j, i in zip(rng.integers(0, window.shape[0], 20), rng.integers(0, window.shape[1], 20), strict=True)
    ]

    results = []
    for layout in args.layouts:
        chunks, compressors, dtype, *rest = LAYOUTS[layout]
        filters = rest[0] if rest and rest[0] else None
        serializer = rest[1] if len(rest) > 1 else BytesCodec()
        path = out / layout.replace(" ", "_")
        shutil.rmtree(path, ignore_errors=True)
        group = zarr.open_group(path, mode="w")
        n_year = steps_in_year(year, "hour")
        chunk_shape = (min(chunks[0], n_year), min(chunks[1], window.shape[0]), min(chunks[2], window.shape[1]))
        arrays = {}
        for name in names:
            arrays[name] = group.create_array(
                name,
                shape=(n_year, *window.shape),
                chunks=chunk_shape,
                dtype=dtype,
                fill_value=int(FILL) if dtype == "int16" else np.nan,
                filters=filters or (),
                serializer=serializer,
                compressors=compressors or (),
            )

        def as_stored(name: str, block: np.ndarray, dtype: str = dtype) -> np.ndarray:
            if dtype == "int16":
                return block
            decoded = pilot_variable(name).decode(block) * (COARSE.get(name, 1) if args.coarse else 1)
            return decoded.astype(np.float32)

        began = time.perf_counter()
        for name in names:
            arrays[name][t0 : t0 + n_hours] = as_stored(name, blocks[name])
        write_month = time.perf_counter() - began

        # Hourly ingest: rewrite one hour in the middle of the month, every variable
        mid = t0 + n_hours // 2
        began = time.perf_counter()
        for name in names:
            arrays[name][mid : mid + 1] = as_stored(name, blocks[name][n_hours // 2 : n_hours // 2 + 1])
        write_hour = time.perf_counter() - began

        reopened = zarr.open_group(path, mode="r")
        began = time.perf_counter()
        for j, i in cells:
            np.asarray(reopened["air_temperature"][t0 : t0 + n_hours, j, i])  # pyright: ignore[reportIndexIssue]
        point_month = (time.perf_counter() - began) / len(cells)

        began = time.perf_counter()
        for k in range(10):
            np.asarray(reopened["air_temperature"][t0 + k * (n_hours // 10)])  # pyright: ignore[reportIndexIssue]
        hour_window = (time.perf_counter() - began) / 10

        sizes = {name: du(path / name) for name in names}
        total = sum(sizes.values())
        raw_bytes = sum(block.nbytes for block in blocks.values())
        results.append(
            {
                "layout": layout,
                "bytes": total,
                "bytes_per_variable": sizes,
                "ratio_vs_int16": raw_bytes / total,
                "chunk_files": sum(1 for _ in path.rglob("c/*")),
                "write_month_s": write_month,
                "write_hour_s": write_hour,
                "read_point_month_ms": point_month * 1000,
                "read_hour_window_ms": hour_window * 1000,
            }
        )
        r = results[-1]
        print(
            f"{layout:40} {total / 1e6:8.1f} MB  x{r['ratio_vs_int16']:4.1f}  write month {write_month:5.1f}s"
            f"  write 1 h {write_hour:5.2f}s  point {r['read_point_month_ms']:6.1f} ms"
            f"  hour {r['read_hour_window_ms']:6.1f} ms"
        )

    meta = {
        "coarse": args.coarse,
        "hours": n_hours,
        "start": hours[0].isoformat(),
        "window": list(window.shape),
        "variables": names,
    }
    (out / f"results{'-coarse' if args.coarse else ''}.json").write_text(
        json.dumps({"meta": meta, "results": results}, indent=2)
    )


if __name__ == "__main__":
    main()
