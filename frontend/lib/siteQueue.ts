// Requests for the sites page's cards: each card loads as it scrolls into view, and at most `limit` requests run at
// once (3), so a page of 50 sites doesn't spend the API's rate limit in one burst (track 3: 50 cards' /risk cost
// 150–500 of a minute's 200 units). A newer request under a key aborts the older one (lib/api's latestRequests), and
// a waiting request whose card went away is dropped before it starts (lib/slots.ts).
//
// `createBatcher` gathers the cards that come into view together into one request for up to `max` sites
// (`/weather/daily?points=` takes several), which then waits its turn in the same queue.

import { latestRequests } from './api'
import { slots } from './slots'

export type Task<T> = (signal: AbortSignal) => Promise<T>

export function createSiteQueue({ limit = 3 }: { limit?: number } = {}) {
  const latest = latestRequests()
  const queue = slots(limit)

  return {
    /** Runs `task` when a slot is free; a newer `run` under the same key aborts this one (it rejects with an
     * AbortError, `isAbort`), and one aborted while it waits is let go at once */
    run<T>(key: string, task: Task<T>): Promise<T> {
      return latest.run(key, (signal) => queue.run(signal, () => task(signal)))
    },
    /** Aborts the request under `key`, or every one (the page is leaving) */
    cancel(key?: string) {
      latest.cancel(key)
    },
    get running() {
      return queue.busy
    },
    get waiting() {
      return queue.waiting
    },
  }
}

export type SiteQueue = ReturnType<typeof createSiteQueue>

/** One request for several keys: `fetch` gets up to `max` keys that asked within `wait` ms of each other and returns
 * each one's answer (a key it leaves out gets undefined). A failure rejects every key in that batch. */
export function createBatcher<T>({
  queue,
  fetch,
  max = 10,
  wait = 30,
  name = 'batch',
}: {
  queue: SiteQueue
  fetch: (keys: string[], signal: AbortSignal) => Promise<Map<string, T>>
  max?: number
  wait?: number
  name?: string
}) {
  let pending: { key: string; resolve: (value: T | undefined) => void; reject: (error: unknown) => void }[] = []
  let timer: ReturnType<typeof setTimeout> | null = null
  let count = 0

  function flush() {
    if (timer) clearTimeout(timer)
    timer = null
    const batch = pending.slice(0, max)
    pending = pending.slice(max)
    if (pending.length) timer = setTimeout(flush, 0)
    if (!batch.length) return
    const keys = [...new Set(batch.map((item) => item.key))]
    queue
      .run(`${name}:${count++}`, (signal) => fetch(keys, signal))
      .then(
        (found) => batch.forEach((item) => item.resolve(found.get(item.key))),
        (error) => batch.forEach((item) => item.reject(error)),
      )
  }

  return {
    load(key: string): Promise<T | undefined> {
      return new Promise((resolve, reject) => {
        pending.push({ key, resolve, reject })
        if (pending.length >= max) flush()
        else timer ??= setTimeout(flush, wait)
      })
    },
  }
}
