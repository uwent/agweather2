"""Daily weather for the field seasons the crop-stage models are checked against, from Open-Meteo's archive (ERA5).

Yang et al. (2004) Table 1: maize at Lincoln, Nebraska (1999–2001) and Manchester, Iowa (2002). Setiyono et al. (2007)
Table 3: soybean NE3001 at Lincoln (1999–2002, 2004, 2005). Writes `phenology_weather.csv` (site, date, min, max and
mean temperature in °C), April through October.

Run: `uv run python packages/agmodels/tests/fixtures/make_phenology_weather.py`.
"""

import csv
from pathlib import Path

import requests

HERE = Path(__file__).parent
SITES = {
    "lincoln": (40.83, -96.67, (1999, 2000, 2001, 2002, 2004, 2005)),  # UNL's research farm, ~10 km NE of Lincoln
    "manchester": (42.48, -91.46, (2002,)),
}

rows = []
for site, (lat, lon, years) in SITES.items():
    for year in years:
        response = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": f"{year}-04-01",
                "end_date": f"{year}-10-31",
                "daily": "temperature_2m_min,temperature_2m_max,temperature_2m_mean",
                "timezone": "America/Chicago",
            },
            timeout=60,
        )
        response.raise_for_status()
        daily = response.json()["daily"]
        for date, lo, hi, mean in zip(
            daily["time"],
            daily["temperature_2m_min"],
            daily["temperature_2m_max"],
            daily["temperature_2m_mean"],
            strict=True,
        ):
            rows.append((site, date, lo, hi, mean))

with (HERE / "phenology_weather.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["site", "date", "temperature_min", "temperature_max", "temperature_mean"])
    writer.writerows(rows)
print(len(rows), "rows")
