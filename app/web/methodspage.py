"""The methods page (`/methods`), Phase 7 track 4: generated from the code and data (D92), never written by hand.

The same functions as `/api/v2/methods` and `/api/v2/variables` give the sources by date and use
(`agdata.provenance`), the corrections with their held-out scores and evidence (`agdata.corrections`), and the
variable catalog (`agdata.catalog`, `agdata.computed`); the grid, the days and the gap rules come from their modules'
constants, so the page can't drift from what the code does.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.urls import reverse

from agdata import corrections, provenance
from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED
from agdata.cumulative import MAX_BRIDGE_DAYS
from agdata.grid import NDFD
from agdata.layers import INTERNAL_TOTALS
from agdata.timezones import GRID_ZONE
from agmodels.features import EVENING_HOUR, OVERNIGHT_HOUR
from agmodels.gaps import MAX_GAP_DAYS
from api.routes.discovery import _variable
from api.routes.methods import _correction, _source
from web.props import MethodsCorrection, MethodsGrid, MethodsProps, MethodsScore, MethodsSource, MethodsVariable

# Standard time's names by UTC offset (hours), for the zone the grid's days keep (`GRID_ZONE`)
ZONE_NAMES = {
    -5: ("Eastern Standard Time", "EST"),
    -6: ("Central Standard Time", "CST"),
    -7: ("Mountain Standard Time", "MST"),
    -8: ("Pacific Standard Time", "PST"),
}


def grid() -> MethodsGrid:
    offset = datetime(2026, 1, 1, tzinfo=ZoneInfo(GRID_ZONE)).utcoffset()
    hours = int(offset.total_seconds() // 3600) if offset is not None else 0
    name, abbreviation = ZONE_NAMES[hours]
    return MethodsGrid(
        name=NDFD.name,
        cell_km=round(NDFD.dx / 1000, 1),
        day_zone=name,
        day_zone_abbreviation=abbreviation,
        day_start_utc=-hours % 24,
        evening_hour=EVENING_HOUR,
        overnight_hour=OVERNIGHT_HOUR,
        interpolate_days=MAX_GAP_DAYS,
        bridge_days=MAX_BRIDGE_DAYS,
    )


def variables() -> list[MethodsVariable]:
    """The catalog as `/api/v2/variables` lists it: hourly, daily, then the running totals people see."""
    hourly = [*VARIABLES.values(), *(c.variable for c in HOURLY_COMPUTED.values())]
    daily = [*DAILY_VARIABLES.values(), *(c.variable for c in DAILY_COMPUTED.values())]
    totals = [v for v in CUMULATIVE_VARIABLES.values() if v.name not in INTERNAL_TOTALS]
    found = [_variable(v, "hourly") for v in hourly]
    found += [_variable(v, "daily") for v in daily]
    found += [_variable(v, "cumulative") for v in totals]
    return [
        MethodsVariable(
            name=v.name,
            long_name=v.long_name,
            kind=v.kind,
            unit=v.unit,
            notes=v.notes,
            statistic=v.statistic,
            hourly_sources=v.hourly_sources,
            computed_from=v.computed_from,
            sources=v.sources,
            gap_fill=v.gap_fill,  # pyright: ignore[reportArgumentType]  # the catalog's GapFill: interpolate or zero
            corrections=v.corrections,
        )
        for v in found
    ]


def methods_props() -> MethodsProps:
    found = [_correction(c) for c in corrections.CORRECTIONS]
    return MethodsProps(
        grid=grid(),
        sources=[MethodsSource(**_source(u).model_dump()) for u in provenance.USES],
        corrections=[
            MethodsCorrection(
                **{k: v for k, v in c.items() if k != "scores"},
                scores=[
                    MethodsScore(
                        measure=s["measure"], unit=s["unit"], before=s["before"], after=s["after"], tested=s["tested"]
                    )
                    for s in c["scores"]
                ],
            )
            for c in found
        ],
        variables=variables(),
        api_methods_url=f"{reverse('api-root')}methods",
    )
