"""Livestock heat stress from hourly weather (D77): the Temperature Humidity Index and the Cattle Comfort Index.
Pure functions, on a point's hours or the grid's alike.

- **THI** (NRC 1971): THI = (1.8 T + 32) − (0.55 − 0.0055 RH)(1.8 T − 26), with T in °C and RH in percent. Dairy
  cattle's milk yield begins to fall at a THI of 68 (Zimbelman et al. 2009) and stress is commonly counted from 72
  (Armstrong 1994); the daily features count hours at or above both.
- **Cattle Comfort Index** (Mader, Johnson and Gaughan 2010, their comprehensive climate index): an apparent
  temperature (°C), air temperature adjusted for humidity (eq. 1), wind (eq. 2) and solar radiation (eq. 3),
  developed over −30 to 45 °C. Checked against the paper's worked values (37.9, −44.1 and 67.7 °C). The paper's
  wind came from Nebraska feedlot and High Plains network stations (3 m); ours is the analysis's 10 m wind, brought
  to 2 m by FAO-56's log profile (`agmodels.weather.wind_speed_2m`), within about 6% of 3 m.
"""

import numpy as np

from agmodels.spec import Citation
from agmodels.weather import wind_speed_2m

CITATIONS = (
    Citation(
        text="National Research Council (1971). A Guide to Environmental Research on Animals. National Academy of "
        "Sciences, Washington, DC.",
    ),
    Citation(
        text="Zimbelman, R. B., Rhoads, R. P., Rhoads, M. L., Duff, G. C., Baumgard, L. H. and Collier, R. J. "
        "(2009). A re-evaluation of the impact of temperature humidity index (THI) and black globe humidity index "
        "(BGHI) on milk production in high producing dairy cows. Proceedings of the Southwest Nutrition and "
        "Management Conference, 158–169.",
    ),
    Citation(
        text="Armstrong, D. V. (1994). Heat stress interaction with shade and cooling. Journal of Dairy Science "
        "77(7), 2044–2050.",
        doi="10.3168/jds.S0022-0302(94)77149-6",
    ),
    Citation(
        text="Mader, T. L., Johnson, L. J. and Gaughan, J. B. (2010). A comprehensive index for assessing "
        "environmental stress in animals. Journal of Animal Science 88(6), 2153–2165.",
        doi="10.2527/jas.2009-2586",
    ),
)

THI_MILD_DAIRY = 68.0
THI_STRESS = 72.0


def thi(temperature_c, rh_percent) -> np.ndarray:
    """The Temperature Humidity Index (NRC 1971), unitless."""
    t, rh = np.asarray(temperature_c, dtype=float), np.asarray(rh_percent, dtype=float)
    return (1.8 * t + 32) - (0.55 - 0.0055 * rh) * (1.8 * t - 26)


def cci_from_2m(temperature_c, rh_percent, wind_2m_m_s, shortwave_w_m2) -> np.ndarray:
    """Mader et al.'s comprehensive climate index (°C) from wind at animal height (m/s)."""
    t = np.asarray(temperature_c, dtype=float)
    rh = np.asarray(rh_percent, dtype=float)
    ws = np.maximum(np.asarray(wind_2m_m_s, dtype=float), 0.0)
    rad = np.maximum(np.asarray(shortwave_w_m2, dtype=float), 0.0)
    humidity = np.exp(0.00182 * rh + 1.8e-5 * t * rh) * (0.000054 * t**2 + 0.00192 * t - 0.0246) * (rh - 30)
    exponent = (1 / (2.26 * ws + 0.23)) ** 0.45 * (
        2.9 + 1.14e-6 * ws**2.5 - np.log((2.26 * ws + 0.33) ** -2) / np.log(0.3)
    )
    wind = -6.56 / np.exp(exponent) - 0.00566 * ws**2 + 3.33
    radiation = 0.0076 * rad - 0.00002 * rad * t + 0.00005 * t**2 * np.sqrt(rad) + 0.1 * t - 2
    return t + humidity + wind + radiation


def cci(temperature_c, rh_percent, wind_speed_10m_m_s, shortwave_w_m2) -> np.ndarray:
    """The Cattle Comfort Index (°C) from the 10 m wind the archive stores."""
    return cci_from_2m(temperature_c, rh_percent, wind_speed_2m(wind_speed_10m_m_s), shortwave_w_m2)
