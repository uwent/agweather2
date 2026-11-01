import numpy as np

from agdata import soil_seam

SEAM = soil_seam.Table(
    version=1,
    lead_hours=np.array([0.0, 24.0, 48.0]),
    weight={"soil_temperature_10cm": np.array([1.0, 0.5, 0.4])},
)


def test_weights_are_linear_between_leads_held_past_the_last_and_zero_before_the_seam():
    w = soil_seam.weights("soil_temperature_10cm", np.array([-1.0, 0.0, 12.0, 48.0, 500.0]), SEAM)
    np.testing.assert_allclose(w, [0.0, 1.0, 0.75, 0.4, 0.4])


def test_shift_fades_each_cells_offset_and_leaves_cells_without_one():
    values = np.full((3, 1, 2), 3.0, dtype=np.float32)
    offset = np.array([[2.0, np.nan]])
    out = soil_seam.shift(values, offset, np.array([0.0, 24.0, 100.0]), "soil_temperature_10cm", SEAM)
    np.testing.assert_allclose(out[:, 0, 0], [5.0, 4.0, 3.8])
    np.testing.assert_allclose(out[:, 0, 1], 3.0)


def test_fit_recovers_how_much_of_a_difference_persists():
    rng = np.random.default_rng(0)
    phi = 0.98  # per hour: after h hours, phi**h of the difference remains
    d = np.zeros((40, 2000))
    for t in range(1, d.shape[1]):
        d[:, t] = phi * d[:, t - 1] + rng.normal(size=d.shape[0])
    d[:, 100:120] = np.nan  # gaps are skipped
    w = soil_seam.fit(d, np.array([0, 6, 24, 72]))
    np.testing.assert_allclose(w, phi ** np.array([0, 6, 24, 72]), atol=0.05)
    assert (np.diff(w) <= 0).all()


def test_the_shipped_table_starts_at_one_and_never_grows():
    table = soil_seam.table()
    assert table.lead_hours[0] == 0
    for name in soil_seam.VARIABLES:
        w = table.weight[name]
        assert w[0] == 1 and (np.diff(w) <= 0).all() and len(w) == len(table.lead_hours)
