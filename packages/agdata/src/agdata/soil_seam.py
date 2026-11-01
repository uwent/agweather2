"""IFS's soil temperature shifted to meet ERA5-Land's at the seam (Q23, PLAN.md Phase 4 I).

The archive's soil is ERA5-Land's up to its last hour (~5 days behind), then IFS's: the provisional hours and the
forecast. In winter IFS reads 1.6–2.7 °C below ERA5-Land at 10 cm (docs/validation-soil.md), so without this the soil
steps down at the seam. Each cell's IFS soil is shifted by the difference in ERA5-Land's last hour, times a weight
that fades with the hours since it: how much of the difference at the seam is still there that much later, fitted on
the archive (ERA5-Land) against Open-Meteo's IFS at 80 Wisconet stations (`scripts/compare_soil_wisconet.py
--fit-seam`). Snow depth isn't shifted.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np

TABLE_PATH = Path(__file__).parent / "data" / "ifs_soil_seam.json"
VARIABLES = ("soil_temperature_4cm", "soil_temperature_10cm", "soil_temperature_30cm")


@dataclass(frozen=True, kw_only=True)
class Table:
    version: int
    lead_hours: np.ndarray  # ascending, from 0
    weight: dict[str, np.ndarray]  # per variable, at lead_hours; 1 at the seam


@cache
def table(path: Path = TABLE_PATH) -> Table:
    data = json.loads(path.read_text())
    return Table(
        version=int(data["version"]),
        lead_hours=np.asarray(data["lead_hours"], dtype=float),
        weight={name: np.asarray(w, dtype=float) for name, w in data["weight"].items()},
    )


def weights(name: str, lead_hours: np.ndarray, seam: Table | None = None) -> np.ndarray:
    """The weight on the seam's difference `lead_hours` after it: linear between the table's leads and held at its
    last (part of the difference is a lasting bias); 0 before the seam."""
    seam = seam or table()
    w = seam.weight[name]
    return np.interp(np.asarray(lead_hours, dtype=float), seam.lead_hours, w, left=0.0, right=float(w[-1]))


def shift(
    values: np.ndarray, offset: np.ndarray, lead_hours: np.ndarray, name: str, seam: Table | None = None
) -> np.ndarray:
    """IFS's hours (time, y, x) shifted by each cell's `offset` (ERA5-Land − IFS in the seam's hour, °C; NaN where
    either was missing, which leaves the cell as it is) faded by the weight at each hour's lead."""
    w = weights(name, lead_hours, seam).astype(np.float32)
    return values + np.nan_to_num(offset, nan=0.0)[None, :, :] * w[:, None, None]


def fit(difference: np.ndarray, lead_hours: np.ndarray, starts: np.ndarray | None = None) -> np.ndarray:
    """The least-squares weight w(h) for predicting the difference h hours on from the difference now:
    Σ D(t) D(t+h) / Σ D(t)², over every station (rows) and hour t (columns; `starts` limits which t count). Held to
    [0, 1] and made non-increasing, so noise at long leads can't make the shift grow back."""
    n = difference.shape[1]
    use = np.ones(n, dtype=bool) if starts is None else starts
    out = []
    for h in lead_hours:
        h = int(h)
        now, then = difference[:, : n - h], difference[:, h:]
        ok = np.isfinite(now) & np.isfinite(then) & use[None, : n - h]
        out.append(float((now[ok] * then[ok]).sum() / (now[ok] ** 2).sum()) if ok.any() else 0.0)
    w = np.clip(np.array(out), 0.0, 1.0)
    w[0] = 1.0
    return np.minimum.accumulate(w)
