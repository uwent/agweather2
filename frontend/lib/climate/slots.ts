// Requests a page sends a few at a time (track 6.2): the Climate tab's sections each take 1–4 s of the server's
// time, so they queue for two slots rather than all asking at once and meeting the rate limit together. A task
// waits for a free slot, runs, and frees it however it ends; one cancelled while it waits (its signal aborted)
// leaves the queue with an AbortError (`isAbort`), as a cancelled request does.
//
//   const body = await climateSlots.run(signal, () => get<TableResponse>('/climate/normals', params, { signal }))

export type Slots = {
  run<T>(signal: AbortSignal | undefined, task: () => Promise<T>): Promise<T>
  /** Tasks running now, and waiting (for tests) */
  readonly busy: number
  readonly waiting: number
}

export function slots(limit: number): Slots {
  let busy = 0
  const queue: (() => void)[] = []

  function next() {
    while (busy < limit && queue.length) queue.shift()!()
  }

  return {
    run<T>(signal: AbortSignal | undefined, task: () => Promise<T>): Promise<T> {
      if (signal?.aborted) return Promise.reject(cancelled())
      return new Promise<T>((resolve, reject) => {
        const start = () => {
          signal?.removeEventListener('abort', leave)
          busy += 1
          task()
            .then(resolve, reject)
            .finally(() => {
              busy -= 1
              next()
            })
        }
        const leave = () => {
          const at = queue.indexOf(start)
          if (at >= 0) queue.splice(at, 1)
          reject(cancelled())
        }
        signal?.addEventListener('abort', leave, { once: true })
        queue.push(start)
        next()
      })
    },
    get busy() {
      return busy
    },
    get waiting() {
      return queue.length
    },
  }
}

const cancelled = () => new DOMException('The request was cancelled.', 'AbortError')

/** The climate sections' two slots, shared by every section on the page */
export const climateSlots = slots(2)
