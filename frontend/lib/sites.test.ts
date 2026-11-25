import { beforeEach, describe, expect, it } from 'vitest'

import {
  addGroup,
  addSite,
  effectivePrefs,
  emptyDoc,
  exportSitesCsv,
  groups,
  importSitesCsv,
  isSaved,
  MAX_SITES,
  memoryBackend,
  mergeByCoordinates,
  migrate,
  moveSite,
  prefsAt,
  removeGroup,
  removeSite,
  renameSite,
  resolvePrefs,
  setInGroup,
  setPrefs,
  siteAt,
  sites,
  sitesSnapshot,
  sitesState,
  SITES_KEY,
  useSitesBackend,
  VERSION,
  type SitesDoc,
} from './sites.svelte'

const doc = (patch: Partial<SitesDoc> = {}): SitesDoc => ({ ...emptyDoc(), ...patch })
const site = (lat: number, lng: number, name = '') => ({
  key: `${lat},${lng}`,
  lat,
  lng,
  name,
  addedAt: '2026-11-01T00:00:00Z',
  updatedAt: '2026-11-01T00:00:00Z',
})

let backend: ReturnType<typeof memoryBackend>
beforeEach(() => {
  backend = memoryBackend()
  useSitesBackend(backend)
})

describe('the store', () => {
  it('adds a site keyed by its coordinates and keeps it', () => {
    const result = addSite({ lat: 43.070001, lng: -89.4, name: ' Home  farm ' })
    expect(result.ok).toBe(true)
    expect(sites.map((s) => [s.key, s.name])).toEqual([['43.07,-89.4', 'Home farm']])
    expect(siteAt(43.07, -89.40004)?.name).toBe('Home farm')
    expect(isSaved(43.07, -89.4)).toBe(true)
    expect((backend.stored as SitesDoc).sites[0].key).toBe('43.07,-89.4')
    expect((backend.stored as SitesDoc).version).toBe(VERSION)
  })

  it('refuses a place already saved, naming the site that has it', () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home farm' })
    const again = addSite({ lat: 43.07, lng: -89.4, name: 'Other' })
    expect(again).toMatchObject({ ok: false, message: 'You’ve already saved this location as Home farm.' })
    expect(sites).toHaveLength(1)
  })

  it(`holds at most ${MAX_SITES} sites`, () => {
    for (let k = 0; k < MAX_SITES; k++) expect(addSite({ lat: 40 + k / 100, lng: -90 }).ok).toBe(true)
    expect(addSite({ lat: 30, lng: -90 })).toMatchObject({
      ok: false,
      message: expect.stringMatching(/up to 50 sites/),
    })
  })

  it('renames, reorders and removes, taking a removed site out of its groups and preferences', () => {
    addSite({ lat: 43, lng: -89, name: 'A' })
    addSite({ lat: 44, lng: -89, name: 'B' })
    addSite({ lat: 45, lng: -89, name: 'C' })
    moveSite('45,-89', 0)
    expect(sites.map((s) => s.name)).toEqual(['C', 'A', 'B'])
    moveSite('45,-89', 99)
    expect(sites.map((s) => s.name)).toEqual(['A', 'B', 'C'])
    renameSite('43,-89', '<i>North</i>')
    expect(sites[0].name).toBe('North')
    const group = addGroup('Farm')
    if (!group.ok) throw new Error(group.message)
    setInGroup(group.value.id, '44,-89', true)
    setPrefs({ kind: 'site', key: '44,-89' }, { crops: ['potato'] })
    removeSite('44,-89')
    expect(sites.map((s) => s.name)).toEqual(['North', 'C'])
    expect(groups[0].siteKeys).toEqual([])
    expect(sitesSnapshot().prefs.sites).toEqual({})
  })

  it('refuses a second group of the same name, and deleting a group keeps its sites', () => {
    addSite({ lat: 43, lng: -89 })
    const farm = addGroup('Farm')
    expect(addGroup('farm')).toMatchObject({ ok: false, message: 'You already have a group named farm.' })
    if (!farm.ok) throw new Error()
    setInGroup(farm.value.id, '43,-89', true)
    removeGroup(farm.value.id)
    expect(groups).toHaveLength(0)
    expect(sites).toHaveLength(1)
  })

  it('keeps working in memory when storage is blocked, and says so', () => {
    useSitesBackend(memoryBackend(undefined, { fail: true }))
    expect(addSite({ lat: 43, lng: -89 }).ok).toBe(true)
    expect(sites).toHaveLength(1)
    expect(sitesState.persistent).toBe(false)
  })

  it('opens a document from a newer version read-only', () => {
    useSitesBackend(memoryBackend({ ...doc({ sites: [site(43, -89, 'A')] }), version: VERSION + 1 }))
    expect(sitesState.readOnly).toBe(true)
    expect(sites.map((s) => s.name)).toEqual(['A'])
    expect(addSite({ lat: 44, lng: -89 })).toMatchObject({ ok: false, message: expect.stringMatching(/newer version/) })
    expect(removeSite('43,-89').ok).toBe(false)
  })

  it('follows a change made in another tab', () => {
    addSite({ lat: 43, lng: -89, name: 'A' })
    backend.external(doc({ sites: [site(44, -89, 'B'), site(45, -89, 'C')] }))
    expect(sites.map((s) => s.name)).toEqual(['B', 'C'])
  })

  it('reads its document from localStorage by default', async () => {
    localStorage.setItem(SITES_KEY, JSON.stringify(doc({ sites: [site(43, -89, 'Stored')] })))
    const { localBackend } = await import('./sites.svelte')
    useSitesBackend(localBackend)
    expect(sites.map((s) => s.name)).toEqual(['Stored'])
    addSite({ lat: 44, lng: -89, name: 'New' })
    expect(JSON.parse(localStorage.getItem(SITES_KEY)!).sites).toHaveLength(2)
    localStorage.removeItem(SITES_KEY)
  })

  it('imports a CSV file: groups by name, names made unique, duplicates and rows past the limit listed', () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home' })
    const text = 'name,lat,lng,groups\nHome,44,-89,North;Clients\nAgain,43.07,-89.4,\nhome,45,-89,North\n'
    const result = importSitesCsv(text)
    expect(result.error).toBeNull()
    expect(sites.map((s) => s.name)).toEqual(['Home', 'Home (2)', 'home (3)'])
    expect(groups.map((g) => [g.name, g.siteKeys])).toEqual([
      ['North', ['44,-89', '45,-89']],
      ['Clients', ['44,-89']],
    ])
    expect(result.messages).toEqual(['Added 2 sites.', 'Row 3 was skipped: that location is already saved as Home.'])
    for (let k = sites.length; k < MAX_SITES; k++) addSite({ lat: 30 + k / 100, lng: -90 })
    const over = importSitesCsv('lat,lng\n10,10\n11,11\n12,12\n')
    expect(over.messages).toEqual([
      'No sites were added.',
      '3 rows (2 to 4) were skipped: you can save up to 50 sites.',
    ])
  })

  it('exports what it imports', () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home, north' })
    const group = addGroup('Farm')
    if (group.ok) setInGroup(group.value.id, '43.07,-89.4', true)
    const csv = exportSitesCsv()
    expect(csv).toBe('name,lat,lng,groups\r\n"Home, north",43.07,-89.4,Farm\r\n')
    useSitesBackend(memoryBackend())
    importSitesCsv(csv)
    expect(sites.map((s) => s.name)).toEqual(['Home, north'])
    expect(groups.map((g) => g.name)).toEqual(['Farm'])
  })

  it('sets preferences at a level, a null going back to inheriting', () => {
    addSite({ lat: 43, lng: -89 })
    setPrefs({ kind: 'all' }, { crops: ['corn'], planting: '2026-05-01' })
    setPrefs({ kind: 'site', key: '43,-89' }, { crops: ['potato'] })
    expect(effectivePrefs('43,-89').crops).toEqual(['potato'])
    setPrefs({ kind: 'site', key: '43,-89' }, { crops: null })
    expect(effectivePrefs('43,-89')).toMatchObject({ crops: ['corn'], planting: '2026-05-01' })
    expect(prefsAt({ kind: 'site', key: '43,-89' })).toEqual({})
  })
})

describe('resolvePrefs', () => {
  const base = doc({
    sites: [site(43, -89), site(44, -89)],
    groups: [
      { id: 'g1', name: 'Farm', siteKeys: ['43,-89'] },
      { id: 'g2', name: 'Client', siteKeys: ['43,-89'] },
    ],
  })

  it('takes a list from the site, else the union of its groups’, else all sites’, else nothing', () => {
    const d: SitesDoc = {
      ...base,
      prefs: {
        all: { crops: ['corn'] },
        groups: { g1: { crops: ['potato'] }, g2: { crops: ['onion', 'potato'] } },
        sites: {},
      },
    }
    expect(resolvePrefs(d, '43,-89').crops).toEqual(['potato', 'onion'])
    expect(resolvePrefs(d, '44,-89').crops).toEqual(['corn'])
    d.prefs.sites['43,-89'] = { crops: ['apple'] }
    expect(resolvePrefs(d, '43,-89').crops).toEqual(['apple'])
    expect(resolvePrefs(base, '43,-89')).toEqual({
      crops: undefined,
      models: undefined,
      hiddenModels: [],
      options: {},
      planting: undefined,
    })
  })

  it('subtracts hidden models from the models shown', () => {
    const d: SitesDoc = {
      ...base,
      prefs: {
        all: { models: ['late-blight-dsv', 'early-blight-pdays', 'tar-spot'] },
        groups: { g1: { hiddenModels: ['tar-spot'] } },
        sites: {},
      },
    }
    expect(resolvePrefs(d, '43,-89')).toMatchObject({
      models: ['late-blight-dsv', 'early-blight-pdays'],
      hiddenModels: ['tar-spot'],
    })
    expect(resolvePrefs(d, '44,-89').models).toEqual(['late-blight-dsv', 'early-blight-pdays', 'tar-spot'])
  })

  it('takes a single value from the site, else the first group in order, else all sites', () => {
    const d: SitesDoc = {
      ...base,
      prefs: {
        all: { planting: '2026-05-01', options: { 'late-blight-dsv': { protection_days: '14', a: 'all' } } },
        groups: {
          g2: { planting: '2026-05-20', options: { 'late-blight-dsv': { protection_days: '10' } } },
          g1: { planting: '2026-05-10', options: { 'late-blight-dsv': { protection_days: '7' } } },
        },
        sites: {},
      },
    }
    // g1 is first in the reader's order of groups, whatever order the preferences were written in
    expect(resolvePrefs(d, '43,-89').planting).toBe('2026-05-10')
    expect(resolvePrefs(d, '43,-89').options).toEqual({ 'late-blight-dsv': { protection_days: '7', a: 'all' } })
    expect(resolvePrefs(d, '44,-89').planting).toBe('2026-05-01')
    d.prefs.sites['43,-89'] = { planting: '2026-06-01', options: { 'late-blight-dsv': { protection_days: '5' } } }
    expect(resolvePrefs(d, '43,-89')).toMatchObject({
      planting: '2026-06-01',
      options: { 'late-blight-dsv': { protection_days: '5', a: 'all' } },
    })
  })
})

describe('migrate', () => {
  it('starts empty with nothing stored, and sets aside what it can’t read', () => {
    expect(migrate(undefined)).toEqual({ doc: emptyDoc(), readOnly: false, problem: null })
    expect(migrate('garbage').problem).toBe('unreadable')
    expect(migrate({ sites: [] }).problem).toBe('unreadable')
  })

  it('takes version 0, a bare list of sites, to the current version', () => {
    const { doc: d } = migrate([{ lat: 43.07, lng: -89.4, name: 'Old' }], '2026-01-01T00:00:00Z')
    expect(d.version).toBe(VERSION)
    expect(d.sites).toEqual([
      {
        key: '43.07,-89.4',
        lat: 43.07,
        lng: -89.4,
        name: 'Old',
        addedAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
      },
    ])
  })

  it('drops what doesn’t hold together: bad coordinates, repeated keys, unknown members and preferences', () => {
    const { doc: d } = migrate({
      version: 1,
      sites: [site(43, -89, 'A'), site(43, -89, 'Again'), { lat: 'x', lng: 1 }, site(44, -89, '<b>B</b>')],
      groups: [{ id: 'g', name: 'G', siteKeys: ['43,-89', '99,99', '43,-89'] }, { name: 'no id' }],
      prefs: { all: { crops: ['corn', 5] }, groups: { g: { planting: '2026-05-01' }, gone: {} }, sites: { '1,1': {} } },
    })
    expect(d.sites.map((s) => s.name)).toEqual(['A', 'B'])
    expect(d.groups).toEqual([{ id: 'g', name: 'G', siteKeys: ['43,-89'] }])
    expect(d.prefs).toEqual({ all: { crops: ['corn'] }, groups: { g: { planting: '2026-05-01' } }, sites: {} })
  })
})

describe('mergeByCoordinates', () => {
  it('keeps the account’s sites and adds this browser’s it lacks, joining groups by name', () => {
    const remote = doc({
      sites: [site(43, -89, 'Home')],
      groups: [{ id: 'r1', name: 'Farm', siteKeys: ['43,-89'] }],
      prefs: { all: { crops: ['corn'] }, groups: {}, sites: { '43,-89': { planting: '2026-05-01' } } },
    })
    const local = doc({
      sites: [site(43, -89, 'Mine'), site(44, -89, 'Home'), site(45, -89, 'Other')],
      groups: [
        { id: 'l1', name: 'farm', siteKeys: ['44,-89'] },
        { id: 'r1', name: 'Clients', siteKeys: ['45,-89'] },
      ],
      prefs: {
        all: { crops: ['potato'], hiddenModels: ['tar-spot'] },
        groups: { l1: { planting: '2026-04-20' } },
        sites: { '43,-89': { planting: '2026-06-01', crops: ['onion'] } },
      },
    })
    const { doc: merged, added, skipped } = mergeByCoordinates(local, remote)
    expect(merged.sites.map((s) => [s.key, s.name])).toEqual([
      ['43,-89', 'Home'],
      ['44,-89', 'Home (2)'],
      ['45,-89', 'Other'],
    ])
    expect(added).toEqual(['44,-89', '45,-89'])
    expect(skipped).toEqual([])
    expect(merged.groups[0]).toEqual({ id: 'r1', name: 'Farm', siteKeys: ['43,-89', '44,-89'] })
    // The local group whose id the account already used gets a new one
    expect(merged.groups[1].name).toBe('Clients')
    expect(merged.groups[1].id).not.toBe('r1')
    expect(merged.prefs.all).toEqual({ crops: ['corn'], hiddenModels: ['tar-spot'] })
    expect(merged.prefs.groups.r1).toEqual({ planting: '2026-04-20' })
    expect(merged.prefs.sites['43,-89']).toEqual({ planting: '2026-05-01', crops: ['onion'] })
    // Pure: neither input changed
    expect(remote.sites).toHaveLength(1)
  })

  it('leaves out what doesn’t fit in the account', () => {
    const full = doc({ sites: Array.from({ length: MAX_SITES }, (_, k) => site(40 + k, -89)) })
    const { skipped, added } = mergeByCoordinates(doc({ sites: [site(10, 10)] }), full)
    expect(added).toEqual([])
    expect(skipped).toEqual(['10,10'])
  })
})
