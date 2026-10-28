"""RTMA hourly analyses (noaa-rtma-pds): the real-time analysis URMA later replaces, about an hour behind.

The analysis files follow URMA's naming (`_ext` until 2017-05-01, `_wexp` from 2017-05-02); hourly precip is
rtma2p5.YYYYMMDDHH.pcp.184.grb2 (the 2145 x 1377 grid, with .idx) in every year since 2016 (checked
2026-10-27), named by the end of the hour, in that day's directory. The ingest uses RTMA for the newest hours
and for precip before URMA's hourly precip begins (D23).
"""

from datetime import UTC, date, datetime

from agdata.sources.analysis import AnalysisSource

BUCKET = "https://noaa-rtma-pds.s3.amazonaws.com"


def precip_urls(when: datetime) -> list[str]:
    end = when.astimezone(UTC)
    return [f"{BUCKET}/rtma2p5.{end:%Y%m%d}/rtma2p5.{end:%Y%m%d%H}.pcp.184.grb2"]


RTMA = AnalysisSource(name="rtma", bucket=BUCKET, prefix="rtma2p5", wexp_from=date(2017, 5, 2), precip_urls=precip_urls)
