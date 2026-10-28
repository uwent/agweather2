"""The packing the pilot's raw files use: URMA's own precision (catalog scales before D21), so the pilot can
compare it with coarser precision. Kept apart from the catalog, which now stores at D21's precision."""

from dataclasses import replace

from agdata.catalog import VARIABLES, Variable

PILOT_SCALES = {
    "air_temperature": (0.01, 0.0),
    "dew_point": (0.01, 0.0),
    "wind_speed": (0.01, 0.0),
    "wind_gust": (0.01, 0.0),
    "wind_direction": (0.1, 0.0),
    "surface_pressure": (0.01, 80.0),
    "cloud_cover": (0.01, 0.0),
    "precipitation": (0.01, 0.0),
}


def pilot_variable(name: str) -> Variable:
    scale, offset = PILOT_SCALES[name]
    return replace(VARIABLES[name], scale=scale, offset=offset)
