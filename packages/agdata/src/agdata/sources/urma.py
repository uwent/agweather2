"""URMA hourly analyses (noaa-urma-pds), for any hour since 2016; about 6 hours behind real time.

The bucket's files changed over the years (checked 2026-10-27):

- Analysis until 2017-04-30: urma2p5.tHHz.2dvaranl_ndfd.grb2_ext, no .idx, a 2145 x 1597 grid (NDFD columns 200+)
- Analysis from 2017-05-01: urma2p5.tHHz.2dvaranl_ndfd.grb2_wexp, with .idx, the NDFD 2345 x 1597 grid
- Precip until 2017-12-04: 6-hour totals only, pcpurma_g184.YYYYMMDDHH.06h.grb2 (2145 x 1377, columns 200+)
- Precip 2017-12-05 to 2018-11-25: hourly, pcpurma_g184.YYYYMMDDHH.01h.grb2 (2145 x 1377, columns 200+)
- Precip from 2018-11-26: hourly, urma2p5.YYYYMMDDHH.pcp_01h.wexp.grb2 (NDFD)

All are in urma2p5.YYYYMMDD/. Precip files are named by the end of their accumulation. The older grids are
aligned sub-windows of NDFD (`grid.NDFD.offset_of`), so every era lands on the same cells. Before hourly precip
begins, the ingest takes RTMA's (D23).
"""

from datetime import UTC, date, datetime

from agdata.sources.analysis import AnalysisSource

BUCKET = "https://noaa-urma-pds.s3.amazonaws.com"
HOURLY_PRECIP_FROM = date(2017, 12, 5)
PRECIP_WEXP_FROM = date(2018, 11, 26)


def precip_urls(when: datetime) -> list[str]:
    """Hourly precip files for the hour ending at `when`; none before URMA's hourly precip began."""
    end = when.astimezone(UTC)
    if end.date() < HOURLY_PRECIP_FROM:
        return []
    g184 = f"{BUCKET}/urma2p5.{end:%Y%m%d}/pcpurma_g184.{end:%Y%m%d%H}.01h.grb2"
    wexp = f"{BUCKET}/urma2p5.{end:%Y%m%d}/urma2p5.{end:%Y%m%d%H}.pcp_01h.wexp.grb2"
    return [g184, wexp] if end.date() < PRECIP_WEXP_FROM else [wexp, g184]


URMA = AnalysisSource(name="urma", bucket=BUCKET, prefix="urma2p5", wexp_from=date(2017, 5, 1), precip_urls=precip_urls)
