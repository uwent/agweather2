"""The data status page (`/status`, Phase 7 step 7.2): `/api/v2/status`'s answer to show first (the page asks again
every minute while it's visible), each source of observed hours with its usual delay (`web.status.SOURCE_LAG`), and
the changelog's recent outage notices."""

from datetime import timedelta

from django.utils import timezone

from agdata.provenance import USES
from api.routes.discovery import status_data
from updates.models import ChangelogEntry
from updates.props import ChangelogEntryProps
from web.props import StatusPageProps, StatusSource
from web.status import SOURCE_LAG

OUTAGE_DAYS = 90  # outage notices this recent are listed
REFRESH_SECONDS = 60

# What each source gives the archive, in the order the page lists them (public text)
PROVIDES = {
    "urma": "Temperature, humidity, wind and precipitation",
    "rtma": "The newest hours of temperature, humidity, wind and precipitation, until URMA's arrive",
    "hrrr": "Solar radiation",
    "era5land": "Soil temperature, soil moisture and snow depth",
    "ifs": "The newest days of soil temperature, soil moisture and snow depth, until ERA5-Land's arrive",
}


def sources() -> list[StatusSource]:
    """The sources of observed hours, named as the methods page names them."""
    names = {use.source: (use.name, use.url) for use in reversed(USES)}  # each source's first use
    return [
        StatusSource(
            id=source,
            name=names[source][0],
            url=names[source][1],
            provides=PROVIDES[source],
            normal_lag_hours=SOURCE_LAG[source] / timedelta(hours=1),
        )
        for source in PROVIDES
    ]


def outages(days: int = OUTAGE_DAYS) -> list[ChangelogEntryProps]:
    """The changelog's published outage notices of the last `days`, newest first."""
    since = timezone.localdate() - timedelta(days=days)
    found = ChangelogEntry.objects.visible().filter(kind=ChangelogEntry.Kind.OUTAGE, date__gte=since)
    return [ChangelogEntryProps.of(e) for e in found]


def props() -> StatusPageProps:
    return StatusPageProps(report=status_data(), sources=sources(), outages=outages(), refresh_seconds=REFRESH_SECONDS)
