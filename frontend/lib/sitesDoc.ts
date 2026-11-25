// The saved-sites document, pure (lib/sites.svelte.ts is the store over it): its types, where it's kept
// (`SitesBackend`), reading and migrating a stored copy, resolving preferences, merging two documents by coordinates
// and importing a CSV file. Plain functions on plain objects, so they're tested without the store.

import { readStored, writeStored } from './storage'
import { cleanName, parseSitesCsv, uniqueName, type SkippedRow } from './sitesCsv'
import { formatCoords, roundCoord, siteKey, validCoords } from './siteKey'

export const SITES_KEY = 'agweather.sites'
export const VERSION = 1
export const MAX_SITES = 50

export type Site = {
  key: string
  lat: number
  lng: number
  /** The reader's name for it; '' when they gave none (pages show the coordinates) */
  name: string
  addedAt: string
  updatedAt: string
}

export type Group = { id: string; name: string; siteKeys: string[] }

/** One level's choices; a field left out (or null in a patch) inherits from the level above */
export type Prefs = {
  /** Crops to show models for */
  crops?: string[]
  /** Models to show, by id */
  models?: string[]
  /** Models to leave out of whatever the lists above give */
  hiddenModels?: string[]
  /** A model's options by name (`{ 'late-blight-dsv': { protection_days: '7' } }`) */
  options?: Record<string, Record<string, string>>
  /** A planting date, YYYY-MM-DD */
  planting?: string
}

export type SitesDoc = {
  version: number
  sites: Site[]
  groups: Group[]
  prefs: { all: Prefs; groups: Record<string, Prefs>; sites: Record<string, Prefs> }
  updatedAt: string | null
  /** When the account last took this document (track 8); null until then */
  syncedAt: string | null
}

/** What a site's pages use: lists from the site, else the union of its groups', else all sites'; `models` without
 * the hidden ones; single values from the site, else its first group in the reader's order, else all sites */
export type EffectivePrefs = {
  crops: string[] | undefined
  models: string[] | undefined
  hiddenModels: string[]
  options: Record<string, Record<string, string>>
  planting: string | undefined
}

/** Where the document lives: this browser (`localBackend`), memory (`memoryBackend`, tests), the account later */
export interface SitesBackend {
  /** The stored document as found (any shape, or undefined); `migrate` reads it */
  load(): unknown
  /** False if it couldn't be kept (storage blocked or full) */
  save(doc: SitesDoc): boolean
  /** Calls `changed` when another tab or device changes the document; returns a function that stops watching */
  watch(changed: () => void): () => void
}

export const localBackend: SitesBackend = {
  load: () => readStored(SITES_KEY),
  save: (doc) => writeStored(SITES_KEY, doc),
  watch(changed) {
    if (typeof addEventListener === 'undefined') return () => {}
    const listener = (event: StorageEvent) => {
      if (event.key === SITES_KEY || event.key === null) changed()
    }
    addEventListener('storage', listener)
    return () => removeEventListener('storage', listener)
  },
}

/** A backend in memory, for tests: `fail` makes saves fail as blocked storage does; `external` stands in for another
 * tab's write */
export function memoryBackend(initial?: unknown, { fail = false }: { fail?: boolean } = {}) {
  let stored: unknown = initial === undefined ? undefined : structuredClone(initial)
  const watchers = new Set<() => void>()
  return {
    load: () => (stored === undefined ? undefined : structuredClone(stored)),
    save(doc: SitesDoc) {
      if (fail) return false
      stored = structuredClone(doc)
      return true
    },
    watch(changed: () => void) {
      watchers.add(changed)
      return () => watchers.delete(changed)
    },
    external(doc: unknown) {
      stored = structuredClone(doc)
      for (const changed of watchers) changed()
    },
    get stored() {
      return stored
    },
  }
}

// --- The document, pure ------------------------------------------------------------------------------------------

export function emptyDoc(): SitesDoc {
  return {
    version: VERSION,
    sites: [],
    groups: [],
    prefs: { all: {}, groups: {}, sites: {} },
    updatedAt: null,
    syncedAt: null,
  }
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
const strings = (value: unknown): string[] | undefined =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : undefined

function readSite(value: unknown, now: string): Site | null {
  if (!isObject(value)) return null
  const lat = Number(value.lat)
  const lng = Number(value.lng)
  if (!validCoords(lat, lng)) return null
  return {
    key: siteKey(lat, lng),
    lat: roundCoord(lat),
    lng: roundCoord(lng),
    name: typeof value.name === 'string' ? cleanName(value.name) : '',
    addedAt: typeof value.addedAt === 'string' ? value.addedAt : now,
    updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : now,
  }
}

function readPrefs(value: unknown): Prefs {
  if (!isObject(value)) return {}
  const prefs: Prefs = {}
  for (const field of ['crops', 'models', 'hiddenModels'] as const) {
    const list = strings(value[field])
    if (list) prefs[field] = list
  }
  if (isObject(value.options)) {
    prefs.options = {}
    for (const [model, chosen] of Object.entries(value.options)) {
      if (isObject(chosen))
        prefs.options[model] = Object.fromEntries(
          Object.entries(chosen).filter((entry): entry is [string, string] => typeof entry[1] === 'string'),
        )
    }
  }
  if (typeof value.planting === 'string') prefs.planting = value.planting
  return prefs
}

/** Version 0: before the document had a version, a bare list of `{lat, lng, name}` */
function fromVersion0(list: unknown[]): Record<string, unknown> {
  return { version: 1, sites: list, groups: [], prefs: {}, updatedAt: null, syncedAt: null }
}

/** Each step takes a document of one version to the next; add one with each change to the shape */
const MIGRATIONS: Record<number, (doc: Record<string, unknown>) => Record<string, unknown>> = {}

export type Loaded = { doc: SitesDoc; readOnly: boolean; problem: string | null }

/** The stored document, migrated to this version and checked field by field (anything unreadable is dropped). One
 * from a newer version is read as far as this version understands it and opened read-only, so it isn't overwritten
 * with less than it held. */
export function migrate(raw: unknown, now: string = new Date().toISOString()): Loaded {
  if (raw === undefined || raw === null) return { doc: emptyDoc(), readOnly: false, problem: null }
  let value: Record<string, unknown>
  if (Array.isArray(raw)) value = fromVersion0(raw)
  else if (isObject(raw) && typeof raw.version === 'number') value = raw
  else return { doc: emptyDoc(), readOnly: false, problem: 'unreadable' }
  let readOnly = false
  if ((value.version as number) > VERSION) readOnly = true
  while ((value.version as number) < VERSION) {
    const step = MIGRATIONS[value.version as number]
    if (!step) return { doc: emptyDoc(), readOnly: false, problem: 'unreadable' }
    value = step(value)
  }

  const doc = emptyDoc()
  const keys = new Set<string>()
  for (const item of Array.isArray(value.sites) ? value.sites : []) {
    const site = readSite(item, now)
    if (site && !keys.has(site.key) && doc.sites.length < MAX_SITES) {
      keys.add(site.key)
      doc.sites.push(site)
    }
  }
  for (const item of Array.isArray(value.groups) ? value.groups : []) {
    if (!isObject(item) || typeof item.id !== 'string' || typeof item.name !== 'string') continue
    const members = (strings(item.siteKeys) ?? []).filter((key) => keys.has(key))
    doc.groups.push({ id: item.id, name: cleanName(item.name), siteKeys: [...new Set(members)] })
  }
  const prefs = isObject(value.prefs) ? value.prefs : {}
  doc.prefs.all = readPrefs(prefs.all)
  const groupIds = new Set(doc.groups.map((g) => g.id))
  for (const [id, p] of Object.entries(isObject(prefs.groups) ? prefs.groups : {}))
    if (groupIds.has(id)) doc.prefs.groups[id] = readPrefs(p)
  for (const [key, p] of Object.entries(isObject(prefs.sites) ? prefs.sites : {}))
    if (keys.has(key)) doc.prefs.sites[key] = readPrefs(p)
  doc.updatedAt = typeof value.updatedAt === 'string' ? value.updatedAt : null
  doc.syncedAt = typeof value.syncedAt === 'string' ? value.syncedAt : null
  return { doc, readOnly, problem: null }
}

const union = (lists: string[][]): string[] => [...new Set(lists.flat())]

/** A site's preferences resolved through its groups and all sites (see `EffectivePrefs`) */
export function resolvePrefs(doc: SitesDoc, key: string): EffectivePrefs {
  const site = doc.prefs.sites[key] ?? {}
  const groups = doc.groups.filter((g) => g.siteKeys.includes(key)).map((g) => doc.prefs.groups[g.id] ?? {})
  const all = doc.prefs.all
  const list = (field: 'crops' | 'models' | 'hiddenModels'): string[] | undefined => {
    if (site[field]) return [...site[field]]
    const set = groups.map((g) => g[field]).filter((l): l is string[] => l !== undefined)
    if (set.length) return union(set)
    return all[field] ? [...all[field]] : undefined
  }
  const hidden = list('hiddenModels') ?? []
  const models = list('models')?.filter((m) => !hidden.includes(m))
  const options: Record<string, Record<string, string>> = {}
  // Lowest precedence first, so the site's own choices are written last
  for (const level of [all, ...[...groups].reverse(), site]) {
    for (const [model, chosen] of Object.entries(level.options ?? {})) options[model] = { ...options[model], ...chosen }
  }
  const planting = site.planting ?? groups.find((g) => g.planting !== undefined)?.planting ?? all.planting
  return { crops: list('crops'), models, hiddenModels: hidden, options, planting }
}

/** `b`'s choices over `a`'s, field by field (options model by model, name by name) */
function mergePrefs(a: Prefs = {}, b: Prefs = {}): Prefs {
  const merged: Prefs = { ...a, ...Object.fromEntries(Object.entries(b).filter(([, v]) => v !== undefined)) }
  if (a.options || b.options) {
    merged.options = { ...a.options }
    for (const [model, chosen] of Object.entries(b.options ?? {}))
      merged.options[model] = { ...merged.options[model], ...chosen }
  }
  return merged
}

export type Merged = {
  doc: SitesDoc
  /** Keys of this browser's sites the account didn't have, now in it */
  added: string[]
  /** Keys of this browser's sites left out because the account reached MAX_SITES */
  skipped: string[]
}

/** The account's document (`remote`) with this browser's (`local`) merged in by coordinates, for the first sign-in
 * (track 8): nothing is lost but what doesn't fit. Sites: the account's, then this browser's it lacks. Groups: by
 * name (ignoring case), members joined. Preferences: the account's choices win, this browser's fill the rest. */
export function mergeByCoordinates(local: SitesDoc, remote: SitesDoc): Merged {
  const doc: SitesDoc = structuredClone(remote)
  const added: string[] = []
  const skipped: string[] = []
  const keys = new Set(doc.sites.map((s) => s.key))
  const names = new Set(doc.sites.map((s) => s.name.toLowerCase()))
  for (const site of local.sites) {
    if (keys.has(site.key)) continue
    if (doc.sites.length >= MAX_SITES) {
      skipped.push(site.key)
      continue
    }
    doc.sites.push({ ...site, name: uniqueName(site.name, names) })
    keys.add(site.key)
    added.push(site.key)
  }
  const ids = new Set(doc.groups.map((g) => g.id))
  for (const group of local.groups) {
    const members = group.siteKeys.filter((key) => keys.has(key))
    const same = doc.groups.find((g) => g.name.toLowerCase() === group.name.toLowerCase())
    if (same) {
      same.siteKeys = [...new Set([...same.siteKeys, ...members])]
      doc.prefs.groups[same.id] = mergePrefs(local.prefs.groups[group.id], doc.prefs.groups[same.id])
    } else {
      const id = ids.has(group.id) ? newId() : group.id
      ids.add(id)
      doc.groups.push({ id, name: group.name, siteKeys: members })
      if (local.prefs.groups[group.id]) doc.prefs.groups[id] = structuredClone(local.prefs.groups[group.id])
    }
  }
  doc.prefs.all = mergePrefs(local.prefs.all, remote.prefs.all)
  for (const [key, prefs] of Object.entries(local.prefs.sites)) {
    if (keys.has(key)) doc.prefs.sites[key] = mergePrefs(prefs, remote.prefs.sites[key])
  }
  return { doc, added, skipped }
}

export function newId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `g${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

/** A site's name, or its coordinates when it has none */
export function siteLabel(site: Pick<Site, 'name' | 'lat' | 'lng'>): string {
  return site.name || formatCoords(site.lat, site.lng)
}

export const nowIso = (): string => new Date().toISOString()

export type ImportResult = {
  added: Site[]
  skipped: SkippedRow[]
  /** What happened, in sentences: what was added, then each row left out and why */
  messages: string[]
  /** Set when nothing could be read from the file */
  error: string | null
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/** Adds the sites in a CSV file to `doc` (changing it) after its own, creating the file's groups by name. A row whose
 * place is already saved, or past MAX_SITES, is left out and listed; a name already used gets " (2)". */
export function importInto(doc: SitesDoc, text: string, now: string = nowIso()): ImportResult {
  const parsed = parseSitesCsv(text)
  if (parsed.error) return { added: [], skipped: [], messages: [parsed.error], error: parsed.error }
  const added: Site[] = []
  const skipped = [...parsed.skipped]
  const full: number[] = []
  const names = new Set(doc.sites.map((s) => s.name.toLowerCase()).filter(Boolean))
  for (const row of parsed.sites) {
    const key = siteKey(row.lat, row.lng)
    const existing = doc.sites.find((s) => s.key === key)
    if (existing) {
      skipped.push({
        row: row.row,
        message: `Row ${row.row} was skipped: that location is already saved as ${siteLabel(existing)}.`,
      })
      continue
    }
    if (doc.sites.length >= MAX_SITES) {
      full.push(row.row)
      continue
    }
    const site: Site = {
      key,
      lat: row.lat,
      lng: row.lng,
      name: uniqueName(row.name, names),
      addedAt: now,
      updatedAt: now,
    }
    doc.sites.push(site)
    added.push(site)
    for (const name of row.groups) {
      let group = doc.groups.find((g) => g.name.toLowerCase() === name.toLowerCase())
      if (!group) {
        doc.groups.push({ id: newId(), name, siteKeys: [] })
        group = doc.groups[doc.groups.length - 1]
      }
      if (!group.siteKeys.includes(key)) group.siteKeys.push(key)
    }
  }
  if (full.length) {
    const rowsText =
      full.length === 1
        ? `Row ${full[0]} was`
        : `${plural(full.length, 'row')} (${full[0]} to ${full[full.length - 1]}) were`
    skipped.push({ row: full[0], message: `${rowsText} skipped: you can save up to ${MAX_SITES} sites.` })
  }
  skipped.sort((a, b) => a.row - b.row)
  const summary = added.length ? `Added ${plural(added.length, 'site')}.` : 'No sites were added.'
  return { added, skipped, messages: [summary, ...skipped.map((s) => s.message)], error: null }
}
