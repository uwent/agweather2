from agdata.catalog import CUMULATIVE_VARIABLES, DAILY_VARIABLES, VARIABLES
from agdata.computed import DAILY_COMPUTED, HOURLY_COMPUTED
from agdata.layers import DEGREE_DAYS, LAYERS


def test_every_variable_is_a_layer_but_the_internal_ones():
    variables = {layer.variable for layer in LAYERS.values()}
    assert set(DAILY_VARIABLES) - variables == {"et0_sum_estimate"}
    assert set(VARIABLES) - variables == {"shortwave_radiation_hrrr"}
    totals = {n for n in CUMULATIVE_VARIABLES if not n.endswith(("_days", "_hours"))}
    assert totals - variables == {"chill_state"}  # the Dynamic model's carried intermediate
    assert {*DAILY_COMPUTED, *HOURLY_COMPUTED} <= variables  # computed when read (`agdata.computed`)
    assert len(LAYERS) == len(list(LAYERS.values()))  # ids unique


def test_layers_name_their_palette_axis_and_unit():
    for layer in LAYERS.values():
        assert layer.use != "default", layer.id
        assert layer.time_axis in ("day", "hour")
        if layer.variable is not None:
            catalog = {"daily": DAILY_VARIABLES, "hourly": VARIABLES, "cumulative": CUMULATIVE_VARIABLES}[layer.source]
            computed = {"daily": DAILY_COMPUTED, "hourly": HOURLY_COMPUTED}.get(layer.source, {})
            v = computed[layer.variable].variable if layer.variable in computed else catalog[layer.variable]
            assert v.unit == layer.unit


def test_only_quantities_that_add_up_are_summed():
    summed = {layer.id for layer in LAYERS.values() if layer.summable}
    assert {"precipitation_sum", "et0_sum", "shortwave_radiation_sum", "hours_rh_over_90", DEGREE_DAYS} <= summed
    assert "precipitation_hourly" in summed
    assert not {"air_temperature_max", "snow_depth_max", "relative_humidity_mean", "air_temperature_hourly"} & summed
    assert LAYERS["dd_modified_50_86"].stats == () and LAYERS["precipitation_total"].stats == ()
    assert LAYERS["wind_direction_hourly"].stats == ()
    assert "sum" in LAYERS["water_balance"].stats and "sum" not in LAYERS["relative_humidity_mean"].stats
