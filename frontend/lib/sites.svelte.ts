// Saved sites, groups and preferences (D120): one versioned document in this browser's localStorage
// (`agweather.sites`, through lib/storage), shaped as the account's tables will be (track 8: Site, SiteGroup,
// GroupMembership, Preference), so signing in later merges it by coordinates (`mergeByCoordinates`) and pages don't
// change: they read this module, and a `SitesBackend` decides where the document lives.
//
// - A site is keyed by its coordinates to 4 decimals (lib/siteKey), its page's address (F1); a key saved twice is
//   refused, naming the site that has it; at most MAX_SITES (F4).
// - Groups (a farm, a client) hold sites by key; a site can be in several and stays one site.
// - Preferences at three levels, all sites, a group and a site (F3, F11, F12): `effectivePrefs` resolves them.
// - A document from a newer version of the app opens read-only; one from an older version is migrated. When storage
//   is blocked (a private window), sites last for this page only and `sitesState.persistent` is false, so a page
//   can say so. A change made in another tab arrives here through the storage event.

import {
  emptyDoc,
  importInto,
  localBackend,
  MAX_SITES,
  migrate,
  newId,
  nowIso,
  resolvePrefs,
  siteLabel,
  type EffectivePrefs,
  type Group,
  type ImportResult,
  type Prefs,
  type Site,
  type SitesBackend,
  type SitesDoc,
} from './sitesDoc'
import { cleanName, sitesToCsv } from './sitesCsv'
import { roundCoord, siteKey, validCoords } from './siteKey'

export * from './sitesDoc'

// --- The store ---------------------------------------------------------------------------------------------------

const doc = $state<SitesDoc>(emptyDoc())

/** Whether what's saved lasts (false: storage is blocked, so sites last for this page only), whether the document
 * came from a newer version (read-only), and whether it was unreadable (it was set aside, not overwritten) */
export const sitesState = $state({ persistent: true, readOnly: false, unreadable: false })

/** The saved sites in the reader's order (reactive; change them through the functions below) */
export const sites: readonly Site[] = doc.sites
/** The groups in the reader's order (reactive) */
export const groups: readonly Group[] = doc.groups

let backend: SitesBackend = localBackend
let stopWatching = () => {}

function replace(next: SitesDoc) {
  doc.sites.splice(0, doc.sites.length, ...next.sites)
  doc.groups.splice(0, doc.groups.length, ...next.groups)
  doc.prefs = next.prefs
  doc.version = next.version
  doc.updatedAt = next.updatedAt
  doc.syncedAt = next.syncedAt
}

function load() {
  const loaded = migrate(backend.load())
  replace(loaded.doc)
  sitesState.readOnly = loaded.readOnly
  sitesState.unreadable = loaded.problem !== null
}

/** Reads the document from `next` and follows its changes from now on (tests; the account, track 8) */
export function useSitesBackend(next: SitesBackend) {
  stopWatching()
  backend = next
  sitesState.persistent = true
  load()
  stopWatching = backend.watch(load)
}

if (typeof localStorage !== 'undefined') useSitesBackend(localBackend)

/** Saves the document after a change; storage that won't take it leaves the change for this page only */
function save() {
  doc.updatedAt = nowIso()
  sitesState.persistent = backend.save($state.snapshot(doc) as SitesDoc)
}

const READ_ONLY_MESSAGE =
  'Your sites were saved by a newer version of AgWeather, so they can’t be changed here. Reload the page to get the newer version.'

/** The document as it is now (a copy), for an export or a test */
export function sitesSnapshot(): SitesDoc {
  return $state.snapshot(doc) as SitesDoc
}

export function siteByKey(key: string): Site | undefined {
  return doc.sites.find((s) => s.key === key)
}

/** The saved site at these coordinates (to the key's 4 decimals), if any */
export function siteAt(lat: number, lng: number): Site | undefined {
  return siteByKey(siteKey(lat, lng))
}

export function isSaved(lat: number, lng: number): boolean {
  return siteAt(lat, lng) !== undefined
}

export type Outcome<T = undefined> = { ok: true; value: T } | { ok: false; message: string; existing?: Site }

/** Saves a site at the end of the list. Refused (with a sentence for the reader) when the place is already saved,
 * the list is full, the coordinates aren't a place, or the document is read-only. */
export function addSite(input: { lat: number; lng: number; name?: string }): Outcome<Site> {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  if (!validCoords(input.lat, input.lng))
    return {
      ok: false,
      message:
        'Those coordinates aren’t a place on Earth. Latitude runs from -90 to 90 and longitude from -180 to 180.',
    }
  const existing = siteAt(input.lat, input.lng)
  if (existing) return { ok: false, existing, message: `You’ve already saved this location as ${siteLabel(existing)}.` }
  if (doc.sites.length >= MAX_SITES)
    return { ok: false, message: `You can save up to ${MAX_SITES} sites. Remove one to add another.` }
  const now = nowIso()
  const site: Site = {
    key: siteKey(input.lat, input.lng),
    lat: roundCoord(input.lat),
    lng: roundCoord(input.lng),
    name: cleanName(input.name ?? ''),
    addedAt: now,
    updatedAt: now,
  }
  doc.sites.push(site)
  save()
  return { ok: true, value: site }
}

export function removeSite(key: string): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const k = doc.sites.findIndex((s) => s.key === key)
  if (k < 0) return { ok: true, value: undefined }
  doc.sites.splice(k, 1)
  for (const group of doc.groups) group.siteKeys = group.siteKeys.filter((member) => member !== key)
  delete doc.prefs.sites[key]
  save()
  return { ok: true, value: undefined }
}

export function renameSite(key: string, name: string): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const site = doc.sites.find((s) => s.key === key)
  if (!site) return { ok: false, message: 'That site is no longer saved.' }
  site.name = cleanName(name)
  site.updatedAt = nowIso()
  save()
  return { ok: true, value: undefined }
}

/** Moves a site to `index` in the list (clamped to its ends) */
export function moveSite(key: string, index: number): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const from = doc.sites.findIndex((s) => s.key === key)
  if (from < 0) return { ok: false, message: 'That site is no longer saved.' }
  const to = Math.max(0, Math.min(doc.sites.length - 1, index))
  if (to === from) return { ok: true, value: undefined }
  const [site] = doc.sites.splice(from, 1)
  doc.sites.splice(to, 0, $state.snapshot(site))
  save()
  return { ok: true, value: undefined }
}

export function addGroup(name: string): Outcome<Group> {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const clean = cleanName(name)
  if (!clean) return { ok: false, message: 'Give the group a name.' }
  if (doc.groups.some((g) => g.name.toLowerCase() === clean.toLowerCase()))
    return { ok: false, message: `You already have a group named ${clean}.` }
  const group: Group = { id: newId(), name: clean, siteKeys: [] }
  doc.groups.push(group)
  save()
  return { ok: true, value: group }
}

export function renameGroup(id: string, name: string): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const clean = cleanName(name)
  if (!clean) return { ok: false, message: 'Give the group a name.' }
  if (doc.groups.some((g) => g.id !== id && g.name.toLowerCase() === clean.toLowerCase()))
    return { ok: false, message: `You already have a group named ${clean}.` }
  const group = doc.groups.find((g) => g.id === id)
  if (!group) return { ok: false, message: 'That group no longer exists.' }
  group.name = clean
  save()
  return { ok: true, value: undefined }
}

/** Deletes a group; its sites stay saved */
export function removeGroup(id: string): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const k = doc.groups.findIndex((g) => g.id === id)
  if (k >= 0) doc.groups.splice(k, 1)
  delete doc.prefs.groups[id]
  save()
  return { ok: true, value: undefined }
}

/** Puts a site in a group or takes it out */
export function setInGroup(id: string, key: string, member: boolean): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const group = doc.groups.find((g) => g.id === id)
  if (!group || !siteByKey(key)) return { ok: false, message: 'That group or site no longer exists.' }
  const has = group.siteKeys.includes(key)
  if (member && !has) group.siteKeys.push(key)
  if (!member && has) group.siteKeys = group.siteKeys.filter((k) => k !== key)
  save()
  return { ok: true, value: undefined }
}

export function groupsOf(key: string): Group[] {
  return doc.groups.filter((g) => g.siteKeys.includes(key))
}

export type PrefsLevel = { kind: 'all' } | { kind: 'group'; id: string } | { kind: 'site'; key: string }

/** Changes one level's choices: a field given replaces that level's, a field given as null goes back to inheriting */
export function setPrefs(level: PrefsLevel, patch: { [K in keyof Prefs]?: Prefs[K] | null }): Outcome {
  if (sitesState.readOnly) return { ok: false, message: READ_ONLY_MESSAGE }
  const current: Prefs =
    level.kind === 'all'
      ? doc.prefs.all
      : level.kind === 'group'
        ? (doc.prefs.groups[level.id] ??= {})
        : (doc.prefs.sites[level.key] ??= {})
  for (const [field, value] of Object.entries(patch) as [keyof Prefs, unknown][]) {
    if (value === null || value === undefined) delete current[field]
    else (current as Record<string, unknown>)[field] = structuredClone(value)
  }
  save()
  return { ok: true, value: undefined }
}

/** The level's own choices (what it overrides), not what it inherits */
export function prefsAt(level: PrefsLevel): Prefs {
  const found =
    level.kind === 'all'
      ? doc.prefs.all
      : level.kind === 'group'
        ? doc.prefs.groups[level.id]
        : doc.prefs.sites[level.key]
  return ($state.snapshot(found) as Prefs | undefined) ?? {}
}

export function effectivePrefs(key: string): EffectivePrefs {
  return resolvePrefs(doc, key)
}

// --- CSV ---------------------------------------------------------------------------------------------------------

export function exportSitesCsv(): string {
  return sitesToCsv(doc.sites.map((s) => ({ ...s, groups: groupsOf(s.key).map((g) => g.name) })))
}

/** Adds the sites in a CSV file after the saved ones (`importInto`) and saves them */
export function importSitesCsv(text: string): ImportResult {
  if (sitesState.readOnly) return { added: [], skipped: [], messages: [READ_ONLY_MESSAGE], error: READ_ONLY_MESSAGE }
  const result = importInto(doc, text)
  if (result.added.length) save()
  return result
}
