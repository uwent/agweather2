"""Soybean growth stages from planting, for any maturity group, from temperature and day length (SOYDEV).

Setiyono et al. (2007), fitted at Lincoln, Nebraska: each phase's progress adds a daily rate Rmax·f(T)·f(P) until it
reaches 1, with beta functions of the day's mean temperature (Wang and Engel 1998) and of day length (after Yin et
al. 1995). The parameters come from the maturity group through the paper's generalized relations (its option (c),
RMSE 3.6 days over V1, R1, R3.5, R5 and R7 for 21 cultivars of MG 0.8–4.2 and several sowing dates):

- sowing to emergence: radicle at 40 °C·d above 5 °C, then the hypocotyl grows as 5[1 − exp(−(0.0128 ATT)^4.57)] cm
  (from STICS) until it's 0.6 cm past the seeding depth;
- emergence to V1 (Rmax 0.1194) and to VC, the paper's V0 (0.1990), on temperature (5, 31.5, 45 °C);
- VC to R0, floral induction, on day length to civil twilight (sun above −6°), Rmax 0.25, with the optimum and
  critical day lengths from the maturity group (Fig. 4, from Cregan and Hartwig 1984);
- R0 to R1 on temperature (7, 32.4, 41.9 °C), Rmax from the maturity group (Fig. 11a);
- R1 to R5 on temperature (3.6, 25, 40 °C) and day length to sunrise and sunset (−0.83°; optimum 12 h, critical 18 h),
  Rmax 0.075 − 0.0085 MG (Fig. 11c); R3.5 at 0.613 of the way (Fig. 11b);
- R1 to R7 on temperature (0, 21.5, 38.7 °C) and the same day length, Rmax from the maturity group (Fig. 11d);
- main-stem nodes after V1 at up to rNA,max·f(T) a day (7.6, 31, 40 °C), slowing after VΔ (part of the way from R1
  to R5) by the indeterminate chronology function (A, B, C = 1.149, 0.1, 0.09) until it reaches 0. rNA,max and VΔ
  vary with day length at emergence and are read from Fig. 13's indeterminate panel (the paper gives points, not a
  fit); semi-determinate varieties aren't offered.

Table 2 lists each phase's critical and optimum day lengths in the order "Pcrt Popt" as 11 and 25 h (V0–R0) and 12
and 18 h (R1 phases); the photoperiod function needs the optimum below the critical, and Figs. 4 and 12 show
Popt ≈ 11–12 h and Pcrt ≈ 18–25 h, so the pairs are read as optimum, critical.

Stages are Fehr and Caviness's. The model predicts VE, VC, V1, the V-stages, R1, R3.5, R5 and R7; R2, R3 and R4 are
placed by spacing the R-stages evenly on the R1–R5 progress either side of R3.5, and R6 halfway from R5 to R7 on the
R1–R7 progress (flagged as estimated). R8 isn't modelled. Once flowering starts the stage is the R-stage; nodes
keep their own output. Maturity groups below 0.8 extrapolate the fits.
"""

from collections.abc import Mapping

import numpy as np

from agmodels.crops import CropStage, number_option
from agmodels.spec import Biofix, Change, Citation, ExplorerInput, ModelSpec, Option, Quantity
from agmodels.weather import day_length_hours

RADICLE_CD = 40.0
HYPOCOTYL_MAX_CM, HYPOCOTYL_A, HYPOCOTYL_B = 5.0, 0.0128, 4.57
EMERGED_PAST_DEPTH_CM = 0.6
PHOTOPERIOD_M = 3.0
R3_5_FRACTION = 0.613
CHRONOLOGY = (1.149, 0.1, 0.09)  # indeterminate
# Fig. 13, indeterminate: day length at emergence (h, sun above −0.83°), VΔ and rNA,max (nodes a day)
NODE_DAY_LENGTH = (14.0, 14.3, 14.7, 14.95, 15.1)
NODE_V_DELTA = (0.92, 0.91, 0.917, 0.90, 0.806)
NODE_RATE_MAX = (0.417, 0.459, 0.449, 0.407, 0.384)
MAX_NODES = 25

# Cardinal temperatures (°C): min, optimum, max
T_EMERGENCE = (5.0, 31.5, 45.0)
T_NODES = (7.6, 31.0, 40.0)
T_R0_R1 = (7.0, 32.4, 41.9)
T_R1_R5 = (3.6, 25.0, 40.0)
T_R1_R7 = (0.0, 21.5, 38.7)
P_POST_FLOWERING = (12.0, 18.0)  # optimum, critical (h)

MATURITY = Option(
    name="maturity_group",
    label="Maturity group",
    choices=tuple((f"{g:.1f}", f"MG {g:.1f}") for g in np.arange(0, 4.01, 0.5)),
    default="2.0",
)
BIOFIX_EVENT = Option(
    name="biofix_event",
    label="The biofix is",
    choices=(("planting", "Planting"), ("emergence", "Emergence")),
    default="planting",
)
DEPTH = Option(
    name="seeding_depth_in",
    label="Seeding depth",
    choices=(("1.0", "1 in"), ("1.25", "1¼ in"), ("1.5", "1½ in")),
    default="1.5",
)  # the hypocotyl reaches 5 cm at most, so no deeper than 1¾ in

MARGIN_DAYS = 5  # Setiyono et al.'s generalized mode: RMSE 3.6 days, R1 up to 6 days off on their seasons

STAGES = (
    CropStage(code="VE", name="Emergence", description="Cotyledons above the soil surface."),
    CropStage(code="VC", name="Cotyledon", description="Unifoliate leaves unrolled so their edges don't touch."),
    *(
        CropStage(
            code=f"V{n}",
            name=f"{n} nodes",
            description="Fully developed leaves at n nodes on the main stem, from the unifoliate.",
        )
        for n in range(1, MAX_NODES)
    ),
    CropStage(code="R1", name="Beginning bloom", description="One open flower at any node on the main stem."),
    CropStage(
        code="R2",
        name="Full bloom",
        description="An open flower at one of the two uppermost main-stem nodes.",
        estimated=True,
    ),
    CropStage(
        code="R3",
        name="Beginning pod",
        description="A pod 3/16 in long at one of the four uppermost nodes.",
        estimated=True,
    ),
    CropStage(
        code="R4", name="Full pod", description="A pod 3/4 in long at one of the four uppermost nodes.", estimated=True
    ),
    CropStage(
        code="R5", name="Beginning seed", description="A seed 1/8 in long in a pod at one of the four uppermost nodes."
    ),
    CropStage(
        code="R6",
        name="Full seed",
        description="A pod with a green seed filling its cavity at one of the four uppermost nodes.",
        estimated=True,
    ),
    CropStage(code="R7", name="Beginning maturity", description="One normal pod on the main stem at its mature color."),
)
_INDEX = {s.code: i for i, s in enumerate(STAGES)}

SPEC = ModelSpec(
    id="soybean-stages",
    name="Soybean growth stages",
    group="crop",
    version="1.0",
    status="beta",
    summary="Soybean's vegetative and reproductive stages from planting, from temperature and day length, for any "
    "maturity group (SOYDEV).",
    topics=("soybean",),
    crops=("Soybean",),
    citations=(
        Citation(
            text="Setiyono, T. D., Weiss, A., Specht, J., Bastidas, A. M., Cassman, K. G. and Dobermann, A. (2007). "
            "Understanding and modeling the effect of temperature and daylength on soybean phenology under "
            "high-yield conditions. Field Crops Research 100, 257–271.",
            doi="10.1016/j.fcr.2006.07.011",
        ),
        Citation(
            text="Fehr, W. R. and Caviness, C. E. (1977). Stages of soybean development. Special Report 80, Iowa State "
            "University.",
        ),
    ),
    inputs=(Quantity(name="air_temperature_mean", label="Mean temperature", unit="degC"),),
    outputs=(
        Quantity(name="stage", label="Growth stage", unit="index", description="Index in the crop's stage list"),
        Quantity(name="nodes", label="Main-stem nodes (V-stage)", unit="index"),
    ),
    risk=None,
    explorer=(
        ExplorerInput(
            name="temperature", label="Mean temperature", unit="degC", minimum=0, maximum=45, step=0.5, default=22
        ),
        ExplorerInput(
            name="day_length", label="Day length", unit="hour", minimum=10, maximum=18, step=0.25, default=15
        ),
        ExplorerInput(
            name="maturity_group", label="Maturity group", unit="index", minimum=0, maximum=4, step=0.1, default=2
        ),
    ),
    sweep={
        "temperature": tuple(float(t) for t in range(0, 46)),
        "day_length": tuple(float(p) for p in range(10, 19, 2)),
        "maturity_group": (0.0, 2.0, 4.0),
    },
    options=(MATURITY, BIOFIX_EVENT, DEPTH),
    context=("day_of_year", "latitude"),  # day length
    season=("04-15", "10-31"),
    biofix=Biofix(default="05-17", label="Planting date (or emergence, with that option)"),
    changelog=(Change(version="1.0", date="2026-10-28", note="First version."),),
)


def stages(**options: str) -> tuple[CropStage, ...]:
    return STAGES


def temperature_response(t, cardinal) -> np.ndarray:
    """Wang and Engel's (1998) beta function of temperature: 1 at the optimum, 0 at and beyond the limits."""
    t_min, t_opt, t_max = cardinal
    t = np.asarray(t, dtype=float)
    alpha = np.log(2) / np.log((t_max - t_min) / (t_opt - t_min))
    with np.errstate(invalid="ignore"):
        x = np.clip(t - t_min, 0, None)
        f = (2 * x**alpha * (t_opt - t_min) ** alpha - x ** (2 * alpha)) / (t_opt - t_min) ** (2 * alpha)
    return np.where(np.isnan(t), np.nan, np.where((t > t_min) & (t < t_max), np.maximum(f, 0), 0.0))


def photoperiod_response(p, optimum, critical) -> np.ndarray:
    """Setiyono et al.'s eq. 4 (after Yin et al. 1995): 1 up to the optimum day length, 0 beyond the critical."""
    p = np.asarray(p, dtype=float)
    optimum, critical = np.asarray(optimum, dtype=float), np.asarray(critical, dtype=float)
    span = critical - optimum
    alpha = np.log(2) / np.log(span / PHOTOPERIOD_M + 1)
    with np.errstate(invalid="ignore"):
        inner = ((p - optimum) / PHOTOPERIOD_M + 1) * np.clip((critical - p) / span, 0, None) ** (span / PHOTOPERIOD_M)
        f = inner**alpha
    return np.where(np.isnan(p), np.nan, np.where(p <= optimum, 1.0, np.where(p >= critical, 0.0, f)))


def parameters(maturity_group) -> dict[str, np.ndarray]:
    """The generalized relations to maturity group (Figs. 4 and 11)."""
    mg = np.asarray(maturity_group, dtype=float)
    return {
        "induction_optimum": 12.759 - 0.388 * mg - 0.058 * mg**2,
        "induction_critical": 27.275 - 0.493 * mg - 0.066 * mg**2,
        "rate_r0_r1": (0.2551 + 0.0965 * mg) / (1 + 2.1107 * mg),
        "rate_r1_r5": 0.075 - 0.0085 * mg,
        "rate_r1_r7": (0.0563 + 0.0228 * mg) / (1 + 1.9683 * mg),
    }


RATE_EMERGENCE_V1, RATE_EMERGENCE_VC, RATE_INDUCTION = 0.1194, 0.1990, 0.25


def outputs(inputs: Mapping[str, np.ndarray], biofix_index: int = 0, **options: str) -> dict[str, np.ndarray]:
    temp = np.asarray(inputs["air_temperature_mean"], dtype=float)
    doy = np.asarray(inputs["day_of_year"], dtype=float)
    lat = np.broadcast_to(np.asarray(inputs["latitude"], dtype=float), temp.shape[1:])
    doy = doy.reshape(doy.shape + (1,) * (temp.ndim - doy.ndim))
    long_day = day_length_hours(doy, lat, -0.83)
    civil_day = day_length_hours(doy, lat, -6.0)
    p = parameters(number_option(options, MATURITY))
    depth_cm = number_option(options, DEPTH) * 2.54
    from_emergence = options.get(BIOFIX_EVENT.name, BIOFIX_EVENT.default) == "emergence"

    shape = temp.shape[1:]
    zeros = lambda: np.zeros(shape)  # noqa: E731
    att, att_ra, v1, vc, induction, post, r5, r7, nodes = (zeros() for _ in range(9))
    r7_at_r5, days_after_vd = np.full(shape, np.nan), zeros()
    emerged = np.full(shape, from_emergence)
    rate_max, v_delta = np.full(shape, np.nan), np.full(shape, np.nan)
    stage = np.full(temp.shape, np.nan)
    node_out = np.full(temp.shape, np.nan)
    for d in range(biofix_index, temp.shape[0]):
        t = np.nan_to_num(temp[d], nan=-99.0)  # a missing day adds nothing
        f_emerge = temperature_response(t, T_EMERGENCE)
        if not emerged.all():
            growing = ~emerged
            att = np.where(growing, att + np.maximum(t - 5, 0) * (t > -99), att)
            att_ra = np.where(growing & (att > RADICLE_CD), att_ra + np.maximum(t - 5, 0) * (t > -99), att_ra)
            hypocotyl = HYPOCOTYL_MAX_CM * (1 - np.exp(-((HYPOCOTYL_A * att_ra) ** HYPOCOTYL_B)))
            newly = growing & (hypocotyl > depth_cm + EMERGED_PAST_DEPTH_CM)
            emerged = emerged | newly
        else:
            newly = np.zeros(shape, bool)
        if np.isnan(rate_max).any():  # node parameters fixed by the day length on the day of emergence
            at = newly | (emerged & np.isnan(rate_max))
            rate_max = np.where(at, np.interp(long_day[d], NODE_DAY_LENGTH, NODE_RATE_MAX), rate_max)
            v_delta = np.where(at, np.interp(long_day[d], NODE_DAY_LENGTH, NODE_V_DELTA), v_delta)
        on = emerged & ~newly  # development starts the day after emergence
        v1_before, vc_before = v1 >= 1, vc >= 1
        v1 = np.where(on, v1 + RATE_EMERGENCE_V1 * f_emerge, v1)
        vc = np.where(on, vc + RATE_EMERGENCE_VC * f_emerge, vc)
        induction = np.where(
            vc_before,
            induction
            + RATE_INDUCTION
            * photoperiod_response(civil_day[d], p["induction_optimum"], p["induction_critical"])
            * (t > -99),
            induction,
        )
        r0_before, r1_before = induction >= 1, post >= 1
        post = np.where(r0_before, post + p["rate_r0_r1"] * temperature_response(t, T_R0_R1), post)
        light = photoperiod_response(long_day[d], *P_POST_FLOWERING)
        r5_before = r5 >= 1
        r5 = np.where(r1_before, r5 + p["rate_r1_r5"] * temperature_response(t, T_R1_R5) * light, r5)
        r7 = np.where(r1_before, r7 + p["rate_r1_r7"] * temperature_response(t, T_R1_R7) * light, r7)
        r7_at_r5 = np.where(~r5_before & (r5 >= 1), r7, r7_at_r5)
        past_vd = r1_before & (r5 >= v_delta)
        a, b, c = CHRONOLOGY
        slowing = np.where(past_vd, np.maximum(a * (np.exp(-c * days_after_vd) - b), 0), 1.0)
        nodes = np.where(v1_before, nodes + rate_max * temperature_response(t, T_NODES) * slowing, nodes)
        days_after_vd = np.where(past_vd, days_after_vd + 1, days_after_vd)
        stage[d] = _stage(emerged, vc >= 1, v1 >= 1, nodes, post >= 1, r5, r7, r7_at_r5)
        node_out[d] = np.where(v1 >= 1, 1 + nodes, np.where(emerged, 0.0, np.nan))
    return {"stage": stage, "nodes": node_out}


def _stage(emerged, vc, v1, nodes, r1, r5, r7, r7_at_r5) -> np.ndarray:
    v_number = np.minimum(np.floor(1 + nodes), MAX_NODES - 1)
    vegetative = np.where(
        v1, _INDEX["V1"] - 1 + v_number, np.where(vc, _INDEX["VC"], np.where(emerged, _INDEX["VE"], -1))
    )
    # R-number on the R1–R5 progress: 1 at R1, 3.5 at R3.5, 5 at R5, linear between
    r_number = np.where(
        r5 < R3_5_FRACTION, 1 + 2.5 * r5 / R3_5_FRACTION, 3.5 + 1.5 * (r5 - R3_5_FRACTION) / (1 - R3_5_FRACTION)
    )
    reproductive = _INDEX["R1"] + np.minimum(np.floor(r_number), 5) - 1
    r6 = (r5 >= 1) & (r7 >= (r7_at_r5 + 1) / 2)
    reproductive = np.where(r7 >= 1, _INDEX["R7"], np.where(r6, _INDEX["R6"], reproductive))
    return np.where(r1, reproductive, vegetative).astype(float)


def explore(temperature: float, day_length: float, maturity_group: float) -> dict[str, float]:
    """Each phase's daily rate at one temperature and day length (both day-length definitions taken as one)."""
    p = parameters(maturity_group)
    light = photoperiod_response(day_length, *P_POST_FLOWERING)
    induction = photoperiod_response(day_length, p["induction_optimum"], p["induction_critical"])
    rates = {
        "emergence_to_v1": RATE_EMERGENCE_V1 * temperature_response(temperature, T_EMERGENCE),
        "floral_induction": RATE_INDUCTION * induction,
        "r0_to_r1": p["rate_r0_r1"] * temperature_response(temperature, T_R0_R1),
        "r1_to_r5": p["rate_r1_r5"] * temperature_response(temperature, T_R1_R5) * light,
        "r1_to_r7": p["rate_r1_r7"] * temperature_response(temperature, T_R1_R7) * light,
    }
    return {k: float(v) for k, v in rates.items()}
