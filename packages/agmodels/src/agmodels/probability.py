"""Helpers for the logistic field-crop models (the Crop Risk Tool's `logistic`, `attenuate_prob`,
`risk_from_prob`)."""

import numpy as np

from agmodels.accumulate import rolling_mean


def logistic(logit) -> np.ndarray:
    return 1 / (1 + np.exp(-np.asarray(logit, dtype=float)))


def attenuate_for_cold(probability, temperature_c) -> np.ndarray:
    """Scales a spore probability down as the 21-day mean minimum falls below 10 °C, to 0 at 0 °C (the models
    were fitted in season; without it they report high risk all winter)."""
    p, t = np.asarray(probability, dtype=float), np.asarray(temperature_c, dtype=float)
    return np.where(t > 10, p, np.where(t > 0, p * t / 10, np.where(np.isnan(t), np.nan, 0.0)))


def risk_level(probability, low: float, moderate: float, high: float) -> np.ndarray:
    """0–3 (PROBABILITY_LEVELS) from a probability against thresholds in percent: [0, low) very low, [low,
    moderate) low, [moderate, high) moderate, [high, 100] high."""
    p = np.asarray(probability, dtype=float) * 100
    level = (p >= low).astype(float) + (p >= moderate) + (p >= high)
    return np.where(np.isnan(p), np.nan, level)


def moving_mean(values, days: int) -> np.ndarray:
    """A trailing moving mean over the days that have values (partial at the start), as the tool's `roll_mean`."""
    return rolling_mean(np.asarray(values, dtype=float), days, 0)
