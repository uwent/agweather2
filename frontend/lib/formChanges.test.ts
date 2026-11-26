// Ported from WISP 3: app/frontend/lib/formChanges.test.ts
import { afterEach, describe, expect, it } from 'vitest'

import { ChangeTracker, describeChange, describeChanges, readControls } from './formChanges'

// A form shaped like Setup's: NumberField (a visible box marked with its unit, a hidden stored
// value), a select, a radio group under a legend, a checkbox, a date and notes
function mount(html: string) {
  const root = document.createElement('div')
  root.innerHTML = `<form>${html}</form>`
  document.body.append(root)
  return root
}

const FIELD = `
  <label for="name">Name</label><input id="name" name="field[name]" value="North 40">
  <label for="area">Area</label><input id="area" type="text" value="40" data-unit="ac">
  <span>ac</span><input type="hidden" name="field[area_acres]" value="40">
  <label for="soil">Soil</label>
  <select id="soil" name="field[soil_type_id]">
    <option value="1" selected>Sand</option><option value="2">Loamy sand</option>
  </select>
  <fieldset><legend>Planting size</legend>
    <label><input type="radio" name="size" value="whole" checked> Whole field <span class="text-ink-muted">(40 ac)</span></label>
    <label><input type="radio" name="size" value="part"> Part of the field</label>
  </fieldset>
  <label><input type="checkbox" name="soil_own" value="1" checked> Use the field's soil</label>
  <label for="end">Harvest</label><input id="end" type="date" value="2026-09-15">
  <label for="notes">Notes</label><textarea id="notes">Sandy knoll</textarea>
  <label for="gone">Disabled</label><input id="gone" disabled value="x">
  <div hidden><label for="secret">Hidden</label><input id="secret" value="y"></div>
`

/** As a user would: press or key first, then the value, then the event */
function type(control: HTMLInputElement | HTMLTextAreaElement, value: string) {
  control.dispatchEvent(new Event('pointerdown', { bubbles: true }))
  control.value = value
  control.dispatchEvent(new Event('input', { bubbles: true }))
}
function pick(control: HTMLSelectElement | HTMLInputElement, set: () => void) {
  control.dispatchEvent(new Event('pointerdown', { bubbles: true }))
  set()
  control.dispatchEvent(new Event('change', { bubbles: true }))
}

let tracker: ChangeTracker | undefined
afterEach(() => {
  tracker?.stop()
  document.body.innerHTML = ''
})

function track(root: Element, clean?: () => boolean) {
  tracker = new ChangeTracker(() => root, clean)
  tracker.start()
  return tracker
}

const $ = <T extends Element>(root: Element, selector: string) => root.querySelector<T>(selector)!

describe('readControls', () => {
  it('reads what the user sees: labels, shown values and units, skipping hidden and disabled controls', () => {
    const root = mount(FIELD)
    const read = [...readControls(root).values()].map(({ label, value }) => `${label}=${value}`)
    expect(read).toEqual([
      'Name=North 40',
      'Area=40 ac',
      'Soil=Sand',
      'Planting size=Whole field',
      "Use the field's soil=Yes",
      'Harvest=Sep 15, 2026',
      'Notes=Sandy knoll',
    ])
  })

  it('reads blank as None, and names a radio group by its aria-label', () => {
    const root = mount(`
      <label for="v">Variety</label><input id="v" value="">
      <div role="radiogroup" aria-label="Canopy method">
        <input type="radio" name="m" value="a" aria-label="Percent cover">
      </div>`)
    const read = [...readControls(root).values()].map(({ label, value }) => `${label}=${value}`)
    expect(read).toEqual(['Variety=None', 'Canopy method=None'])
  })
})

describe('ChangeTracker', () => {
  it('lists what the user changed, in the form order, worded in their units', () => {
    const root = mount(FIELD)
    const changes = track(root)
    type($(root, '#area'), '30')
    pick($(root, '#soil'), () => ($<HTMLSelectElement>(root, '#soil').value = '2'))
    pick($(root, 'input[value="part"]'), () => ($<HTMLInputElement>(root, 'input[value="part"]').checked = true))
    pick($(root, 'input[type="checkbox"]'), () => ($<HTMLInputElement>(root, 'input[type="checkbox"]').checked = false))
    type($(root, '#end'), '2026-09-30')
    type($(root, '#notes'), 'Wet corner')
    expect(describeChanges(changes.changes(), 10)).toEqual([
      'Area: 40 ac → 30 ac',
      'Soil: Sand → Loamy sand',
      'Planting size: Whole field → Part of the field',
      "Use the field's soil: Yes → No",
      'Harvest: Sep 15, 2026 → Sep 30, 2026',
      'Notes: changed',
    ])
  })

  it('leaves out a value changed back, and values the form set itself', () => {
    const root = mount(FIELD)
    const changes = track(root)
    type($(root, '#area'), '30')
    type($(root, '#area'), '40')
    // The soil survey's suggestion arriving: no event
    $<HTMLSelectElement>(root, '#soil').value = '2'
    expect(changes.changes()).toEqual([])
  })

  it('starts a control from the value the form gave it before the user changed it', () => {
    const root = mount(FIELD)
    const changes = track(root)
    $<HTMLSelectElement>(root, '#soil').value = '2' // suggested
    pick($(root, '#soil'), () => ($<HTMLSelectElement>(root, '#soil').value = '1'))
    expect(describeChanges(changes.changes())).toEqual(['Soil: Loamy sand → Sand'])
  })

  it('counts what a pressed button fills in', async () => {
    const root = mount(`${FIELD}<button type="button" id="use">Use 38.2 ac</button>`)
    const changes = track(root)
    const button = $<HTMLButtonElement>(root, '#use')
    button.addEventListener('click', () => ($<HTMLInputElement>(root, '#area').value = '38.2'))
    button.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    button.click()
    await new Promise((resolve) => setTimeout(resolve))
    expect(describeChanges(changes.changes())).toEqual(['Area: 40 ac → 38.2 ac'])
  })

  it('starts afresh for a new form, and when its owner has nothing unsaved', () => {
    const root = mount(FIELD)
    let saved = false
    const changes = track(root, () => saved)
    type($(root, '#name'), 'North 41')
    expect(changes.changes()).toHaveLength(1)
    saved = true
    expect(changes.changes()).toEqual([])

    saved = false
    type($(root, '#name'), 'North 42')
    root.innerHTML = `<form>${FIELD}</form>` // remounted, as for the next planting
    type($(root, '#area'), '20')
    expect(describeChanges(changes.changes())).toEqual(['Area: 40 ac → 20 ac'])
  })

  it('ignores events outside its form', () => {
    const root = mount(FIELD)
    const other = mount(FIELD)
    const changes = track(root)
    type($(other, '#name'), 'Elsewhere')
    expect(changes.changes()).toEqual([])
  })
})

describe('describeChanges', () => {
  const change = (label: string, from = 'None', to = 'x') =>
    ({ label, from, to, long: false, control: document.body }) as const

  it('words a new value alone, and a cleared one as None', () => {
    expect(describeChange(change('Name', 'None', 'North 40'))).toBe('Name: North 40')
    expect(describeChange(change('Variety', 'Russet', 'None'))).toBe('Variety: Russet → None')
  })

  it('cuts a long list to six lines', () => {
    const lines = describeChanges(Array.from({ length: 10 }, (_, i) => change(`Rain ${i + 1}`)))
    expect(lines).toHaveLength(6)
    expect(lines.at(-1)).toBe('and 5 more')
    expect(describeChanges(Array.from({ length: 6 }, (_, i) => change(`Rain ${i + 1}`)))).toHaveLength(6)
  })
})
