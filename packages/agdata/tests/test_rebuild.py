from datetime import UTC, date, datetime

import numpy as np

from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.daily import rollup_days
from agdata.grid import Window
from agdata.rebuild import find_stale, rebuild_stale
from agdata.store import DAILY, HOURLY, GridStore

WINDOW = Window(900, 902, 1400, 1403)


def test_a_feature_from_older_code_is_found_and_recomputed(tmp_path):
    hourly = GridStore.create(tmp_path, HOURLY, 2025, WINDOW, VARIABLES.values())
    shape = (96, *WINDOW.shape)
    hourly.write(
        datetime(2025, 7, 1, tzinfo=UTC),
        {"air_temperature": np.full(shape, 22.0), "dew_point": np.full(shape, 21.0)},
        source="test",
    )
    rollup_days(tmp_path, WINDOW, date(2025, 7, 2), date(2025, 7, 3))
    assert find_stale(tmp_path).stale == {}

    # Older code wrote a wrong value and its version
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    t = daily.index_of(date(2025, 7, 2))
    daily.write(date(2025, 7, 2), {"hours_rh_over_90": np.zeros((2, *WINDOW.shape))}, source="derived")
    daily._array("hours_rh_over_90").attrs["version"] = 0
    assert find_stale(tmp_path).stale == {"daily/2025": ["hours_rh_over_90"]}

    assert rebuild_stale(tmp_path, WINDOW, log=lambda line: None).stale == {}
    daily = GridStore.open(tmp_path, DAILY, 2025, DAILY_VARIABLES.values())
    np.testing.assert_array_equal(daily.read_steps("hours_rh_over_90", t, t + 2), 24)  # RH 94%
