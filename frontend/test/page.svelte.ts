// Ported from WISP 3 (adapted): app/frontend/test/page.svelte.ts
import type { FlashData } from '@/types'

// A reactive stand-in for Inertia's `page`, so a component test can change its
// props after mounting: vi.mock('@inertiajs/svelte', () => import('@/test/page.svelte'))
export const page = $state({
  url: '/',
  component: 'Home',
  flash: {} as FlashData,
  props: { app: { version: 'dev', service_box: 'wisconsin' }, today: '2026-07-01' },
})

// What a component may call on Inertia's router: nothing happens in a test
export const router = {
  on: () => () => {},
  visit: () => {},
  flash: () => {},
}
