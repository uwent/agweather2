// The reader's choice of US or metric units (F10), from the settings dialog. Kept in this browser
// (lib/storage) until accounts hold it (D120, D122); every tab follows a change made in another.
// Reactive: lib/units.ts's currentUnits() reads it, so what's shown converts as soon as it changes.

import { readStored, writeStored } from './storage'
import type { UnitSystem } from './units'

export const UNITS_KEY = 'agweather-units'

const read = (): UnitSystem => (readStored(UNITS_KEY) === 'metric' ? 'metric' : 'imperial')

const state = $state<{ system: UnitSystem }>({ system: typeof localStorage === 'undefined' ? 'imperial' : read() })

if (typeof addEventListener !== 'undefined') {
  addEventListener('storage', (event) => {
    if (event.key === UNITS_KEY || event.key === null) state.system = read()
  })
}

export function unitSystem(): UnitSystem {
  return state.system
}

/** Saves the choice in this browser (for this page only when storage is blocked) */
export function setUnitSystem(system: UnitSystem) {
  state.system = system
  writeStored(UNITS_KEY, system)
}
