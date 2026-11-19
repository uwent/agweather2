"""Red crown rot of soybean: predicted field-level incidence (beta).

Ochi et al. (2026) fitted three separate single-variable logistic models of field-level incidence (in Japan, in
fields nearly all infested) to weather around the beginning of flowering (R1): mean temperature over the 31 days
from R1 (R² 0.33), and precipitation over the 31 days before it (0.08) and from it (0.09). The Crop Protection
Network's algorithm (ver. 1.0, 2026-08-12) combines them, weighted by each one's share of the summed R² (0.66,
0.16, 0.18), and sets no risk levels ("no color code for threshold can be set yet"), so this model has none: it gives
the predicted incidence. The biofix is the R1 date.

The incidence is given once the 31 days from R1 are complete (R1 + 30) and held after; until then it has no value.
The Crop Risk Tool showed a running value with the rain so far prorated to a full window, an estimate of rain not yet
fallen that swung the result widely (D45: rain is never estimated). Precipitation is the sum of the known days, with
days without data counted as no rain and reported in `precipitation_days_missing` (a missing day before R1 lowers
the incidence, one after raises it: read the result with care when more than about 3 are missing).

Ported from the Crop Risk Tool (`predict_red_crown_rot`, `build_red_crown_rot`) with parity tests; changed in 0.3
after the audit (`tmp/crt-model-audit-2-wheat-rcr.md`).
"""

from collections.abc import Mapping

import numpy as np

from agmodels.spec import (
    Biofix,
    Change,
    Check,
    Citation,
    ExplorerInput,
    Input,
    ModelSpec,
    Quantity,
)

WINDOW = 31

SPEC = ModelSpec(
    id="red-crown-rot",
    name="Red crown rot incidence",
    group="disease",
    version="0.3",
    status="beta",
    summary="Predicted share of soybean plants with red crown rot, from temperature and rain in the month either side of the beginning of flowering (R1).",
    topics=("red-crown-rot",),
    crops=("soybean",),
    citations=(
        Citation(
            text="Ochi, S., Kishi, S., Kawaguchi, A. and Akamatsu, H. (2026). Meteorological and agronomic factors analysis on the field-level incidence of red crown rot of soybean. Phytopathology 116, 1405–1413.",
            doi="10.1094/PHYTO-06-25-0207-R",
        ),
        Citation(
            text="Crop Protection Network: Red crown rot of soybean.",
            url="https://cropprotectionnetwork.org/encyclopedia/red-crown-rot-of-soybean",
        ),
    ),
    inputs=(
        Input(
            name="air_temperature_mean",
            label="Mean temperature",
            unit="degC",
            description="Mean over the 31 days from R1",
        ),
        Input(
            name="precipitation_sum",
            label="Precipitation",
            unit="mm",
            description="Totals over the 31 days before and from R1",
        ),
    ),
    outputs=(
        Quantity(name="incidence", label="Predicted incidence", unit="percent"),
        Quantity(name="temperature_mean_reproductive", label="Mean temperature from R1", unit="degC"),
        Quantity(name="precipitation_vegetative", label="Precipitation, 31 days before R1", unit="mm"),
        Quantity(name="precipitation_reproductive", label="Precipitation from R1 so far", unit="mm"),
        Quantity(
            name="precipitation_days_missing",
            label="Days without precipitation data",
            unit="day",
            description="In the 31 days before R1 and the days from R1 so far, counted as no rain",
        ),
    ),
    risk=None,  # the authors' algorithm sets no levels yet
    explorer=(
        ExplorerInput(
            name="temperature_reproductive",
            label="Mean temperature, 31 days from R1",
            unit="degC",
            minimum=15,
            maximum=35,
            step=0.5,
            default=25,
        ),
        ExplorerInput(
            name="precipitation_vegetative",
            label="Precipitation, 31 days before R1",
            unit="mm",
            minimum=0,
            maximum=400,
            step=5,
            default=100,
        ),
        ExplorerInput(
            name="precipitation_reproductive",
            label="Precipitation, 31 days from R1",
            unit="mm",
            minimum=0,
            maximum=400,
            step=5,
            default=100,
        ),
    ),
    sweep={
        "temperature_reproductive": (20.0, 24.0, 28.0),
        "precipitation_vegetative": (25.0, 100.0, 250.0),
        "precipitation_reproductive": (25.0, 100.0, 250.0),
    },
    lookback_days=WINDOW,
    biofix=Biofix(default="07-01", label="R1 (beginning flowering)"),
    biofix_stage=("soybean-stages", "R1"),  # the soybean model's R1 is the default when it has run
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool."),
        Change(
            version="0.2",
            date="2026-10-30",
            note="Precipitation sums the known days and counts missing days as no rain, reporting how many; the tool's mean of the known days times 31 estimated them. Unchanged without gaps.",
        ),
        Change(
            version="0.3",
            date="2026-11-19",
            note="The incidence is given once the 31 days from R1 are complete (rain is no longer prorated over the window's first days), and the provisional risk levels (5, 30 and 60 %) are gone: the authors' algorithm sets none. Final values are unchanged.",
        ),
    ),
    checks=(
        Check(
            kind="system",
            against="The Crop Risk Tool, which AgWeather's red crown rot model was ported from, on the tool's own 2025 weather for Eau Claire, Wisconsin",
            result="With flowering (R1) on July 1, 2025, our predicted incidence matched the tool's from July 31 (R1 + 30), when the 31 days from R1 are complete and we give it, and the rain and temperature behind it matched on every day of the year. This shows that we reproduce the tool, not that its predictions are right: the model was developed in Japan and hasn't been tested against red crown rot in the United States.",
            report="docs/validation/models/red-crown-rot.md#against-the-crop-risk-tool-on-the-same-weather",
        ),
    ),
)


def incidence(temperature_reproductive, precipitation_vegetative, precipitation_reproductive) -> np.ndarray:
    def fli(logit):
        return 1 / (1 + np.exp(np.asarray(logit, dtype=float)))

    return (
        0.66 * fli(15.067 - 0.602 * np.asarray(temperature_reproductive, dtype=float))
        + 0.16 * fli(0.184 - 0.004 * np.asarray(precipitation_vegetative, dtype=float))
        + 0.18 * fli(-1.257 + 0.005 * np.asarray(precipitation_reproductive, dtype=float))
    )


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    temperature = np.asarray(inputs["air_temperature_mean"], dtype=float)
    precip = np.asarray(inputs["precipitation_sum"], dtype=float)
    n = temperature.shape[0]
    day = np.arange(n).reshape(-1, *([1] * (temperature.ndim - 1)))
    r1, veg_start = biofix_index, max(0, biofix_index - WINDOW)
    in_veg = (day >= veg_start) & (day < r1)
    in_rep = (day >= r1) & (day < r1 + WINDOW)

    known = np.nan_to_num(precip)  # missing days count as no rain, and are counted
    # Days missing here, or filled with no rain by the runner (D45)
    missing = ~np.isfinite(precip) | np.asarray(inputs.get("precipitation_sum_estimated", False), dtype=bool)
    before_series = WINDOW - (r1 - veg_start)  # days of the window before the series starts are missing too

    veg_total = known[veg_start:r1].sum(axis=0) if r1 > veg_start else np.full(precip.shape[1:], np.nan)
    veg_running = np.cumsum(np.where(in_veg, known, 0), axis=0)
    precipitation_vegetative = np.where(day < veg_start, np.nan, np.where(in_veg, veg_running, veg_total))

    temperature_rep = _cumulative_mean(np.where(in_rep, temperature, np.nan))
    rep_elapsed = np.cumsum(in_rep, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        rep_running = np.cumsum(np.where(in_rep, known, 0), axis=0)
        precipitation_rep = np.where(rep_elapsed > 0, rep_running, np.nan)  # so far, not prorated

    veg_missing = missing[veg_start:r1].sum(axis=0) + before_series
    days_missing = np.where(
        day < veg_start,
        np.nan,
        np.where(
            in_veg,
            np.cumsum(in_veg & missing, axis=0) + before_series,
            veg_missing + np.cumsum(in_rep & missing, axis=0),
        ),
    )
    final = r1 + WINDOW - 1  # the last day of the window from R1
    if final < n:
        complete = incidence(temperature_rep[final], veg_total, precipitation_rep[final])
        incidence_final = np.where(day >= final, complete, np.nan)
    else:
        incidence_final = np.full(temperature.shape, np.nan)
    return {
        "incidence": incidence_final,
        "temperature_mean_reproductive": temperature_rep,
        "precipitation_vegetative": precipitation_vegetative,
        "precipitation_reproductive": precipitation_rep,
        "precipitation_days_missing": days_missing,
    }


def explore(temperature_reproductive: float, precipitation_vegetative: float, precipitation_reproductive: float):
    return {
        "incidence": float(incidence(temperature_reproductive, precipitation_vegetative, precipitation_reproductive))
    }


def _cumulative_mean(values: np.ndarray) -> np.ndarray:
    """Mean of the values so far, NaN until the first (the tool's `cummean_na`)."""
    count = np.cumsum(np.isfinite(values), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, np.cumsum(np.nan_to_num(values), axis=0) / count, np.nan)
