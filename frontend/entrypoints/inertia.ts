import { createInertiaApp } from '@inertiajs/svelte'

import '@/entrypoints/application.css'
import AppLayout from '@/layouts/AppLayout.svelte'

createInertiaApp({
  pages: '../pages',

  layout: () => AppLayout,

  title: (title) => (title ? `${title} · AgWeather` : 'AgWeather'),

  progress: { color: 'var(--color-brand-500)' },

  defaults: {
    form: {
      forceIndicesArrayFormatInFormData: false,
      withAllErrors: true,
    },
  },
})
