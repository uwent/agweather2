import { svelte } from '@sveltejs/vite-plugin-svelte'
import inertia from '@inertiajs/vite'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Django integration (django-vite: manifest, dev server origin, build output) lands in Phase 1 B
export default defineConfig({
  root: 'frontend',
  plugins: [tailwindcss(), inertia(), svelte()],
  // MapLibre's worker is an ES module
  worker: { format: 'es' },
})
