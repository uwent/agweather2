// The status page's props and /api/v2/status's answer, as the development archive gave them (2026-11-26)
import type { StatusSource } from '@/types'
import type { StatusData } from '@/types/api'

export const SOURCES: StatusSource[] = [
  {
    id: 'urma',
    name: 'URMA (Unrestricted Mesoscale Analysis), NOAA',
    url: 'https://example.org/urma',
    provides: 'Temperature, humidity, wind and precipitation',
    normal_lag_hours: 14,
  },
  {
    id: 'rtma',
    name: 'RTMA (Real-Time Mesoscale Analysis), NOAA',
    url: 'https://example.org/rtma',
    provides: 'The newest hours of temperature, humidity, wind and precipitation, until URMA’s arrive',
    normal_lag_hours: 4,
  },
  {
    id: 'hrrr',
    name: 'HRRR (High-Resolution Rapid Refresh), NOAA',
    url: 'https://example.org/hrrr',
    provides: 'Solar radiation',
    normal_lag_hours: 4,
  },
  {
    id: 'era5land',
    name: 'ERA5-Land, ECMWF (Copernicus Climate Change Service)',
    url: 'https://example.org/era5',
    provides: 'Soil temperature, soil moisture and snow depth',
    normal_lag_hours: 168,
  },
]

export function report(overrides: Partial<StatusData> = {}): StatusData {
  return {
    service: 'agweather',
    version: 'dev',
    service_box: 'upper_midwest',
    archive: {
      first_hour: '2016-01-01T00:00Z',
      last_hour_by_source: {
        urma: '2026-11-25T21:00Z',
        rtma: '2026-11-26T04:00Z',
        hrrr: '2026-11-26T04:00Z',
        era5land: '2026-11-21T01:00Z',
      },
      daily_through: '2026-11-24',
      stale: [],
      refreshed_at: '2026-11-26T04:20Z',
    },
    forecast: {
      cycle: '2026-11-26T01:00Z',
      last_hour: '2026-12-07T01:00Z',
      in_use: true,
      reason: null,
      fallback: null,
    },
    models: 56,
    downloads: { files: 674, built_at: '2026-11-26T04:04:04+00:00' },
    gaps: {
      first: '2026-10-27',
      last: '2026-11-25',
      variables: [
        { variable: 'air_temperature', sources: ['rtma', 'urma'], days: [] },
        { variable: 'precipitation', sources: ['rtma', 'urma'], days: [] },
      ],
    },
    ...overrides,
  }
}
