// Ported from WISP 3: app/frontend/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/svelte'
import { afterEach, vi } from 'vitest'

// Under the vmThreads pool, jsdom's window.performance lacks getEntriesByType,
// which Inertia calls when it's imported to tell a reload from a navigation.
window.performance.getEntriesByType ??= () => []

// ECharts can't draw in jsdom (no canvas), and Chart.svelte imports it after the page renders: a test that rendered
// a chart could end, and its environment be torn down, while ECharts still loaded, which failed the run with every
// test passed ("document is not defined", "matchMedia is not a function"). Component tests get a chart that does
// nothing; the option builders are tested as plain functions.
vi.mock('@/lib/charts/echarts', () => {
  // A class instance, not a plain object, so Svelte's $state keeps it as it is rather than proxying it
  class FakeChart {
    getOption() {
      return {}
    }
  }
  const chart = new Proxy(new FakeChart(), {
    get: (target, name) => (name in target || name === 'then' ? Reflect.get(target, name) : () => undefined),
  })
  return { echarts: { init: () => chart, use: () => {} } }
})

// jsdom has no matchMedia, which every browser has (lib/theme.ts, lib/motion.ts). Nothing matches: light mode,
// motion allowed, no hover.
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

// Nor ResizeObserver, which a chart watches its box with
window.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

afterEach(() => cleanup())
