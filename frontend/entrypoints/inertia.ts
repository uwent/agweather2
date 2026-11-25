import { createInertiaApp, router } from '@inertiajs/svelte'

import '@/entrypoints/application.css'
import AppLayout from '@/layouts/AppLayout.svelte'
import AuthLayout from '@/layouts/AuthLayout.svelte'
import { NO_CONNECTION_NOTICE, SIGNED_OUT_NOTICE } from '@/lib/requestFailures'
import { watchHistoryMoves } from '@/lib/unsaved.svelte'

// As WISP 3's (app/frontend/entrypoints/inertia.ts), without its analytics

// Before Inertia listens for Back and Forward, so unsaved changes can be asked about first
watchHistoryMoves()

createInertiaApp({
  pages: '../pages',

  // Sign-in and the other signed-out pages (Phase 7's accounts) use the centered card layout
  layout: (name) => (name.startsWith('Auth/') ? AuthLayout : AppLayout),

  title: (title) => (title ? `${title} · AgWeather` : 'AgWeather'),

  progress: { color: 'var(--color-brand-500)' },

  defaults: {
    form: {
      forceIndicesArrayFormatInFormData: false,
      withAllErrors: true,
    },
  },
})

const alert = (message: string) => router.flash({ messages: [{ level: 'error', message }] })

// A request that never reached AgWeather (no signal at the field's edge) says so, where Inertia would
// do nothing: the page and what's typed on it stay as they are, to try again
router.on('networkError', () => {
  alert(NO_CONNECTION_NOTICE)
  return false
})

// A save after the session ended is answered 401, which leaves the page and what's typed on it in
// place, where a redirect to sign in would drop it
router.on('httpException', (event) => {
  if (event.detail.response.status !== 401) return
  alert(SIGNED_OUT_NOTICE)
  return false
})
