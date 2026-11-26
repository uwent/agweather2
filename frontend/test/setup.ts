// Ported from WISP 3: app/frontend/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/svelte'
import { afterEach } from 'vitest'

// Under the vmThreads pool, jsdom's window.performance lacks getEntriesByType,
// which Inertia calls when it's imported to tell a reload from a navigation.
window.performance.getEntriesByType ??= () => []

// jsdom has no matchMedia, which every browser has: a chart that finishes loading ECharts reads the theme through
// it (lib/theme.ts), and without it the rejection fails the run after the test that rendered the chart has passed.
// Nothing matches: light mode, motion allowed, no hover.
window.matchMedia ??= (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList

// Nor ResizeObserver, which the chart watches its box with
window.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

afterEach(() => cleanup())
