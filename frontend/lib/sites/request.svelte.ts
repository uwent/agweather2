// A section's request on the site page, as state a component reads: loading, its answer, or the failure in the
// API's words with whether trying again could help. Each `load` supersedes the last (lib/api's latestRequests),
// so a setting changed quickly never shows an older answer over a newer one.

import { ApiError, isAbort, latestRequests, NETWORK_MESSAGE } from '../api'

export type Loaded<T> =
  | { status: 'loading'; data: T | null }
  | { status: 'done'; data: T }
  | { status: 'failed'; data: T | null; message: string; retryable: boolean; retryAfter: number | null }

export function request<T>() {
  const latest = latestRequests()
  const state = $state<{ value: Loaded<T> }>({ value: { status: 'loading', data: null } })
  return {
    get value() {
      return state.value
    },
    /** Starts `fetch`, keeping the last answer on screen while the new one loads */
    async load(fetch: (signal: AbortSignal) => Promise<T>): Promise<void> {
      state.value = { status: 'loading', data: state.value.data }
      try {
        const data = await latest.run('load', fetch)
        state.value = { status: 'done', data }
      } catch (error) {
        if (isAbort(error)) return
        const failure = error instanceof ApiError ? error : null
        state.value = {
          status: 'failed',
          data: state.value.data,
          message: failure?.message ?? NETWORK_MESSAGE,
          retryable: failure?.retryable ?? true,
          retryAfter: failure?.retryAfter ?? null,
        }
      }
    },
    cancel: () => latest.cancel(),
  }
}

export type Request<T> = ReturnType<typeof request<T>>
