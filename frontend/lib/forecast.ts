// WISP 3: app/frontend/lib/forecast.ts (adapted: our API has no weather code, so a day's sky is worded from its
// precipitation, high temperature and mean cloud cover)
//
// The days around today in brief (ForecastStrip): each day's sky in words and as an icon.

import { addDays } from './dates'

export type Sky = 'clear' | 'partly' | 'cloudy' | 'rain' | 'showers' | 'snow'

export type SkyWords = { sky: Sky; label: string }

/** A day's values in the API's metric units (`units=metric`): millimeters, °C, percent */
export type SkyInputs = {
  precipitation_mm: number | null
  high_c: number | null
  cloud_cover_percent: number | null
}

// A tenth of an inch is a rainy day; a hundredth, showers (WISP 3's thresholds, in millimeters)
const RAINY_MM = 2.54
const SHOWERS_MM = 0.254

/** By the day's mean cloud cover (percent) */
function clouds(cover: number): SkyWords {
  if (cover < 20) return { sky: 'clear', label: 'Sunny' }
  if (cover < 50) return { sky: 'partly', label: 'Mostly sunny' }
  if (cover < 80) return { sky: 'partly', label: 'Partly cloudy' }
  return { sky: 'cloudy', label: 'Cloudy' }
}

/**
 * The day's sky in words: precipitation first (snow when the high stays at or below freezing), then cloud cover;
 * null with nothing to go on.
 */
export function skyFor(day: SkyInputs): SkyWords | null {
  const precipitation = day.precipitation_mm ?? 0
  const frozen = day.high_c !== null && day.high_c <= 0
  if (precipitation >= RAINY_MM) return frozen ? { sky: 'snow', label: 'Snow' } : { sky: 'rain', label: 'Rain' }
  if (precipitation >= SHOWERS_MM)
    return frozen ? { sky: 'snow', label: 'Light snow' } : { sky: 'showers', label: 'Light showers' }
  if (day.cloud_cover_percent !== null) return clouds(day.cloud_cover_percent)
  return null
}

const weekdays = new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', weekday: 'short' })

/** "Today", "Yesterday", "Tomorrow" or "Thu" ("Today" or "Thu" when short) */
export function dayName(iso: string, today: string, { short = false }: { short?: boolean } = {}): string {
  if (iso === today) return 'Today'
  if (!short && iso === addDays(today, 1)) return 'Tomorrow'
  if (!short && iso === addDays(today, -1)) return 'Yesterday'
  return weekdays.format(new Date(`${iso}T00:00:00Z`))
}
