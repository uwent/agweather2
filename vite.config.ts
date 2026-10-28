import { svelte } from '@sveltejs/vite-plugin-svelte'
import inertia from '@inertiajs/vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const port = Number(process.env.VITE_PORT ?? 5173)

// django-vite (app/config/settings.py) loads entrypoints/inertia.ts from the dev server in development,
// and from the manifest of the build in app/static/vite otherwise. Both serve under /static/vite/.
export default defineConfig({
  root: 'frontend',
  base: '/static/vite/',
  plugins: [tailwindcss(), inertia(), svelte()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./frontend', import.meta.url)) },
  },
  server: {
    port,
    // Asset URLs (fonts, images) point at this server, not at the Django page that loaded them
    origin: `http://localhost:${port}`,
    strictPort: true,
    // Pages come from Django on :8000, which loads modules from here
    cors: { origin: /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/ },
  },
  build: {
    outDir: '../app/static/vite',
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: { input: fileURLToPath(new URL('./frontend/entrypoints/inertia.ts', import.meta.url)) },
  },
  // MapLibre's worker is an ES module
  worker: { format: 'es' },
})
