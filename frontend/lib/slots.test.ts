import { describe, expect, it } from 'vitest'

import { isAbort } from './api'
import { slots } from './slots'

// A promise and the functions that settle it
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0))

describe('slots', () => {
  it('runs two tasks at a time, starting the next as one ends however it ends', async () => {
    const queue = slots(2)
    const tasks = [deferred<number>(), deferred<number>(), deferred<number>(), deferred<number>()]
    const started: number[] = []
    const results = tasks.map((task, k) =>
      queue
        .run(undefined, () => {
          started.push(k)
          return task.promise
        })
        .catch((error: unknown) => error),
    )
    expect(started).toEqual([0, 1])
    expect(queue.waiting).toBe(2)
    tasks[1].reject(new Error('refused'))
    await tick()
    expect(started).toEqual([0, 1, 2])
    tasks[0].resolve(0)
    await tick()
    expect(started).toEqual([0, 1, 2, 3])
    tasks[2].resolve(2)
    tasks[3].resolve(3)
    expect(await Promise.all(results)).toEqual([0, new Error('refused'), 2, 3])
    expect(queue.busy).toBe(0)
  })

  it('drops a task cancelled while it waits, with an AbortError, and never starts it', async () => {
    const queue = slots(1)
    const first = deferred<string>()
    const controller = new AbortController()
    let ran = false
    void queue.run(undefined, () => first.promise)
    const waiting = queue.run(controller.signal, async () => {
      ran = true
      return 'late'
    })
    controller.abort()
    await expect(waiting).rejects.toSatisfy(isAbort)
    expect(queue.waiting).toBe(0)
    first.resolve('done')
    await tick()
    expect(ran).toBe(false)
    expect(queue.busy).toBe(0)
  })

  it('refuses a task whose signal is already aborted', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(slots(2).run(controller.signal, async () => 1)).rejects.toSatisfy(isAbort)
  })
})
