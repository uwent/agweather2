// Ported from WISP 3: app/frontend/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/svelte'
import { afterEach } from 'vitest'

// Under the vmThreads pool, jsdom's window.performance lacks getEntriesByType,
// which Inertia calls when it's imported to tell a reload from a navigation.
window.performance.getEntriesByType ??= () => []

afterEach(() => cleanup())
