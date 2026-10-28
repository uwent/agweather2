from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from agdata.grid import Window, service_window
from agdata.sources import urma
from agdata.sources.grib import RemoteGrib, decode, describe_message_head, parse_idx, place, scan_index

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_idx():
    refs = parse_idx((FIXTURES / "urma_wexp.idx").read_text())
    keys = [ref.key for ref in refs]
    assert ("TMP", "2 m above ground") in keys
    assert ("TCDC", "entire atmosphere (considered as a single layer)") in keys
    assert refs[0].offset == 0 and refs[0].length == refs[1].offset
    assert refs[-1].length is None  # runs to the end of the file


def test_describe_message_head_of_a_2016_file():
    total, key = describe_message_head((FIXTURES / "urma_2016_tmp_head.bin").read_bytes())
    assert key == ("TMP", "2 m above ground")
    assert total > 1_000_000


def test_scan_index_walks_message_lengths():
    head = (FIXTURES / "urma_2016_tmp_head.bin").read_bytes()
    total, _ = describe_message_head(head)
    refs = scan_index(lambda start, end: head, size=total * 3)
    assert [ref.offset for ref in refs] == [0, total, 2 * total]


def test_decode_and_place_on_the_window():
    field = decode((FIXTURES / "urma_tmp_small.grb2").read_bytes())
    expected = np.load(FIXTURES / "urma_tmp_small_expected.npy")
    assert field.units == "K"
    np.testing.assert_allclose(field.values, expected, atol=0.01, equal_nan=True)
    assert np.isnan(field.values[0, 0])  # the bitmap's missing cell

    # The fixture covers NDFD rows 900-939 and columns 1400-1449; this window overlaps part of it
    window = Window(930, 950, 1440, 1460)
    placed = place(field, window)
    np.testing.assert_allclose(placed[:10, :10], expected[30:40, 40:50], atol=0.01)
    assert np.isnan(placed[10:, :]).all() and np.isnan(placed[:, 10:]).all()


def test_urls_by_era():
    assert urma.analysis_url(datetime(2016, 7, 1, 18, tzinfo=UTC)).endswith("urma2p5.t18z.2dvaranl_ndfd.grb2_ext")
    assert urma.analysis_url(datetime(2017, 5, 1, 0, tzinfo=UTC)).endswith("grb2_wexp")
    assert urma.precip_url(datetime(2017, 12, 4, 23, tzinfo=UTC)) is None
    assert urma.precip_url(datetime(2018, 7, 1, 18, tzinfo=UTC)).endswith(  # pyright: ignore[reportOptionalMemberAccess]
        "urma2p5.20180701/pcpurma_g184.2018070118.01h.grb2"
    )
    assert urma.precip_url(datetime(2025, 7, 15, 18, tzinfo=UTC)).endswith(  # pyright: ignore[reportOptionalMemberAccess]
        "urma2p5.20250715/urma2p5.2025071518.pcp_01h.wexp.grb2"
    )


def test_fetch_hour_needs_an_aware_time_on_the_hour():
    with pytest.raises(ValueError):
        urma.fetch_hour(datetime(2025, 7, 15, 18), service_window("wisconsin"))  # noqa: DTZ001


@pytest.mark.network
@pytest.mark.enable_socket
@pytest.mark.parametrize("when", [datetime(2016, 7, 1, 18, tzinfo=UTC), datetime(2025, 7, 15, 18, tzinfo=UTC)])
def test_fetch_a_real_hour_over_wisconsin(when):
    window = service_window("wisconsin")
    values = urma.fetch_hour(when, window)
    temp = values["air_temperature"]
    assert temp.shape == window.shape
    assert 5 < np.nanmean(temp) < 40  # a July afternoon, °C
    assert np.isfinite(temp).mean() > 0.95
    assert 85 < np.nanmean(values["surface_pressure"]) < 105  # kPa
    assert ("precipitation" in values) == (when.year >= 2018)


@pytest.mark.network
@pytest.mark.enable_socket
def test_remote_index_without_idx_matches_shape():
    old = RemoteGrib(urma.analysis_url(datetime(2016, 7, 1, 18, tzinfo=UTC)))
    assert {("TMP", "2 m above ground"), ("PRES", "surface")} <= {ref.key for ref in old.index()}
