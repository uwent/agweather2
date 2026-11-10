"""Winter chill for fruit trees from hourly temperature (D76): chill hours, Utah chill units, and the Dynamic model's
chill portions. Pure functions on hours (axis 0), a point's (hours,) or the grid's (hours, y, x).

- **Chill hours** (Bennett 1949, as chillR counts them): hours with 0 °C ≤ T ≤ 7.2 °C (32–45 °F).
- **Utah chill units** (Richardson, Seeley and Walker 1974): each hour weighted by temperature, warm hours counting
  against the total: 0 at or below 1.4 °C, 0.5 to 2.4 °C, 1 to 9.1 °C, 0.5 to 12.4 °C, 0 to 15.9 °C, −0.5 to
  18 °C, −1 above (each range's top included, as chillR's `Utah_Model` at 0.1 °C, the paper's precision).
- **Chill portions** (the Dynamic model: Fishman, Erez and Couvillon 1987; Erez et al. 1990): chill builds up as an
  intermediate that warm hours can still undo, and once it reaches a critical amount a share of it becomes a
  permanent portion. The intermediate carries from hour to hour across days, so a day's portions depend on the
  season before it: `dynamic` takes the state at the start and returns it at the end. Constants and steps as
  chillR's `Dynamic_Model` (Luedeling), including its kelvin as °C + 273; a parity test runs chillR's own code.

A count or sum over a day with any hour missing is missing (D25). The Dynamic model skips a missing hour instead:
the intermediate is held and nothing accrues, and the hour is counted, so a season's total says how many hours it
went without (D76).
"""

import numpy as np

from agmodels.spec import Citation

CITATIONS = (
    Citation(
        text="Bennett, J. P. (1949). Temperature and bud rest period. California Agriculture 3(11), 9, 12.",
    ),
    Citation(
        text="Richardson, E. A., Seeley, S. D. and Walker, D. R. (1974). A model for estimating the completion of rest "
        "for 'Redhaven' and 'Elberta' peach trees. HortScience 9(4), 331–332.",
        doi="10.21273/HORTSCI.9.4.331",
    ),
    Citation(
        text="Fishman, S., Erez, A. and Couvillon, G. A. (1987). The temperature dependence of dormancy breaking in "
        "plants: mathematical analysis of a two-step model involving a cooperative transition. Journal of Theoretical "
        "Biology 124(4), 473–483.",
        doi="10.1016/S0022-5193(87)80221-7",
    ),
    Citation(
        text="Erez, A., Fishman, S., Linsley-Noakes, G. C. and Allan, P. (1990). The dynamic model for rest completion "
        "in peach buds. Acta Horticulturae 276, 165–174.",
        doi="10.17660/ActaHortic.1990.276.18",
    ),
    Citation(
        text="Luedeling, E. chillR: Statistical methods for phenology analysis in temperate fruit trees. R package "
        "(the reference implementation of all three).",
        url="https://cran.r-project.org/package=chillR",
    ),
)

CHILL_LOW_C = 0.0
CHILL_HIGH_C = 7.2

# Utah weights by the top of each range (°C, inclusive), chillR's step table
UTAH_TOPS_C = np.array([1.4, 2.4, 9.1, 12.4, 15.9, 18.0])
UTAH_WEIGHTS = np.array([0.0, 0.5, 1.0, 0.5, 0.0, -0.5, -1.0])

# The Dynamic model's constants (Fishman et al. 1987; chillR's defaults)
E0 = 4153.5
E1 = 12888.8
A0 = 139500.0
A1 = 2.567e18
SLOPE = 1.6
TF = 277.0
KELVIN = 273.0  # chillR's conversion; kept for parity (273.15 moves a season's total by under 0.1%)


def _celsius(temperature_c: np.ndarray) -> np.ndarray:
    """Temperatures as float64 to 0.01 °C: they're stored to 0.1 °C, so many fall exactly on a range's edge (7.2,
    9.1), and a float32 read (9.1000004) would land past it where a float64 one doesn't."""
    return np.round(np.asarray(temperature_c, dtype=np.float64), 2)


def chill_hours(temperature_c: np.ndarray, low_c: float = CHILL_LOW_C, high_c: float = CHILL_HIGH_C) -> np.ndarray:
    """Hours with `low_c` ≤ T ≤ `high_c` (by default 0–7.2 °C); missing if any hour is."""
    t = _celsius(temperature_c)
    return np.where(np.isnan(t).any(axis=0), np.nan, ((t >= low_c) & (t <= high_c)).sum(axis=0))


def utah_weights(temperature_c: np.ndarray) -> np.ndarray:
    """Each hour's Utah chill units (NaN where the hour is)."""
    t = _celsius(temperature_c)
    weights = UTAH_WEIGHTS[np.searchsorted(UTAH_TOPS_C, np.nan_to_num(t), side="left")]
    return np.where(np.isnan(t), np.nan, weights)


def utah_units(temperature_c: np.ndarray) -> np.ndarray:
    """The hours' Utah chill units summed (negative when warm hours outweigh); missing if any hour is."""
    w = utah_weights(temperature_c)
    return np.where(np.isnan(w).any(axis=0), np.nan, np.nansum(w, axis=0))


def _rates(temperature_c: np.ndarray):
    """(xs, e^−k1, ξ): the hour's equilibrium intermediate, its decay factor, and the share of a completed
    intermediate fixed as a portion."""
    tk = np.asarray(temperature_c, dtype=float) + KELVIN
    sr = np.exp(SLOPE * TF * (tk - TF) / tk)
    xi = sr / (1 + sr)
    xs = (A0 / A1) * np.exp((E1 - E0) / tk)
    decay = np.exp(-A1 * np.exp(-E1 / tk))
    return xs, decay, xi


def dynamic(temperature_c: np.ndarray, state: np.ndarray | float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The Dynamic model over consecutive hours (axis 0) from `state`, the intermediate left by the hour before
    (0 at a season's start): (portions per hour, the intermediate after the last hour, missing hours). In each hour
    the intermediate moves toward the hour's equilibrium; once it reaches 1, the share ξ of it becomes portions and
    the rest carries on. A missing hour holds the intermediate and adds nothing."""
    t = np.asarray(temperature_c, dtype=float)
    shape = t.shape[1:]
    s = np.broadcast_to(np.asarray(state, dtype=float), shape).copy()
    portions = np.zeros(t.shape)
    xs, decay, xi = _rates(np.nan_to_num(t))
    for h in range(t.shape[0]):
        known = ~np.isnan(t[h])
        x = xs[h] - (xs[h] - s) * decay[h]
        done = known & (x >= 1)
        portions[h] = np.where(done, x * xi[h], 0.0)
        s = np.where(known, np.where(done, x * (1 - xi[h]), x), s)
    missing = np.isnan(t).sum(axis=0).astype(float)
    return portions, s, missing
