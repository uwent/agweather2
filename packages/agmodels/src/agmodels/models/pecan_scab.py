"""Pecan scab hours and the spray decision: hours with RH at or above 90% and temperature at or above 70 °F, since
March 1 or the last spray, against the Oklahoma Mesonet's threshold for the variety and its waiting period.

The Oklahoma Mesonet's Pecan Scab Advisor (March 1 to August 31): spraying is recommended once 10 scab hours have
accumulated for highly susceptible varieties, 20 for moderately and 30 for low susceptibility, and it has been 30 days
since March 1 or 5 to 14 days (the grower's choice) since the last fungicide application. Options: `susceptibility`
(the threshold) and `protection_days` (the wait after a spray); the wait is 30 days when the count starts on March 1
(the biofix's default), `protection_days` when it starts on a spray. Risk, three levels: Low below half the threshold;
Moderate from half (LSU's 50–90% caution), or at the threshold within the wait; High when the threshold is reached
and the wait has passed (spray advised). Scab hours are counted from hourly values as a daily feature
(`hours_rh_over_90_temperature_over_70f`, the calendar day), so the model itself reads days.

Ported from the Crop Risk Tool (`build_pecan_scab`), whose code counts RH at or above 92% and temperature above
21.1 °C, where its docs and the Mesonet say 90% and 70 °F: v2 follows the Mesonet (intended difference). The tool's
92% was Ben's trial-and-error adjustment to match the Mesonet's scab hours on Open-Meteo's weather (2026-11-19); v2
corrects its own weather separately, so it counts at the Mesonet's 90% (at Okmulgee in 2025 Open-Meteo ran drier than
the Mesonet's station, so 92% moved the wrong way: audit round 2). 0.1 rated the total against all three thresholds
and left the waits out; 0.2 models the advisor's decision (audit round 2, `tmp/crt-model-audit-2-cotton-pecan-rye.md`).
0.3 (D100): the scab hour's 90% is counted at 88% (D50's `STATION_RH_90_AS_GRIDDED`), and Open-Meteo's RH is no
longer mapped by D51 outside the Upper Midwest: at five Oklahoma Mesonet stations, March–August 2023–2025, raw
Open-Meteo at 90% counted 0.68 of the stations' hours, matched them at 87.5–88.2%, and at 88% gave the advisor's
spray count (10.0 a season against 9.7); D51's map had made spring 2–4 times too humid there (1.12 times the hours at
90%, thresholds reached a median 15 days early). `tmp/pecan-check/report.md`.
Southern, beta: run at points through Open-Meteo until the box reaches the South.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import number_option
from agmodels.ingredients import Accumulation, Ingredient, finished, with_accumulations
from agmodels.spec import Biofix, Change, Check, Citation, ExplorerInput, Input, ModelSpec, Option, Quantity, Risk

THRESHOLDS = {"high": 10, "moderate": 20, "low": 30}  # spray thresholds (scab hours) by variety susceptibility
MARCH_1_WAIT = 30  # days from March 1 before a first spray is advised (susceptible growth starts)
SUSCEPTIBILITY = Option(
    name="susceptibility",
    label="Variety susceptibility",
    choices=(
        ("high", "High (10 hours): Desirable, Pawnee, Wichita"),
        ("moderate", "Moderate (20 hours): Caddo, Kiowa, Stuart"),
        ("low", "Low (30 hours): Excel, Kanza, Lakota"),
    ),
    default="high",
)
PROTECTION = Option(
    name="protection_days",
    label="Days a spray protects",
    choices=tuple((str(d), f"{d} days") for d in (5, 7, 10, 14)),
    default="14",
)
PECAN_STATES = ("AL", "AR", "AZ", "CA", "FL", "GA", "KS", "LA", "MO", "MS", "NC", "NM", "OK", "SC", "TN", "TX")

SPEC = ModelSpec(
    id="pecan-scab",
    name="Pecan scab hours",
    group="disease",
    version="0.3",
    status="beta",
    summary="Hours warm (70 °F or more) and humid (RH 90% or more) since March 1 or the last fungicide spray, and whether a spray is advised: the total has reached the threshold for your variety's susceptibility and the waiting period after March 1 or the last spray has passed.",
    topics=("pecan-scab",),
    crops=("pecan",),
    checks=(
        Check(
            kind="system",
            against="The Crop Risk Tool, which this model replaces, on its recorded 2025 weather at one Wisconsin location, used only to test the arithmetic",
            result="Counted at the tool's own thresholds (92 percent humidity and above 21.1 °C), our daily and running scab hours match the tool's on all 365 days. We count at the Oklahoma Mesonet's 90 percent and 70 °F, as the tool's documentation says, with the 90 percent read as 88 percent on our weather (as a station measures it), so more hours count.",
            report="docs/validation/models/pecan-scab.md#against-the-crop-risk-tool",
        ),
    ),
    citations=(
        Citation(
            text="Oklahoma Mesonet: Pecan Scab Advisor.",
            url="https://www.mesonet.org/agriculture/horticulture/pecan/pecan-scab-advisor",
        ),
        Citation(text="University of Arkansas: Pecan scab.", url="https://pecanscab.uada.edu/"),
        Citation(
            text="Payne, A. F. and Smith, D. L. (2012). Development and evaluation of two pecan scab prediction models. Plant Disease 96, 1358–1364.",
            doi="10.1094/PDIS-03-11-0202-RE",
        ),
    ),
    inputs=(
        Input(
            name="hours_rh_over_90_temperature_over_70f",
            label="Scab hours (RH ≥ 90% and ≥ 70 °F)",
            unit="hour",
            description="Calendar day",
        ),
    ),
    outputs=(
        Quantity(name="scab_hours_total", label="Scab hours since March 1 or the last spray", unit="hour"),
        Quantity(name="scab_hours", label="Scab hours", unit="hour"),
        Quantity(name="scab_hours_14_day", label="Scab hours in the last 14 days", unit="hour"),
        Quantity(name="days_since_start", label="Days since March 1 or the last spray", unit="day"),
        Quantity(
            name="wait_days_left",
            label="Days left in the waiting period",
            unit="day",
            description="Days until 30 days after March 1, or until the chosen protection period after the last spray ends; 0 once it has passed",
        ),
    ),
    risk=Risk(
        levels=("Low", "Moderate", "High"),
        criteria="Scab hours since March 1 or the last spray, against the threshold for the variety's susceptibility (10 hours for high, such as Desirable, Pawnee and Wichita; 20 for moderate, such as Caddo, Kiowa and Stuart; 30 for low, such as Excel, Kanza and Lakota): Low below half the threshold; Moderate from half, or at the threshold while the waiting period (30 days after March 1, or the chosen 5 to 14 days after a spray) lasts; High, spray advised, at the threshold once the waiting period has passed.",
    ),
    explorer=(
        ExplorerInput(
            name="scab_hours_total",
            label="Scab hours since March 1 or the last spray",
            unit="hour",
            minimum=0,
            maximum=60,
            step=1,
            default=10,
        ),
        ExplorerInput(
            name="wait_days_left",
            label="Days left in the waiting period",
            unit="day",
            minimum=0,
            maximum=30,
            step=1,
            default=0,
        ),
    ),
    explorer_outputs=(
        Quantity(
            name="risk_high",
            label="Risk level, highly susceptible varieties",
            unit="index",
            description="Index into the risk levels",
        ),
        Quantity(
            name="risk_moderate",
            label="Risk level, moderately susceptible varieties",
            unit="index",
            description="Index into the risk levels",
        ),
        Quantity(
            name="risk_low",
            label="Risk level, varieties of low susceptibility",
            unit="index",
            description="Index into the risk levels",
        ),
    ),
    sweep={
        "scab_hours_total": tuple(float(h) for h in range(0, 41)),
        "wait_days_left": (0.0, 1.0, 14.0, 30.0),
    },
    options=(SUSCEPTIBILITY, PROTECTION),
    context=("day_of_year", "year"),
    region=PECAN_STATES,
    season=("03-01", "08-31"),
    biofix=Biofix(default="03-01", label="March 1, or the last fungicide application"),
    ingredients=(Ingredient(name="scab_hours", unit="hour"),),
    accumulations=(
        Accumulation(name="scab_hours_total", of="scab_hours"),
        Accumulation(name="scab_hours_14_day", of="scab_hours", how="sum", days=14),
    ),
    changelog=(
        Change(version="0.1", date="2026-10-28", note="Ported from the Crop Risk Tool, with the Mesonet's thresholds."),
        Change(
            version="0.2",
            date="2026-11-19",
            note="The Mesonet's spray decision: options for the variety's susceptibility (10, 20 or 30 hours) and the days a spray protects (5, 7, 10 or 14); a wait of 30 days from March 1 or the protection period from a spray; three levels (Low, Moderate, High = spray advised) in place of four steps at 10, 20 and 30 hours. New outputs: the days since March 1 or the last spray, and the days left in the wait. Cites Payne and Smith 2012.",
        ),
        Change(
            version="0.3",
            date="2026-11-19",
            note="Scab hours are counted at 88% humidity on our weather, which matches the Oklahoma Mesonet stations' 90%: at five stations in pecan country, March to August 2023 to 2025, Open-Meteo at 90% counted about two-thirds of the stations' hours, and at 88% it matched them and gave the same number of sprays. Open-Meteo's humidity is no longer adjusted by the Wisconsin-fitted correction here, which had made spring too humid.",
        ),
    ),
)


def ingredients(inputs: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"scab_hours": np.asarray(inputs["hours_rh_over_90_temperature_over_70f"], dtype=float)}


def finish(values: Mapping[str, np.ndarray], **options: str) -> dict[str, np.ndarray]:
    total = np.asarray(values["scab_hours_total"], dtype=float)
    found = {name: values[name] for name in ("scab_hours_total", "scab_hours", "scab_hours_14_day")}
    days = _days_since_start(values, shape=total.shape)
    wait = np.where(_from_march_1(values, ndim=total.ndim), MARCH_1_WAIT, number_option(options, PROTECTION))
    return found | {"days_since_start": days, "wait_days_left": np.maximum(wait - days, 0.0)}


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    return finished(
        accumulations=SPEC.accumulations,
        values=ingredients(inputs),
        inputs=inputs,
        biofix_index=biofix_index,
        finish=finish,
        options=options,
    )


def risk(outputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> np.ndarray:
    total = with_accumulations(outputs, SPEC.accumulations, biofix_index)["scab_hours_total"]
    threshold = _threshold(options.get(SUSCEPTIBILITY.name, SUSCEPTIBILITY.default))
    return spray_level(scab_hours_total=total, wait_days_left=outputs["wait_days_left"], threshold=threshold)


def spray_level(*, scab_hours_total, wait_days_left, threshold: float) -> np.ndarray:
    """0 Low (below half the threshold), 1 Moderate (from half, or at the threshold within the wait), 2 High (at
    the threshold with the wait passed: spray advised); NaN where the total is missing, or it's at the threshold and
    the wait is unknown."""
    total = np.asarray(scab_hours_total, dtype=float)
    left = np.asarray(wait_days_left, dtype=float)
    reached = total >= threshold
    with np.errstate(invalid="ignore"):
        level = np.where(reached, np.where(left > 0, 1.0, 2.0), np.where(total >= threshold / 2, 1.0, 0.0))
    return np.where(np.isnan(total) | (reached & np.isnan(left)), np.nan, level)


def explore(scab_hours_total: float, wait_days_left: float) -> dict[str, float]:
    return {
        f"risk_{name}": float(
            spray_level(scab_hours_total=scab_hours_total, wait_days_left=wait_days_left, threshold=threshold)
        )
        for name, threshold in THRESHOLDS.items()
    }


def _threshold(susceptibility: str) -> float:
    if susceptibility not in THRESHOLDS:
        raise ValueError(f"susceptibility must be one of {', '.join(THRESHOLDS)}, got {susceptibility!r}")
    return float(THRESHOLDS[susceptibility])


def _days_since_start(values: Mapping[str, np.ndarray], shape: tuple[int, ...]) -> np.ndarray:
    """Days from the biofix (March 1 or the last spray) to each day, within its calendar year; NaN before the
    biofix or without the day of year."""
    if "day_of_year" not in values or "biofix_day_of_year" not in values:
        return np.full(shape, np.nan)
    days = _along_time(values["day_of_year"], ndim=len(shape)) - np.asarray(values["biofix_day_of_year"], dtype=float)
    return np.broadcast_to(np.where(days >= 0, days, np.nan), shape).copy()


def _from_march_1(values: Mapping[str, np.ndarray], ndim: int) -> np.ndarray:
    """Whether the count starts on March 1 (day 60, 61 in a leap year), the biofix's default, rather than on a spray.
    Without the dates it's taken to (the 30-day wait)."""
    if "biofix_day_of_year" not in values or "year" not in values:
        return np.asarray(True)
    year = _along_time(values["year"], ndim=ndim)
    march_1 = 60.0 + (((year % 4 == 0) & (year % 100 != 0)) | (year % 400 == 0))
    return np.asarray(values["biofix_day_of_year"], dtype=float) == march_1


def _along_time(v, ndim: int) -> np.ndarray:
    """A per-day series (time on axis 0) shaped to broadcast over a grid of `ndim` dimensions."""
    a = np.asarray(v, dtype=float)
    return a.reshape(a.shape + (1,) * (ndim - a.ndim)) if a.ndim else a
