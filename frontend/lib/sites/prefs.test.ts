import { describe, expect, it } from 'vitest'

import { emptyDoc, resolvePrefs, type SitesDoc } from '@/lib/sitesDoc'

import { groupBounds, groupCodec, groupMapUrl, mapGroup } from './groupMap'
import { explainPrefs, hiddenPatch, inheritanceWords, modelShown, optionPatch, sourceWords, toggled } from './prefs'

const at = '2026-11-01T00:00:00Z'
const site = (key: string, name: string) => {
  const [lat, lng] = key.split(',').map(Number)
  return { key, lat, lng, name, addedAt: at, updatedAt: at }
}

function doc(): SitesDoc {
  const d = emptyDoc()
  d.sites = [site('43.07,-89.4', 'Madison'), site('44.1336,-89.5168', 'Hancock')]
  d.groups = [
    { id: 'corn', name: 'Corn fields', siteKeys: ['43.07,-89.4', '44.1336,-89.5168'] },
    { id: 'spuds', name: 'Potatoes', siteKeys: ['44.1336,-89.5168'] },
  ]
  d.prefs.all = { planting: 'mid', hiddenModels: ['tar-spot'] }
  d.prefs.groups = {
    corn: { crops: ['corn'], planting: '2026-05-01', options: { 'late-blight-dsv': { protection_days: '7' } } },
    spuds: {
      crops: ['potato'],
      hiddenModels: ['white-mold'],
      options: { 'late-blight-dsv': { protection_days: '5' } },
    },
  }
  return d
}

describe('explainPrefs', () => {
  it('says where each of a site’s values comes from, by the same rules as resolvePrefs', () => {
    const d = doc()
    const level = { kind: 'site', key: '44.1336,-89.5168' } as const
    const e = explainPrefs(d, level)
    const resolved = resolvePrefs(d, '44.1336,-89.5168')
    // Lists: the union of its groups'
    expect(e.crops).toEqual({
      value: ['corn', 'potato'],
      source: { kind: 'groups', names: ['Corn fields', 'Potatoes'] },
    })
    expect(e.crops.value).toEqual(resolved.crops)
    expect(e.hiddenModels).toEqual({ value: ['white-mold'], source: { kind: 'groups', names: ['Potatoes'] } })
    // A single value: the first group in the reader's order
    expect(e.planting).toEqual({ value: '2026-05-01', source: { kind: 'groups', names: ['Corn fields'] } })
    expect(e.planting.value).toEqual(resolved.planting)
    expect(e.options['late-blight-dsv'].protection_days).toEqual({
      value: '7',
      source: { kind: 'groups', names: ['Corn fields'] },
    })
    expect(resolved.options['late-blight-dsv'].protection_days).toBe('7')
    expect(e.parents.map((p) => p.name)).toEqual(['Corn fields', 'Potatoes', null])
  })

  it('takes the site’s own choice first, and all sites’ where no group has one', () => {
    const d = doc()
    d.prefs.sites['43.07,-89.4'] = { crops: ['apple'] }
    d.prefs.groups.corn.planting = undefined
    const e = explainPrefs(d, { kind: 'site', key: '43.07,-89.4' })
    expect(e.crops).toEqual({ value: ['apple'], source: { kind: 'here' } })
    expect(e.planting).toEqual({ value: 'mid', source: { kind: 'all' } })
    expect(e.hiddenModels).toEqual({ value: ['tar-spot'], source: { kind: 'all' } })
  })

  it('has a group follow all sites only, and all sites follow the defaults', () => {
    const d = doc()
    const group = explainPrefs(d, { kind: 'group', id: 'spuds' })
    expect(group.crops.source).toEqual({ kind: 'here' })
    expect(group.planting).toEqual({ value: 'mid', source: { kind: 'all' } })
    const all = explainPrefs(d, { kind: 'all' })
    expect(all.crops).toEqual({ value: undefined, source: { kind: 'default' } })
    expect(all.planting.source).toEqual({ kind: 'here' })
  })
})

describe('changes', () => {
  it('shows a model a group hides by keeping an empty list at the site', () => {
    const d = doc()
    const level = { kind: 'site', key: '44.1336,-89.5168' } as const
    expect(hiddenPatch(explainPrefs(d, level), 'white-mold', false)).toEqual([])
    d.prefs.sites['44.1336,-89.5168'] = { hiddenModels: [] }
    expect(resolvePrefs(d, '44.1336,-89.5168').hiddenModels).toEqual([])
    // Hiding one starts from what the site follows
    delete d.prefs.sites['44.1336,-89.5168']
    expect(hiddenPatch(explainPrefs(d, level), 'tar-spot', true)).toEqual(['white-mold', 'tar-spot'])
  })

  it('clears a list that ends empty where nothing above sets one', () => {
    const d = emptyDoc()
    expect(hiddenPatch(explainPrefs(d, { kind: 'all' }), 'tar-spot', true)).toEqual(['tar-spot'])
    d.prefs.all.hiddenModels = ['tar-spot']
    expect(hiddenPatch(explainPrefs(d, { kind: 'all' }), 'tar-spot', false)).toBeNull()
    expect(toggled(['corn'], 'corn', false)).toBeNull()
    expect(toggled(undefined, 'corn', true)).toEqual(['corn'])
  })

  it('sets and clears one option of a model', () => {
    expect(optionPatch({}, 'm', 'a', '1')).toEqual({ options: { m: { a: '1' } } })
    expect(optionPatch({ options: { m: { a: '1', b: '2' } } }, 'm', 'a', null)).toEqual({ options: { m: { b: '2' } } })
    expect(optionPatch({ options: { m: { a: '1' } } }, 'm', 'a', null)).toEqual({ options: null })
  })
})

describe('words', () => {
  it('explains what a level follows', () => {
    const d = doc()
    expect(inheritanceWords(d, { kind: 'site', key: '44.1336,-89.5168' })).toBe(
      'This site follows its groups: Corn fields and Potatoes. Change a choice here to override them for this site only.',
    )
    d.groups = []
    expect(inheritanceWords(d, { kind: 'site', key: '43.07,-89.4' })).toMatch(/^This site follows your choices for all/)
    expect(sourceWords({ kind: 'groups', names: ['A'] }, { kind: 'site', key: 'x' })).toBe('From the group A')
    expect(sourceWords({ kind: 'here' }, { kind: 'group', id: 'g' })).toBe('Set for this group')
  })
})

describe('modelShown', () => {
  const prefs = { crops: undefined, models: undefined, hiddenModels: [] as string[] }
  it('follows hidden models, then chosen models, then chosen crops', () => {
    const model = { id: 'late-blight-dsv', crops: ['potato'] }
    expect(modelShown(null, model)).toBe(true)
    expect(modelShown(prefs, model)).toBe(true)
    expect(modelShown({ ...prefs, hiddenModels: ['late-blight-dsv'] }, model)).toBe(false)
    expect(modelShown({ ...prefs, crops: ['corn'] }, model)).toBe(false)
    expect(modelShown({ ...prefs, crops: ['corn'], models: ['late-blight-dsv'] }, model)).toBe(true)
  })
})

describe('a group on the map', () => {
  it('writes its sites’ coordinates and names into the link and reads them back', () => {
    const d = doc()
    d.sites[0].name = 'North; the “big” field, east'
    const group = mapGroup(d.groups[0], d.sites)
    const text = groupCodec.format(group)
    expect(groupCodec.parse(text)).toEqual(group)
    expect(group.sites.map((s) => s.name)).toEqual(['North; the “big” field, east', 'Hancock'])
    const url = new URL(groupMapUrl(d.groups[0], d.sites, 'late-blight-dsv'), 'https://example.org')
    expect(url.pathname).toBe('/map')
    expect(url.searchParams.get('layer')).toBe('late-blight-dsv')
    expect(groupCodec.parse(url.searchParams.get('group')!)).toEqual(group)
  })

  it('refuses a link it can’t read, and frames the sites', () => {
    expect(groupCodec.parse('Farm')).toBeUndefined()
    expect(groupCodec.parse('Farm;95,-89,A')).toBeUndefined()
    expect(groupCodec.parse('Farm;x,-89,A')).toBeUndefined()
    expect(groupBounds({ name: 'g', sites: [] })).toBeNull()
    expect(
      groupBounds({
        name: 'g',
        sites: [
          { lat: 43, lng: -89, name: 'a' },
          { lat: 44, lng: -90, name: 'b' },
        ],
      }),
    ).toEqual([
      [-90, 43],
      [-89, 44],
    ])
  })
})
