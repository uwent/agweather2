"""The root maggots (part H, H1): cabbage and onion maggot rebuilt on NEWA's models (D95), checked against NEWA's
tables and their sources; seedcorn maggot's first emergence against Olaya-Arenas et al. 2024 and Cho et al. 2025."""

import numpy as np
import pytest

from agmodels.degree_days import degree_days_average
from agmodels.insects import cabbage_maggot, onion_maggot, seedcorn_maggot
from agmodels.phenology import DD_STEP, PhenologyModel, curves, dd_grid, generation_densities

X = dd_grid()


def shares(insect) -> list[np.ndarray]:
    """Each generation's adult flight, cumulative (0 to 1) on the degree-day grid."""
    return [np.cumsum(d) * DD_STEP for d in generation_densities(insect=insect, stage=insect.life_stages[0])]


def dd_at(cumulative: np.ndarray, share: float) -> float:
    return float(np.interp(share, cumulative, X))


def window_edges(insect, key: str) -> list[tuple[float, float]]:
    table = curves(insect)[key]
    edges = np.flatnonzero(np.diff(np.r_[0, table, 0]) != 0)
    return [(float(X[a]), float(X[b - 1])) for a, b in zip(edges[::2], edges[1::2], strict=True)]


# --- Cabbage maggot ------------------------------------------------------------------------------------------------

CM = cabbage_maggot.INSECT
# Jyoti, Shelton and Barnard 2003's spring emergence (°C·d above 4 °C, upstate New York 1999–2000) × 1.8, and
# NEWA's table of the same (DD40, simple average, from January 1)
JYOTI_F = {0.10: 176.6 * 1.8, 0.25: 204.2 * 1.8, 0.50: 251.3 * 1.8, 0.75: 297.6 * 1.8, 0.95: 390.9 * 1.8}
NEWA_CM = {0.25: 366, 0.50: 452, 0.75: 547, 0.95: 697}
NEWA_CM_PEAKS = (1261, 2176, 3014)


def test_cabbage_maggot_is_newas_method():
    assert (CM.dd_method, CM.base_f, CM.upper_f, CM.biofix) == ("average", 40, None, "01-01")
    assert degree_days_average(np.array([30.0]), np.array([60.0]), base=40, upper=None)[0] == 5


def test_cabbage_maggots_spring_flight_follows_newas_table_and_jyoti_2003():
    spring = shares(CM)[0]
    for share, dd in NEWA_CM.items():
        assert abs(np.interp(dd, X, spring) - share) <= 0.01, share  # within a percentage point
    for share, dd in JYOTI_F.items():
        assert abs(dd_at(spring, share) - dd) <= 15, share
    # NEWA's first emergence (288, Jyoti's 160.7 °C·d) at about 5 % of the flight
    assert np.interp(288, X, spring) == pytest.approx(0.059, abs=0.005)


def test_cabbage_maggots_later_flights_follow_newas_peaks_and_stop_at_four():
    flights = shares(CM)
    assert len(flights) == 4
    for g, peak in enumerate(NEWA_CM_PEAKS, start=1):
        assert abs(dd_at(flights[g], 0.5) - peak) <= 45, g
    # generation time 850 against NEWA's 809, 915 and 838 between peaks
    gaps = np.diff([dd_at(f, 0.5) for f in flights])
    assert np.all(np.abs(gaps - 850) <= 5)


def test_cabbage_maggot_generation_against_eckenrode_and_chapman():
    """Eckenrode and Chapman 1971: 1,112 DD43 from egg to the first egg peak at 69.8 °F (41.5 days); 1972: 1,176
    DD43 between Wisconsin flights in the field. NEWA's 850 DD40 is shorter (a difference kept, D95): at a summer
    mean of 70 °F it's 28 days, against their 41–45."""
    days_newa = CM.generation_dd / (70 - 40)  # type: ignore[operator]
    days_lab = 1112 / (69.8 - 43)
    days_field = 1176 / (70 - 43)
    assert 27 < days_newa < 30 and 41 < days_lab < 42 and 43 < days_field < 44.5


def test_cabbage_maggot_larvae_follow_the_flight():
    larvae = CM.life_stages[1]
    flight = shares(CM)[0]
    entered = np.interp(X - larvae.lag, X, flight, left=0)  # type: ignore[union-attr]
    # half the spring flight's larvae are feeding by about 700 DD40, three weeks after the flight's 50 %
    assert 680 <= dd_at(entered, 0.5) <= 710


def test_cabbage_maggot_protection_window_runs_from_first_emergence_to_95_percent():
    windows = window_edges(CM, "window_protect_seedlings_and_transplants_during_fly_flight")
    assert len(windows) == 4
    first, last = windows[0]
    assert abs(first - 288) <= 6 and abs(last - 697) <= 6  # NEWA's first emergence and 95 %


# --- Onion maggot --------------------------------------------------------------------------------------------------

OM = onion_maggot.INSECT
NEWA_OM = ((390, 735), (1218, 1752), (2415, 2975))  # first emergence and peak (50 %) of each flight, DD40


def test_onion_maggot_is_newas_method_with_three_flights():
    assert (OM.dd_method, OM.base_f, OM.upper_f, OM.biofix) == ("average", 40, None, "01-01")
    assert len(shares(OM)) == 3


def test_onion_maggots_spring_flight_is_newas():
    spring = shares(OM)[0]
    assert abs(dd_at(spring, 0.05) - 390) <= 3
    assert abs(dd_at(spring, 0.50) - 735) <= 3
    # before the next flight's first flies (NEWA's 1,218)
    assert dd_at(spring, 0.95) < 1218


def test_onion_maggots_later_flights_against_newa_and_eckenrode_1975():
    flights = shares(OM)
    peaks = [dd_at(f, 0.5) for f in flights]
    assert abs(peaks[1] - NEWA_OM[1][1]) <= 85 and abs(peaks[2] - NEWA_OM[2][1]) <= 50
    # first flies (5 %) of the later flights within 150 of NEWA's
    for g in (1, 2):
        assert abs(dd_at(flights[g], 0.05) - NEWA_OM[g][0]) <= 150, g
    # Eckenrode et al. 1975, Table 2: spring 50 % catch averaged 712; the next two came 1,187 and 1,257 later
    assert abs(peaks[0] - 712) <= 25
    assert all(abs(gap - 1222) <= 130 for gap in np.diff(peaks))


def test_onion_maggot_larvae_from_liu_1982():
    larvae = OM.life_stages[1]
    # pre-oviposition 103 and egg 50 °C·d, larva 287 °C·d (Ritcey and McEwen, in Liu et al. 1982)
    assert larvae.lag == pytest.approx((103 + 50) * 1.8, abs=1)  # type: ignore[union-attr]
    assert larvae.duration == pytest.approx(287 * 1.8, abs=1)  # type: ignore[union-attr]


def test_onion_maggot_protection_window_opens_at_first_emergence():
    windows = window_edges(OM, "window_protect_onion_seedlings_during_fly_flight")
    assert abs(windows[0][0] - 390) <= 3
    assert len(windows) == 3


def test_every_generation_weighs_alike():
    """NEWA calls each maggot's spring flight the most damaging; the models still weigh generations alike (D37)."""
    for insect in (CM, OM):
        model = PhenologyModel(insect=insect, summary="")
        flights = shares(insect)
        spring_peak = model.explore(dd_total=dd_at(flights[0], 0.5))["activity_adult_flight"]
        assert spring_peak == pytest.approx(1, abs=0.05)
        assert all(s.weight == 1 for s in insect.life_stages)


# --- Seedcorn maggot -----------------------------------------------------------------------------------------------


def test_seedcorn_maggots_first_flight_starts_within_new_yorks_first_emergence():
    """Olaya-Arenas et al. 2024: first emergence at a mean 68 DD (°F, average above 39 °F from January 1) in 2023;
    Cho et al. 2025: 52 to 197 (mean 98) at 29 sites, 2023–2024, also °F·d (98 is reached in mid-March in New York,
    their mean date; NEWA reads the same numbers as °C·d, about 95–355 °F·d)."""
    flight = seedcorn_maggot.INSECT.life_stages[0]
    assert 52 <= flight.start <= 98  # type: ignore[union-attr]
    spring = shares(seedcorn_maggot.INSECT)[0]
    # our 10 % and 50 % (about 201 and 345) fall inside NEWA's first-emergence window read as °C·d (95–355 °F·d)
    assert dd_at(spring, 0.10) >= 53 * 1.8 and dd_at(spring, 0.50) <= 197.5 * 1.8
