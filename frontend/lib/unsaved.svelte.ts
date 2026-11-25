// Ported from WISP 3: app/frontend/lib/unsaved.svelte.ts
import { router } from '@inertiajs/svelte'

import { type Change, ChangeTracker, describeChanges } from '@/lib/formChanges'

export const UNSAVED_MESSAGE = 'You have unsaved changes. Leave this page without saving them?'

/** The confirm's text: the changes listed when the form's are known, else the plain question */
export function unsavedMessage(tracker?: ChangeTracker): string {
  return changesMessage(tracker ? tracker.changes() : []) ?? UNSAVED_MESSAGE
}

/** A confirm listing changes before leaving them (a page, or a dialog's form), or null without any */
export function changesMessage(changes: Change[], leaving = 'this page'): string | null {
  const lines = describeChanges(changes)
  if (!lines.length) return null
  return `You have unsaved changes:\n\n${lines.map((line) => `• ${line}`).join('\n')}\n\nLeave ${leaving} without saving them?`
}

// Back and Forward. Inertia shows the other page from the browser's history without a visit, so
// there's no `before` to stop, and its own popstate listener can only be kept from the event by
// one added before it: listeners on the window run in the order they were added. So one listener
// is added as the app starts (watchHistoryMoves, before Inertia's), and pages and dialogs give it
// their questions while they have something to lose (confirmHistoryMoves).
let questions: (() => string | null)[] = []

// The Navigation API, where the browser has it, says which entry a Back or Forward left, to go
// back to it
type NavigationEntry = { index: number }
type Navigation = {
  currentEntry?: NavigationEntry | null
  addEventListener(type: 'currententrychange', listener: (event: { from?: NavigationEntry }) => void): void
}
const navigation = () => (globalThis as { navigation?: Navigation }).navigation

/**
 * Listens for the browser's Back and Forward ahead of Inertia: call once, before the Inertia app is
 * created. While a page or dialog has unsaved changes (confirmHistoryMoves) it asks first; told to
 * stay, it keeps the event from Inertia and steps back to the entry it left, whose own popstate is
 * swallowed the same way. Nothing was re-rendered, so what's typed is as it was.
 */
export function watchHistoryMoves() {
  let left: number | undefined
  navigation()?.addEventListener('currententrychange', (event) => (left = event.from?.index))
  let returning = false
  let giveUp: ReturnType<typeof setTimeout> | undefined
  addEventListener(
    'popstate',
    (event) => {
      if (returning) {
        returning = false
        clearTimeout(giveUp)
        event.stopImmediatePropagation()
        return
      }
      // An entry without state is a link within the page (#…), which Inertia doesn't redraw
      if (event.state === null) return
      const text = questions.map((question) => question()).find((asked) => asked !== null)
      if (text === undefined || confirm(text)) return
      event.stopImmediatePropagation()
      returning = true
      // If the step back goes nowhere, the next Back or Forward is a real one
      clearTimeout(giveUp)
      giveUp = setTimeout(() => (returning = false), 1000)
      const now = navigation()?.currentEntry?.index
      // Without the Navigation API, it was most likely Back
      history.go(left !== undefined && now !== undefined && left !== now ? left - now : 1)
    },
    { capture: true },
  )
}

/**
 * Asks before the browser's Back or Forward leaves the page (watchHistoryMoves): question gives the
 * confirm's text while there's something to lose, else null. Returns the cleanup.
 */
export function confirmHistoryMoves(question: () => string | null): () => void {
  questions.push(question)
  return () => {
    questions = questions.filter((other) => other !== question)
  }
}

/**
 * Asks before leaving a page with unsaved changes: links and other Inertia visits get a confirm,
 * listing what changed in `form` (an element holding the page's form, looked up when asked), as do
 * the browser's Back and Forward (confirmHistoryMoves), and closing or reloading the tab gets the
 * browser's own prompt (its text can't be changed). Submitting the form (any non-GET visit) isn't
 * stopped, nor is a reload of the page's data in place, which keeps what's typed. Call during
 * component setup; it's removed with the component. Returns the message, for a page that asks on
 * its own too.
 */
export function confirmUnsavedChanges(isDirty: () => boolean, form?: () => Element | null | undefined) {
  const tracker = form ? new ChangeTracker(form, () => !isDirty()) : undefined
  $effect(() => {
    tracker?.start()
    const offBefore = router.on('before', (event) => {
      const { visit } = event.detail
      if (visit.method !== 'get' || !isDirty()) return
      if (visit.preserveState === true && visit.url.pathname === location.pathname) return
      if (!confirm(unsavedMessage(tracker))) return false
    })
    const onUnload = (event: BeforeUnloadEvent) => {
      if (isDirty()) event.preventDefault()
    }
    addEventListener('beforeunload', onUnload)
    const offHistory = confirmHistoryMoves(() => (isDirty() ? unsavedMessage(tracker) : null))
    return () => {
      tracker?.stop()
      offBefore()
      removeEventListener('beforeunload', onUnload)
      offHistory()
    }
  })
  return { message: () => unsavedMessage(tracker) }
}
