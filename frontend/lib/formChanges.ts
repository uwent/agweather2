// Ported from WISP 3: app/frontend/lib/formChanges.ts
import { formatDate } from '@/lib/dates'

// What the user changed in a form, worded as they see it ("Area: 40 ac → 30 ac"), for the prompts
// that ask before dropping changes: a dialog's own prompt and a page's confirm. Read
// from the form's visible, labelled controls, so a form needs no list of its own.
//
// Only controls the user changed are listed: by typing or picking in them (an input or change event;
// Svelte setting a value sends none), or through a button they pressed (the value a "Use 38.2 ac" button fills in). A value the form sets itself (the soil
// survey's suggestion arriving) isn't the user's, so each control's starting value is taken again
// at every press or key until the user changes it.

export type Change = {
  label: string
  from: string
  to: string
  /** Notes: listed as "Notes: changed" rather than both texts */
  long: boolean
  /** To give focus back to (Keep editing) */
  control: HTMLElement
}

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
type Reading = { label: string; value: string; long: boolean; control: Control }

const NONE = 'None'
const SKIPPED_TYPES = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'file'])

/** A label's own words: without the controls inside it, its muted asides and hidden extras */
function words(element: Element | null | undefined): string {
  if (!element) return ''
  const copy = element.cloneNode(true) as Element
  copy
    .querySelectorAll('input, select, textarea, button, .text-ink-muted, [data-change-ignore]')
    .forEach((node) => node.remove())
  return (copy.textContent ?? '').replace(/\s+/g, ' ').trim()
}

function labelOf(control: Control): string {
  const labelledBy = control.getAttribute('aria-labelledby')
  return (
    words(control.labels?.[0]) ||
    control.getAttribute('aria-label')?.trim() ||
    (labelledBy ? words(document.getElementById(labelledBy)) : '') ||
    ''
  )
}

/** A radio group's name: its radiogroup's label, else its fieldset's legend */
function groupLabelOf(radio: HTMLInputElement): string {
  const group = radio.closest('[role="radiogroup"]')
  const named = group?.getAttribute('aria-label')?.trim()
  if (named) return named
  const fieldset = radio.closest('fieldset')
  return words(fieldset?.querySelector(':scope > legend')) || labelOf(radio)
}

function shown(control: Control): boolean {
  if (control.disabled || control.closest('[hidden], [inert]')) return false
  return !(control instanceof HTMLInputElement && SKIPPED_TYPES.has(control.type))
}

/** One key per control the user sees (a radio group is one), the same while the form is open */
function keyOf(control: Control): string {
  if (control instanceof HTMLInputElement && control.type === 'radio') return `radio:${control.name}`
  if (control.id) return `#${control.id}`
  if (control instanceof HTMLInputElement && control.type === 'checkbox')
    return `checkbox:${control.name}:${control.value}`
  return control.name ? `name:${control.name}` : `label:${labelOf(control)}`
}

function valueOf(control: Control): string {
  if (control instanceof HTMLSelectElement) {
    const text = [...control.selectedOptions].map((option) => option.textContent?.trim() ?? '').join(', ')
    return text || NONE
  }
  if (control instanceof HTMLTextAreaElement) return control.value.trim() || NONE
  if (control.type === 'checkbox') return control.checked ? 'Yes' : 'No'
  const unit = control.dataset.unit
  // A blank box standing for a default (NumberField's blankValue) reads as that default
  const value = control.value.trim() || control.dataset.blank || ''
  if (!value) return NONE
  if (control.type === 'date') return formatDate(value, { year: true })
  return unit ? `${value} ${unit}` : value
}

/** The form's visible, labelled controls, by key */
export function readControls(root: ParentNode): Map<string, Reading> {
  const readings = new Map<string, Reading>()
  for (const control of root.querySelectorAll<Control>('input, select, textarea')) {
    if (!shown(control)) continue
    const key = keyOf(control)
    if (control instanceof HTMLInputElement && control.type === 'radio') {
      const existing = readings.get(key)
      if (existing && existing.value !== NONE) continue
      const label = groupLabelOf(control)
      if (!label) continue
      const value = control.checked
        ? words(control.labels?.[0]) || control.getAttribute('aria-label') || control.value
        : NONE
      readings.set(key, { label, value, long: false, control: existing?.control ?? control })
      continue
    }
    const label = labelOf(control)
    if (!label) continue
    readings.set(key, { label, value: valueOf(control), long: control instanceof HTMLTextAreaElement, control })
  }
  return readings
}

/**
 * Follows a form for what the user changes in it. `root` gives the element holding it (a dialog's
 * body, a page's form), looked up at each event, so the form may be remounted; a new form inside it
 * starts afresh. `clean` says the owner has nothing unsaved (after a save), which starts afresh too.
 */
export class ChangeTracker {
  #root: () => Element | null | undefined
  #clean: () => boolean
  #form: Element | null = null
  #start = new Map<string, string>()
  #changed = new Set<string>()
  #off: (() => void) | null = null

  constructor(root: () => Element | null | undefined, clean: () => boolean = () => false) {
    this.#root = root
    this.#clean = clean
  }

  /** Listens on the document (removed by stop) */
  start(doc: Document = document) {
    this.stop()
    const within = (event: Event) => {
      const root = this.#root()
      return root && event.target instanceof Node && root.contains(event.target) ? root : null
    }
    // Before the user acts: the values they see now are where their changes start from
    const before = (event: Event) => {
      const root = within(event)
      if (root) this.#refresh(root)
    }
    const changed = (event: Event) => {
      if (!within(event)) return
      const target = event.target as Control
      if (target.matches?.('input, select, textarea') && shown(target)) this.#changed.add(keyOf(target))
    }
    // A button that fills in values (Use 38.2 ac, Use Sand): whatever moved once it has run
    const pressed = (event: Event) => {
      const root = within(event)
      const button = (event.target as Element).closest?.('button, [role="button"]')
      if (!root || !button || (button as HTMLButtonElement).type === 'submit') return
      setTimeout(() => {
        // A button that swapped the form for another (Add the next planting) starts afresh
        if ((root.querySelector('form') ?? root) !== this.#form) return this.#refresh(root)
        for (const [key, reading] of readControls(root)) {
          if (this.#start.has(key) && this.#start.get(key) !== reading.value) this.#changed.add(key)
        }
      })
    }
    doc.addEventListener('pointerdown', before, true)
    doc.addEventListener('keydown', before, true)
    doc.addEventListener('focusin', before, true)
    doc.addEventListener('input', changed, true)
    doc.addEventListener('change', changed, true)
    doc.addEventListener('click', pressed, true)
    this.#off = () => {
      doc.removeEventListener('pointerdown', before, true)
      doc.removeEventListener('keydown', before, true)
      doc.removeEventListener('focusin', before, true)
      doc.removeEventListener('input', changed, true)
      doc.removeEventListener('change', changed, true)
      doc.removeEventListener('click', pressed, true)
    }
    const root = this.#root()
    if (root) this.#refresh(root)
  }

  stop() {
    this.#off?.()
    this.#off = null
  }

  /** Forgets every change: the values shown now are the starting point */
  reset() {
    this.#changed.clear()
    this.#start.clear()
    this.#form = null
    const root = this.#root()
    if (root) this.#refresh(root)
  }

  #refresh(root: Element) {
    const form = root.querySelector('form') ?? root
    if (form !== this.#form || this.#clean()) {
      this.#form = form
      this.#changed.clear()
      this.#start.clear()
    }
    for (const [key, reading] of readControls(root)) {
      if (!this.#changed.has(key)) this.#start.set(key, reading.value)
    }
  }

  /** What the user changed, in the form's order */
  changes(): Change[] {
    const root = this.#root()
    if (!root || this.#clean()) return []
    const list: Change[] = []
    for (const [key, reading] of readControls(root)) {
      if (!this.#changed.has(key)) continue
      const from = this.#start.get(key) ?? NONE
      if (from !== reading.value)
        list.push({ label: reading.label, from, to: reading.value, long: reading.long, control: reading.control })
    }
    return list
  }
}

/** "Area: 40 ac → 30 ac"; a new value alone ("Name: North 40"); notes as "Notes: changed" */
export function describeChange({ label, from, to, long }: Change): string {
  if (long) return `${label}: changed`
  if (from === NONE) return `${label}: ${to}`
  return `${label}: ${from} → ${to}`
}

/** The changes as lines, a long list cut to `max` lines ending "and 4 more" */
export function describeChanges(changes: Change[], max = 6): string[] {
  const lines = changes.map(describeChange)
  return lines.length <= max ? lines : [...lines.slice(0, max - 1), `and ${lines.length - (max - 1)} more`]
}
