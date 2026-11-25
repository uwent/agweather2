// Ported from WISP 3 (adapted): app/frontend/lib/requestFailures.ts
// What a page says when a request fails before AgWeather can answer it (entrypoints/inertia.ts)

export const NO_CONNECTION_NOTICE =
  "We couldn't reach AgWeather, so nothing was saved or loaded. Check your connection and try again."

export const SIGNED_OUT_NOTICE =
  "You've been signed out, so that wasn't saved. Sign in again in another tab, then come back to this page and save again."
