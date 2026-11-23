"""A reference of NEWA's apple scab and fire blight results, checked against NEWA's own page exports (models plan B5).

NEWA (newa.cornell.edu) computes its apple models in the browser from a station's hours (NRCC's stnHrly, fetched
by scripts/fetch_newa.py into tmp/newa/hours/). This script repeats that computation in Python from a reading of
NEWA 3.0's page logic (tmp/newa-src/; methods and constants only, no code copied), exactly as its pages compute them, so it can stand
in for NEWA at every station-season we have hours for. Constants are NEWA's (credit: NEWA, Cornell IPM).

What it repeats, per NEWA's pages as of 2026-11:

- Days: the station's local clock (America/Chicago), hours ending 01:00 to 24:00; the very first hour of the
  request is dropped and a last, incomplete day isn't formed. Daily max and min from those hours.
- Degree days: base 43 °F by NEWA's single sine (with its `sin` for `asin` and π = 3.14), base 40 °F and base 0 °C
  by the simple average; each day's value rounded to a whole degree day where NEWA rounds it.
- Apple scab: green tip at 101 DD43; ascospore maturity (Gadoury and MacHardy 1982 as a logistic, base 0 °C, a day
  counted only after a week with rain, Stensvand et al. 2005) and discharge; wet and dry periods from green tip
  (start: wet and raining; continue: wet or raining), merged when less than 24 hours apart, an infection when the
  hours reach NEWA's Revised Mills table at the rounded mean temperature; the daily summary.
- Root maggots (cabbage, onion, seedcorn): the simple-average running total from January 1 and the days it reaches
  each event of NEWA's tables (used by scripts/check_maggots.py; NEWA's pages weren't exported to check against).
- Fire blight: Cougarblight's daily degree hours (Smith's table, hours from 60 to 105 °F) and NEWA's 4-day sum;
  MaryBlyt's EIP from first blossom (230 DD43) to the end of the data, with NEWA's blossom window and cold-day cuts;
  the daily wetness table.

    uv run python scripts/newa_reference.py check     # every export in tmp/newa/{apple-scab,fire-blight}/

Exports are the CSVs NEWA's pages download, one folder per station-season, named like `apple-scab-gays-mills-2025`.
"""

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

CACHE = Path("tmp/newa")
LOCAL = ZoneInfo("America/Chicago")  # the browser's clock NEWA's pages format and group days by
HOUR_MS = 3_600_000
STATIONS = {"baileys-harbor": "wi_bai", "brighton": "wi_bri", "eau-claire": "wi_eau", "gays-mills": "wi_gay"}

# NEWA's Revised Mills table: the event's mean temperature (°F, rounded) → wet hours needed for infection.
MILLS_F = (
    {
        34: 41,
        35: 41,
        36: 35,
        37: 30,
        38: 30,
        39: 28,
        40: 28,
        41: 21,
        42: 21,
        43: 18,
        44: 18,
        45: 15,
        46: 13,
        47: 13,
        48: 12,
        49: 12,
        50: 11,
        51: 11,
        52: 9,
        53: 9,
        54: 8,
        55: 8,
        56: 8,
        57: 7,
        58: 7,
        59: 7,
        60: 7,
    }
    | dict.fromkeys(range(61, 77), 6)
    | {77: 8, 78: 8, 79: 11}
)

# Cougarblight's degree-hour value of an hour at each whole °F (Smith's table as NEWA has it, 60–105 °F; NEWA
# counts hours below 60 or above 105 as 0, so its 51–59 rows never apply).
COUGARBLIGHT_F = {
    60: 0.52,
    61: 0.62,
    62: 0.72,
    63: 0.95,
    64: 1.06,
    65: 1.16,
    66: 1.41,
    67: 2,
    68: 2.7,
    69: 3.3,
    70: 4,
    71: 4.9,
    72: 6.3,
    73: 7.95,
    74: 11,
    75: 14.1,
    76: 17,
    77: 20.3,
    78: 23.5,
    79: 27,
    80: 30,
    81: 33.2,
    82: 36,
    83: 38.9,
    84: 42.2,
    85: 46,
    86: 48.2,
    87: 50.2,
    88: 52,
    89: 52,
    90: 51.5,
    91: 50.5,
    92: 47.5,
    93: 40,
    94: 28,
    95: 10,
    96: 0,
    97: 0,
    98: 0,
    99: 0,
    100: 0,
    101: -10,
    102: -20,
    103: -30,
    104: -40,
    105: -50,
}

SCAB_GREEN_TIP_DD43 = 101
FIRST_BLOSSOM_DD43 = 230


# JavaScript's rounding, which the CSVs show: Math.round rounds half up; toFixed rounds the exact binary value half
# away from zero.
def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def to_fixed(x: float, digits: int) -> str:
    return str(Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def js_sum(values) -> float:
    """Left-to-right float addition, as JavaScript's reduce does it (Python's sum() compensates since 3.12, which
    changes ties such as 31.5 against 31.4999…)."""
    total = 0.0
    for v in values:
        total += v
    return total


def num(x: float, digits: int) -> float:
    """`+x.toFixed(digits)`: the rounded value as a number."""
    return float(to_fixed(x, digits))


def positive(x) -> bool:
    return x is not None and x > 0


def zero(x) -> bool:
    return x is not None and x == 0


@dataclass(kw_only=True)
class Hour:
    ms: int  # the hour's end, ms since 1970 (NEWA's `ms`)
    local: datetime
    prcp: float | None
    temp: float | None
    rhum: float | None
    dwpt: float | None
    lwet: float | None


@dataclass(kw_only=True)
class Day:
    doy: int
    date: datetime  # the 23:00 hour's end, local
    ms: int
    hours: list[Hour]
    maxt: float = math.nan
    mint: float = math.nan
    values: dict = field(default_factory=dict)

    def series(self, name: str) -> list:
        return [getattr(h, name) for h in self.hours]


def load_hours(path: Path, until: datetime | None = None) -> list[Hour]:
    data = json.loads(path.read_text())
    fields = data["hrlyFields"]
    hours = []
    for row in data["hrlyData"]:
        value = dict(zip(fields, row, strict=True))
        local = datetime.fromisoformat(value["date"]).astimezone(LOCAL)
        if until is not None and local > until:
            break
        read = {
            name: None if value.get(name, "M") == "M" else float(value[name])
            for name in ("prcp", "temp", "rhum", "dwpt", "lwet")
        }
        hours.append(
            Hour(
                ms=int(local.timestamp() * 1000),
                local=local,
                prcp=read["prcp"],
                temp=read["temp"],
                rhum=read["rhum"],
                dwpt=read["dwpt"],
                lwet=read["lwet"],
            )
        )
    return hours


def make_days(hours: list[Hour]) -> list[Day]:
    """NEWA's days: hours ending 01–24 on the local clock, the request's first hour dropped, a last incomplete day
    left out; a day is dated by its 23:00 hour."""
    days: list[Day] = []
    current: list[Hour] = []
    date, ms = hours[0].local, hours[0].ms
    for h in hours[1:]:
        hour = h.local.hour or 24
        if hour == 23:
            date, ms = h.local, h.ms
        current.append(h)
        if hour == 24:
            days.append(Day(doy=len(days) + 1, date=date, ms=ms, hours=current))
            current = []
    for d in days:
        temps = [t for t in d.series("temp") if t is not None]
        d.maxt = max(temps) if temps else -math.inf
        d.mint = min(temps) if temps else math.inf
    return days


def sine_dd_newa(*, tmin: float, tmax: float, base: float) -> float:
    """NEWA's single sine, as its code has it (`sin` where the method needs `asin`, π as 3.14)."""
    if tmin >= base:
        dd = (tmax + tmin) / 2 - base
    elif tmax <= base:
        dd = 0.0
    else:
        avg = (tmax + tmin) / 2
        amt = (tmax - tmin) / 2
        t1 = math.sin((base - avg) / amt)
        dd = 0.0 if avg < 0 else abs((amt * math.cos(t1) - (base - avg) * (3.14 / 2 - t1)) / 3.14)
    return max(dd, 0.0)


def average_dd(*, tmin: float, tmax: float, base: float) -> float:
    return max((tmin + tmax) / 2 - base, 0.0)


def accumulate(days: list[Day], *, base: float, start: int, method, celsius: bool = False) -> list[tuple[int, int]]:
    """NEWA's calculateGdd from day index `start`: (the day's DD rounded, the running total rounded), per day."""
    total = 0.0
    out = []
    for d in days[start:]:
        lo, hi = d.mint, d.maxt
        if celsius:
            lo, hi = (lo - 32) * 5 / 9, (hi - 32) * 5 / 9
        dd = method(tmin=lo, tmax=hi, base=base)
        total += dd
        out.append((js_round(dd), js_round(total)))
    return out


# --- Apple scab ---------------------------------------------------------------------------------------------------


@dataclass(kw_only=True)
class WetDry:
    kind: str  # wet, dry or combined
    start_ms: int
    end_ms: int
    hours: int
    avg_t: float
    rain: float

    def start_text(self) -> str:
        return stamp(self.start_ms - HOUR_MS, minute="01")

    def end_text(self) -> str:
        return stamp(self.end_ms, minute="00")


def stamp(ms: int, *, minute: str) -> str:
    t = datetime.fromtimestamp(ms / 1000, LOCAL)
    return f"{t:%b %d} {t.hour % 12 or 12}:{minute} {'am' if t.hour < 12 else 'pm'}"


def percent(x: float) -> str:
    """NEWA's discharge as its table shows it."""
    return "<1%" if 0 < x < 1 else f"{to_fixed(x, 0)}%"


def summarize(kind: str, event: list[Hour]) -> WetDry:
    temps = [h.temp for h in event if h.temp is not None]
    rain = js_sum(h.prcp for h in event if positive(h.prcp))  # type: ignore[misc]
    return WetDry(
        kind=kind,
        start_ms=event[0].ms,
        end_ms=event[-1].ms,
        hours=len(event),
        avg_t=num(js_sum(temps) / len(temps), 0) if temps else math.nan,
        rain=num(rain, 2),
    )


def scab(hours: list[Hour], days: list[Day]) -> dict:
    """NEWA's apple scab page for a past season: green tip, ascospore maturity and discharge by day, the wet and dry
    log, infection events and the daily summary."""
    dd43 = accumulate(days, base=43, start=0, method=sine_dd_newa)
    green_tip = next((d for d, (_, total) in zip(days, dd43, strict=True) if total >= SCAB_GREEN_TIP_DD43), None)
    result: dict = {"green_tip": green_tip, "dd43": dd43}

    # Daily summary
    summary = []
    for d in days:
        wet_temps = [h.temp for h in d.hours if positive(h.lwet) and h.temp is not None]
        summary.append(
            {
                "date": d.date.strftime("%m/%d/%Y"),
                "wet_t": to_fixed(js_sum(wet_temps) / len(wet_temps), 0) if wet_temps else "-",
                "lwet_hours": sum(1 for h in d.hours if positive(h.lwet)),
                "rh90_hours": sum(1 for h in d.hours if h.rhum is not None and h.rhum >= 90),
                "rain": num(js_sum(p for p in d.series("prcp") if positive(p)), 2),
                "doy": d.doy,
            }
        )

    # Ascospore maturity and discharge, from the day 8 days before green tip (its 7-day rain window makes the first
    # degree days count the day before green tip).
    maturity = []
    if green_tip is not None:
        start = max(green_tip.doy - 9, 0)
        dd0 = accumulate(days, base=0, start=start, method=average_dd, celsius=True)
        window = days[start:]
        rain7: list[float] = []
        gdd0 = 0.0
        released = 0.0
        for i, (d, (dd, _)) in enumerate(zip(window, dd0, strict=True)):
            rain7.append(num(js_sum(p for p in d.series("prcp") if p is not None), 2))
            if i >= 7 and js_sum(rain7[i - 7 : i]) > 0:  # at i = 6 JavaScript's slice(-1, 6) is empty
                gdd0 += dd
            z = math.exp(math.pi / math.sqrt(3) * (2.51 + 0.01 * gdd0 - 5))
            mature = 100 * z / (1 + z)
            discharge = 0.0
            all_released = False
            if i > 0:
                night = window[i - 1].series("prcp")[19:] + d.series("prcp")[:6]
                day_prcp = d.series("prcp")[6:19]
                day_temp = d.series("temp")[6:19]
                night_sum = js_sum(p for p in night if p)
                day_sum = js_sum(p for p in day_prcp if p)
                rain_temps = [t for p, t in zip(day_prcp, day_temp, strict=False) if positive(p) and t is not None]
                rain_t = js_sum(rain_temps) / len(rain_temps) if rain_temps else 0.0
                if night_sum > 0:
                    step = (mature - released) * 0.05
                    released += step
                    discharge += step
                if day_sum > 0:
                    share = {(True, True): 0.9, (True, False): 0.5, (False, True): 0.5, (False, False): 0.25}[
                        (rain_t >= 50, day_sum >= 0.1)
                    ]
                    step = (mature - released) * share
                    released += step
                    discharge += step
                all_released = mature >= 95 and day_sum > 0.1 and rain_t > 50
            maturity.append(
                {
                    "date": d.date.strftime("%m/%d/%Y"),
                    "gdd0c": gdd0,
                    "maturity": js_round(mature),
                    "discharge": discharge,
                    "released": released,
                    "all_released": all_released,
                    "daily_text": percent(discharge) if i > 0 else "",
                    "released_text": percent(released) if i > 0 else "",
                }
            )
    result["maturity"] = maturity

    # Wet and dry periods from the hour ending 00:00 on green tip day
    wet_events: list[list[Hour]] = []
    dry_events: list[list[Hour]] = []
    if green_tip is not None:
        index = next(i for i, h in enumerate(hours) if h.ms == green_tip.ms)
        run = hours[index - 23 :]
        event: list[Hour] = []
        for n, h in enumerate(run):
            if not event:
                if positive(h.lwet) and positive(h.prcp):
                    event.append(h)
            else:
                if positive(h.lwet) or positive(h.prcp):
                    event.append(h)
                    if n == len(run) - 1:
                        wet_events.append(event)
                        event = []
                if zero(h.lwet) and zero(h.prcp):
                    wet_events.append(event)
                    event = []
        event = []
        for n, h in enumerate(run):
            if not event:
                if zero(h.lwet) and zero(h.prcp):
                    event.append(h)
            elif positive(h.lwet) and positive(h.prcp):
                dry_events.append(event)
                event = []
            else:
                event.append(h)
                if n == len(run) - 1:
                    dry_events.append(event)
                    event = []
    wets = [summarize("wet", e) for e in wet_events]
    log = sorted(wets + [summarize("dry", e) for e in dry_events], key=lambda e: e.start_ms)
    result["log"] = log

    combined: list[WetDry] = []
    for e in wets:
        if combined and (e.start_ms - combined[-1].end_ms) / HOUR_MS < 24:
            prev = combined[-1]
            combined[-1] = WetDry(
                kind="combined",
                start_ms=prev.start_ms,
                end_ms=e.end_ms,
                hours=prev.hours + e.hours,
                avg_t=num((prev.hours * prev.avg_t + e.hours * e.avg_t) / (prev.hours + e.hours), 0),
                rain=prev.rain + e.rain,
            )
        else:
            combined.append(
                WetDry(kind=e.kind, start_ms=e.start_ms, end_ms=e.end_ms, hours=e.hours, avg_t=e.avg_t, rain=e.rain)
            )
    infections = [e for e in combined if 34 <= e.avg_t <= 79 and e.hours >= MILLS_F[int(e.avg_t)]]
    result["infections"] = infections

    def doy(ms: int) -> int:
        return datetime.fromtimestamp(ms / 1000, LOCAL).timetuple().tm_yday

    for row in summary:
        row["infection"] = "no"
        event = next((e for e in infections if doy(e.start_ms) <= row["doy"] <= doy(e.end_ms)), None)
        if event is not None:
            row["infection"] = "yes" if doy(event.end_ms) == row["doy"] else "combined"
    result["summary"] = summary
    return result


# --- Fire blight --------------------------------------------------------------------------------------------------


def fire_blight(days: list[Day]) -> list[dict]:
    """NEWA's fire blight page for a past season, its date of interest between first blossom and petal fall and no
    dates entered: Cougarblight's 4-day degree hours, MaryBlyt's EIP and risk, and the wetness table, by day."""
    dd43 = accumulate(days, base=43, start=0, method=sine_dd_newa)
    dd40 = accumulate(days, base=40, start=0, method=average_dd)
    rows: list[dict] = []
    four_day = 0
    daily: list[int] = []
    starting = -1
    for i, d in enumerate(days):
        temps = [t for t in d.series("temp") if t is not None]
        dh = js_round(js_sum(0 if t < 60 or t > 105 else COUGARBLIGHT_F[js_round(t)] for t in temps))
        if dd43[i][1] >= FIRST_BLOSSOM_DD43 and starting == -1:
            starting = d.doy
        daily.append(dh)
        # NEWA's ramp after first blossom: 1, 2, 3 days, the 3-day sum again, then 4 days. Before first blossom
        # `starting` is −1 and every day from January 4 gets the 4-day sum.
        if d.doy == starting + 1:
            four_day = dh
        if d.doy == starting + 2:
            four_day = sum(js_slice(daily, i - 1, i + 1))
        if d.doy == starting + 3:
            four_day = sum(js_slice(daily, i - 2, i + 1))
        if d.doy > starting + 4:
            four_day = sum(js_slice(daily, i - 3, i + 1))
        prcp = d.series("prcp")
        rain = js_sum(p for p in prcp if positive(p))
        rhs = [r for r in d.series("rhum") if r is not None]
        dew = any(
            t is not None and w is not None and p is not None and t - w <= 3 and p == 0
            for t, w, p in zip(d.series("temp"), d.series("dwpt"), prcp, strict=True)
        )
        rows.append(
            {
                "date": d.date.strftime("%Y-%m-%d"),
                "doy": d.doy,
                "maxt": d.maxt,
                "mint": d.mint,
                "dd43": dd43[i][1],
                "dd40": dd40[i][0],
                "first_bloom": dd43[i][1] >= FIRST_BLOSSOM_DD43,
                "dh": dh,
                "four_day": four_day,
                "rain": rain,
                "dew": "yes" if dew else "no",
                "lwet_hours": sum(1 for h in d.hours if positive(h.lwet)),
                "rh90_hours": sum(1 for r in rhs if r > 90),
                "rh_max": max(rhs) if rhs else None,
                "rh_min": min(rhs) if rhs else None,
                "avg_t": (d.maxt + d.mint) / 2,
                "dh65": num(js_sum(t - 65 if t > 65 else 0 for t in temps), 1),
                "eip": 0,
                "risk": "low",
            }
        )
    first = next((r for r in rows if r["first_bloom"]), None)
    if first is not None:
        maryblyt(rows=rows, first_doy=first["doy"])
    return rows


def js_slice(values: list, start: int, end: int) -> list:
    n = len(values)
    start = max(n + start, 0) if start < 0 else start
    end = max(n + end, 0) if end < 0 else end
    return values[start:end]


def maryblyt(*, rows: list[dict], first_doy: int) -> None:
    """NEWA's EIP loop, as its code runs it. Its days are looked up by index = day of year, so `at(doy)` is the day
    after `doy` and `at(doy - 2)` the day before; a lookup past either end is an empty day, whose comparisons fail."""

    def at(k: int) -> dict:
        return rows[k] if 0 <= k < len(rows) else {}

    def le(day: dict, key: str, limit: float) -> bool:
        return key in day and day[key] <= limit

    acc_dd40 = 0.0
    start = at(first_doy)
    for i in range(first_doy, len(rows)):
        day = rows[i]
        while acc_dd40 >= 80:
            acc_dd40 -= at(start["doy"])["dd40"]
            start = at(start["doy"])
        acc = 0.0
        td = start
        while "doy" in td and td["doy"] <= day["doy"]:
            one, two = at(td["doy"] - 2), at(td["doy"] - 3)
            if le(td, "maxt", 65) and le(one, "maxt", 65) and le(two, "maxt", 65):
                start = day
                td = day
                one, two = at(td["doy"] - 2), at(td["doy"] - 3)
                acc_dd40 = 0.0
                acc = 0.0
            acc += td["dh65"]
            if td["mint"] < 24 or (td["mint"] < 33 and acc < 400):
                acc = 0.0
            elif td["maxt"] <= 65 and acc < 400:
                if le(one, "maxt", 65) and le(two, "maxt", 65):
                    acc = 0.0
                elif le(one, "maxt", 65):
                    acc *= 0.5
                else:
                    acc *= 0.667
            td = at(td["doy"])
        acc_dd40 += day["dd40"]
        day["eip"] = js_round(acc / 198 * 100)
        yesterday = at(day["doy"] - 2)
        wetting = day["rain"] > 0 or day["lwet_hours"] > 0 or day["dew"] == "yes" or yesterday.get("rain", 0) > 0.1
        count = (day["eip"] > 100) + (day["avg_t"] > 60) + wetting
        day["risk"] = ["low", "moderate", "high", "infection"][count]


# --- Codling moth -------------------------------------------------------------------------------------------------

# NEWA's codling moth page (codling-moth.json, as read from its live page 2026-11-17): DD50 by its sine, no upper,
# from January 1; first catch (biofix 1) where the rounded total reaches 404, the second generation's first catch
# (biofix 2) 1501 after biofix 1; its management guide's stages in degree days after each biofix.
CM_BIOFIX1, CM_BIOFIX2 = 404, 1501
CM_AFTER_BIOFIX1 = {"first hatch": 220, "first spray": 250, "first flight over": 592, "second flight": 771}
CM_AFTER_BIOFIX2 = {"second hatch": 0, "second flight over": 351}


def codling_moth(days: list[Day], biofix1: int | None = None) -> dict:
    """NEWA's codling moth: each day's totals from January 1, biofix 1 and biofix 2 (rounded as its page rounds them:
    the January 1 total once, totals from a biofix as sums of each day's rounded DD), the biofix days and the first
    day of each stage of its management guide. `biofix1` is a grower's first catch (a day index)."""
    jan1 = accumulate(days, base=50, start=0, method=sine_dd_newa)
    if biofix1 is None:
        biofix1 = next((k for k, (_, total) in enumerate(jan1) if total >= CM_BIOFIX1), None)
    after1: list[int | None] = [None] * len(days)
    after2: list[int | None] = [None] * len(days)
    biofix2 = None
    if biofix1 is not None:
        total1 = total2 = 0
        for k in range(biofix1, len(days)):
            dd = jan1[k][0]
            total1 += dd
            after1[k] = total1
            if biofix2 is None and total1 >= CM_BIOFIX2:
                biofix2 = k
            if biofix2 is not None:
                total2 += dd
                after2[k] = total2
    events: dict[str, int | None] = {"first catch": biofix1, "second catch": biofix2}
    for name, dd in CM_AFTER_BIOFIX1.items():
        events[name] = next((k for k, t in enumerate(after1) if t is not None and t >= dd), None)
    for name, dd in CM_AFTER_BIOFIX2.items():
        events[name] = next((k for k, t in enumerate(after2) if t is not None and t >= dd), None)
    return {"jan1": [t for _, t in jan1], "after1": after1, "after2": after2, "events": events}


# --- Root maggots -------------------------------------------------------------------------------------------------
# NEWA's cabbage, onion and seedcorn maggot pages (tmp/references/insects/notes/newa-insects.md, read 2026-11-21):
# the day's simple average above a base, no upper, unrounded into a running total from January 1; an event is the
# first day the total reaches its degree days. Cabbage and onion maggot in °F above 40 °F; seedcorn maggot, as
# deployed, in °C above 3.9 °C (its table: 53 first adult emergence, 198 complete).
CABBAGE_MAGGOT = {"first emergence": 288, "25%": 366, "spring peak": 452, "75%": 547, "95%": 697, "first generation peak": 1261, "second generation peak": 2176, "third generation peak": 3014}  # fmt: skip
ONION_MAGGOT = {"first emergence": 390, "spring peak": 735, "first generation first": 1218, "first generation peak": 1752, "second generation first": 2415, "second generation peak": 2975}  # fmt: skip
SEEDCORN_MAGGOT_C = {"first emergence": 53, "emergence complete": 198}


def maggot(days: list[Day], table: dict[str, float], *, base: float = 40, celsius: bool = False) -> dict:
    """NEWA's root maggot models: the running simple-average total from January 1 (each day unrounded) and the
    first day index reaching each event's degree days (None if not reached). A day without hours adds nothing."""
    total, totals = 0.0, []
    for d in days:
        if math.isfinite(d.mint) and math.isfinite(d.maxt):
            lo, hi = (d.mint, d.maxt) if not celsius else ((d.mint - 32) * 5 / 9, (d.maxt - 32) * 5 / 9)
            total += average_dd(tmin=lo, tmax=hi, base=base)
        totals.append(total)
    events = {name: next((k for k, t in enumerate(totals) if t >= dd), None) for name, dd in table.items()}
    return {"totals": totals, "events": events}


# --- Checking against NEWA's exports ------------------------------------------------------------------------------


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def same(a: str, b) -> bool:
    try:
        return math.isclose(float(a), float(b), abs_tol=1e-9)
    except (TypeError, ValueError):
        return str(a) == str(b)


def compare(*, label: str, ours: dict[str, dict], theirs: list[dict], columns: dict[str, str], key: str) -> list[str]:
    """Rows matched by `key`; each NEWA column against ours. Returns the mismatches as lines."""
    lines = []
    matched = 0
    for row in theirs:
        mine = ours.get(row[key])
        if mine is None:
            lines.append(f"  {label}: {row[key]} not in ours")
            continue
        matched += 1
        for col, name in columns.items():
            if not same(row[col], mine[name]):
                lines.append(f"  {label} {row[key]} {col}: NEWA {row[col]!r}, ours {mine[name]!r}")
    lines.insert(0, f"{label}: {matched} rows matched, {len(lines)} differences")
    return lines


def check(folder: Path, out: list[str]) -> int:
    model, _, rest = folder.name.partition("-")
    if model == "apple":
        model, rest = "apple-scab", rest.removeprefix("scab-")
    else:
        model, rest = "fire-blight", rest.removeprefix("blight-")
    place, year = rest.rsplit("-", 1)
    station = STATIONS[place]
    path = CACHE / "hours" / f"{station}_newa_{year}.json"
    out.append(f"\n## {folder.name} ({station} {year})")
    if model == "apple-scab":
        # The scab page's hours ended at October 30, 23:00 (its wet and dry log's last row).
        hours = load_hours(path, until=datetime(int(year), 10, 30, 23, tzinfo=LOCAL))
        days = make_days(hours)
        result = scab(hours, days)
        gt = result["green_tip"]
        out.append(f"green tip {gt.date:%Y-%m-%d}" if gt else "no green tip")
        diffs = compare(
            label="infection summary",
            ours={r["date"]: r for r in result["summary"]},
            theirs=read_csv(folder / "Infection Event Summary.csv"),
            columns={
                "Infection Events": "infection",
                "Avg Temp (˚F) for wet hours": "wet_t",
                "Leaf Wetness (hrs)": "lwet_hours",
                "Hrs > 90% RH": "rh90_hours",
                "Rain Amount (in)": "rain",
            },
            key="date",
        )
        log = {
            e.start_text(): {"end": e.end_text(), "hours": e.hours, "avg_t": e.avg_t, "rain": e.rain}
            for e in result["log"]
        }
        theirs = read_csv(folder / "Wet And Dry Log Table.csv")
        diffs += compare(
            label="wet and dry log",
            ours=log,
            theirs=theirs,
            columns={"Ending Date Time": "end", "Hours": "hours", "Avg Temp (˚F)": "avg_t", "Total Rain (in)": "rain"},
            key="Starting Date Time",
        )
        maturity_csv = folder / "Ascospore Maturity Summary.csv"
        if maturity_csv.exists():
            diffs += compare(
                label="ascospore maturity",
                ours={r["date"]: r for r in result["maturity"]},
                theirs=read_csv(maturity_csv),
                columns={
                    "Ascospore Maturity": "maturity",
                    "Daily Ascospore Discharge": "daily_text",
                    "Cumulative Ascospore Discharge": "released_text",
                },
                key="date",
            )
        else:
            out.append("ascospore maturity: no export to check")
        extra = sorted(set(log) - {r["Starting Date Time"] for r in theirs})
        diffs += [f"  wet and dry log: ours has {s} ({log[s]})" for s in extra]
        infections = (
            [
                f"{e.start_text()} – {e.end_text()} {e.hours} h {e.avg_t:.0f} °F {e.kind}"
                for e in result["infections"]
                if e.start_ms < gt.ms + 120 * 86_400_000
            ]
            if gt
            else []
        )
        out.append(f"infection events (first 120 days): {len(infections)}")
        out += [f"  {line}" for line in infections]
    else:
        hours = load_hours(path)
        days = make_days(hours)
        rows = fire_blight(days)
        first = next((r for r in rows if r["first_bloom"]), None)
        out.append(f"first blossom {first['date']}" if first else "no first blossom")
        ours = {
            r["date"]: r
            | {
                "rain_text": to_fixed(r["rain"], 2),
                "rh": f"{r['rh_max']:g}/{r['rh_min']:g}",
                "avg_text": to_fixed(r["avg_t"], 1),
            }
            for r in rows
        }
        diffs = compare(
            label="results",
            ours=ours,
            theirs=read_csv(folder / "Results Table.csv"),
            columns={"Cougar Blight 4-Day DH": "four_day", "Infection Potential EIP Value": "eip"},
            key="date",
        )
        diffs += compare(
            label="wetness",
            ours=ours,
            theirs=read_csv(folder / "Wetness Events Table.csv"),
            columns={
                "Rain Amount (in)": "rain_text",
                "Dew": "dew",
                "Leaf Wetness (hrs)": "lwet_hours",
                "Hrs > 90% RH": "rh90_hours",
                "RH max/min": "rh",
                "Avg Temp (˚F)": "avg_text",
            },
            key="date",
        )
    out += diffs
    return sum(1 for line in diffs if line.startswith("  "))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--max-lines", type=int, default=40, help="differences shown per station-season")
    args = parser.parse_args()
    total = 0
    for folder in sorted([*(CACHE / "apple-scab").iterdir(), *(CACHE / "fire-blight").iterdir()]):
        out: list[str] = []
        total += check(folder, out)
        shown = [line for line in out if not line.startswith("  ")] + [line for line in out if line.startswith("  ")][
            : args.max_lines
        ]
        print("\n".join(shown))
    print(f"\n{total} differences in all")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
