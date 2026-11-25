// Ported from WISP 3 (adapted): app/frontend/lib/fieldInfo.ts
import { glossaryEntry, type GlossaryEntry } from './glossary'
import type { Units } from './units'

// The info tips on form inputs, one per form and input: `site.biofix` says what the biofix input is
// for in that form, not what a biofix is. Tips are plain words, at most two sentences
// (fieldInfo.test.ts), for what the input does here and when to change it; a hint that must be read
// before typing stays under the box instead. Where the input's label is a glossary term, `term` adds
// its definition below the tip. When two forms ask the same thing for the same reason, both name one
// shared entry, so this module lists every tip in the app. A tip that needs a value in the user's
// units is a function of them.

type Entry = {
  text: string | ((u: Units) => string)
  /** A glossary id: its definition is shown below the tip */
  term?: string
}

export const FIELD_INFO = {
  'settings.units': {
    text: 'How AgWeather shows temperatures, rain, degree days and other amounts on every page in this browser. Downloads and the API keep their own units.',
  },
} as const satisfies Record<string, Entry>

export type FieldInfoKey = keyof typeof FIELD_INFO

export type Tip = { text: string; term?: GlossaryEntry }

export function fieldInfo(key: FieldInfoKey, u: Units): Tip {
  const entry: Entry = FIELD_INFO[key]
  const text = typeof entry.text === 'function' ? entry.text(u) : entry.text
  return { text, term: entry.term ? glossaryEntry(entry.term) : undefined }
}
