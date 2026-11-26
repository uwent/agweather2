// The changelog's announcement banners (the shared `announcements` prop, from `ChangelogEntry.banners()`): shown on
// every page until the entry's `banner_until`, and dismissed per entry in this browser (lib/storage), so a reader who
// closes one doesn't see it again while a newer one still shows.

import type { AnnouncementProps } from '@/types'

import { readStored, writeStored } from './storage'

export const DISMISSED_KEY = 'announcements:dismissed'

/** The entries this browser has dismissed, by id */
export function dismissedIds(): number[] {
  const found = readStored(DISMISSED_KEY)
  return Array.isArray(found) ? found.filter((id): id is number => typeof id === 'number') : []
}

/** Remembers an entry as dismissed, keeping only the ids still shown (`current`) so the list doesn't grow */
export function dismiss(id: number, current: number[]): number[] {
  const kept = [...new Set([...dismissedIds().filter((k) => current.includes(k)), id])]
  writeStored(DISMISSED_KEY, kept)
  return kept
}

/** The announcements still to show: not dismissed, and not past their time (a page kept open past it) */
export function shown(announcements: AnnouncementProps[], dismissed: number[], now: Date): AnnouncementProps[] {
  return announcements.filter((a) => !dismissed.includes(a.id) && new Date(a.until).getTime() > now.getTime())
}
