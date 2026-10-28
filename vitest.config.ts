import { fileURLToPath } from 'node:url'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vitest/config'

// Separate from vite.config.ts so component tests don't need the Django integration
export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./frontend', import.meta.url)) },
    conditions: ['browser'],
  },
  test: {
    environment: 'jsdom',
    include: ['frontend/**/*.test.ts'],
    setupFiles: ['frontend/test/setup.ts'],
    passWithNoTests: true,
  },
})
