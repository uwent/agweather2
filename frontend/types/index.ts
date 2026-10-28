import type { SharedProps } from './generated/props'
export type * from './generated/props'

// Django's messages framework, as inertia-django sends it on page.flash
export type FlashData = {
  messages?: { level: 'debug' | 'info' | 'success' | 'warning' | 'error'; message: string }[]
}

// Every page also gets the last form's validation errors, keyed by input name (web/inertia.py)
export type { SharedProps }
