"""Phase 1 D pilot, step 3: turn results.json (and results-coarse.json) into the tables for docs/pilot.md.

uv run python scripts/pilot_report.py --stores data/pilot/stores [--catalog-variables 12]
Extrapolates the measured hours to a year and to each service-box preset by cell count; the archive will hold
more variables than the pilot measured, so sizes are also scaled to --catalog-variables.
"""

import argparse
import json
from pathlib import Path

from agdata.grid import service_window

PRESETS = ["wisconsin", "upper_midwest", "conus"]
YEARS = 11


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stores", default="data/pilot/stores")
    parser.add_argument("--catalog-variables", type=int, default=12)
    args = parser.parse_args()
    stores = Path(args.stores)

    for name in ["results.json", "results-coarse.json"]:
        path = stores / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        meta, results = data["meta"], data["results"]
        hours, n_vars = meta["hours"], len(meta["variables"])
        cells = meta["window"][0] * meta["window"][1]
        per_year = 8766 / hours
        scale_vars = args.catalog_variables / n_vars
        precision = "coarse (0.1 °C, 0.1 m/s, 1 %, 1°, 0.1 mm)" if meta["coarse"] else "URMA's own (0.01)"
        print(f"\n### Precision: {precision}\n")
        print(f"Measured: {hours} hours from {meta['start'][:10]}, {n_vars} variables, {cells:,} cells.\n")
        header = "| Layout | Measured MB | x vs int16 | Write all | Write 1 h | Point read | Hour read |"
        header += " GB/yr WI | GB/yr UM | 11 yr UM | 11 yr CONUS |"
        print(header)
        print("|" + "---|" * 11)
        for r in sorted(results, key=lambda r: r["bytes"]):
            yearly = r["bytes"] * per_year * scale_vars / cells  # bytes per cell per year
            sizes = {p: yearly * service_window(p).size / 1e9 for p in PRESETS}
            print(
                f"| {r['layout']} | {r['bytes'] / 1e6:.1f} | {r['ratio_vs_int16']:.1f} | {r['write_month_s']:.1f} s"
                f" | {r['write_hour_s']:.2f} s | {r['read_point_month_ms']:.1f} ms | {r['read_hour_window_ms']:.0f} ms"
                f" | {sizes['wisconsin']:.1f} | {sizes['upper_midwest']:.0f} | {sizes['upper_midwest'] * YEARS:.0f}"
                f" | {sizes['conus'] * YEARS:.0f} |"
            )
        best = min(results, key=lambda r: r["bytes"])
        print(f"\nPer variable ({best['layout']}), MB measured:")
        for var, size in sorted(best["bytes_per_variable"].items(), key=lambda kv: -kv[1]):
            print(f"- {var}: {size / 1e6:.1f}")


if __name__ == "__main__":
    main()
