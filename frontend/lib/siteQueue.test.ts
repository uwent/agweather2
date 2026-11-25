import { describe, expect, it, vi } from 'vitest'

import { isAbort } from './api'
import { createBatcher, createSiteQueue } from './siteQueue'

/** A task that waits until released, recording that it started */
function held(started: string[], key: string) {
  let release!: (value: string) => void
  const done = new Promise<string>((resolve) => (release = resolve))
  return {
    task: (signal: AbortSignal) => {
      started.push(key)
      return new Promise<string>((resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
        done.then(resolve)
      })
    },
    release: () => release(key),
  }
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0))

describe('createSiteQueue', () => {
  it('runs at most `limit` at once, the rest in turn as slots free', async () => {
    const queue = createSiteQueue({ limit: 3 })
    const started: string[] = []
    const tasks = ['a', 'b', 'c', 'd', 'e'].map((key) => ({ key, ...held(started, key) }))
    const results = tasks.map((t) => queue.run(t.key, t.task))
    await settle()
    expect(started).toEqual(['a', 'b', 'c'])
    expect([queue.running, queue.waiting]).toEqual([3, 2])
    tasks[1].release()
    await settle()
    expect(started).toEqual(['a', 'b', 'c', 'd'])
    for (const t of tasks) t.release()
    expect(await Promise.all(results)).toEqual(['a', 'b', 'c', 'd', 'e'])
    expect([queue.running, queue.waiting]).toEqual([0, 0])
  })

  it('aborts an older request under the same key, and drops a waiting one that’s cancelled', async () => {
    const queue = createSiteQueue({ limit: 1 })
    const started: string[] = []
    const first = held(started, 'first')
    const waiting = held(started, 'waiting')
    const running = queue.run('a', first.task)
    const queued = queue.run('b', waiting.task)
    queue.cancel('b')
    await expect(queued).rejects.toSatisfy(isAbort)
    const newer = held(started, 'newer')
    const replaced = queue.run('a', newer.task)
    await expect(running).rejects.toSatisfy(isAbort)
    newer.release()
    expect(await replaced).toBe('newer')
    expect(started).toEqual(['first', 'newer'])
  })
})

describe('createBatcher', () => {
  it('gathers keys asked together into one request of at most `max`', async () => {
    vi.useFakeTimers()
    const queue = createSiteQueue({ limit: 3 })
    const fetch = vi.fn(async (keys: string[]) => new Map(keys.map((k) => [k, k.toUpperCase()])))
    const batcher = createBatcher({ queue, fetch, max: 2, wait: 30 })
    const answers = Promise.all(['a', 'b', 'c'].map((key) => batcher.load(key)))
    await vi.advanceTimersByTimeAsync(50)
    expect(await answers).toEqual(['A', 'B', 'C'])
    expect(fetch.mock.calls.map((call) => call[0])).toEqual([['a', 'b'], ['c']])
    vi.useRealTimers()
  })

  it('rejects every key of a batch that failed', async () => {
    const queue = createSiteQueue()
    const batcher = createBatcher<string>({ queue, fetch: () => Promise.reject(new Error('busy')), wait: 0 })
    await expect(Promise.all([batcher.load('a'), batcher.load('b')])).rejects.toThrow('busy')
  })
})
