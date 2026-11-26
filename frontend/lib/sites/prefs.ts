// What a preferences panel shows of one level (all sites, a group or a site, F3, F11): each choice's value there,
// whether the level sets it or follows a level above, and which one. Pure, over the document, by the same rules as
// `resolvePrefs`: lists from the level, else the union of its groups', else all sites'; a single value (a planting
// date, a model's option) from the level, else its first group in the reader's order, else all sites.

import type { PrefsLevel } from '@/lib/sites.svelte'
import type { EffectivePrefs, Group, Prefs, SitesDoc } from '@/lib/sitesDoc'

/** Where a value comes from: this level, some of the site's groups, the choices for all sites, or nowhere (AgWeather's
 * default) */
export type Source = { kind: 'here' } | { kind: 'groups'; names: string[] } | { kind: 'all' } | { kind: 'default' }

export type Explained<T> = { value: T | undefined; source: Source }

export type ExplainedPrefs = {
  crops: Explained<string[]>
  models: Explained<string[]>
  hiddenModels: Explained<string[]>
  planting: Explained<string>
  layer: Explained<string>
  /** By model, then option name */
  options: Record<string, Record<string, Explained<string>>>
  /** The levels this one follows, nearest first: a site's groups (in the reader's order), then all sites */
  parents: { name: string | null; prefs: Prefs }[]
}

type ListField = 'crops' | 'models' | 'hiddenModels'
type SingleField = 'planting' | 'layer'

/** The groups a site is in, in the reader's order */
export function groupsWith(doc: SitesDoc, key: string): Group[] {
  return doc.groups.filter((g) => g.siteKeys.includes(key))
}

/** A level's own choices */
export function ownPrefs(doc: SitesDoc, level: PrefsLevel): Prefs {
  if (level.kind === 'all') return doc.prefs.all
  if (level.kind === 'group') return doc.prefs.groups[level.id] ?? {}
  return doc.prefs.sites[level.key] ?? {}
}

/** Each choice at a level and where it comes from */
export function explainPrefs(doc: SitesDoc, level: PrefsLevel): ExplainedPrefs {
  const own = ownPrefs(doc, level)
  const groups =
    level.kind === 'site'
      ? groupsWith(doc, level.key).map((g) => ({ name: g.name, prefs: doc.prefs.groups[g.id] ?? {} }))
      : []
  const all = level.kind === 'all' ? [] : [{ name: null, prefs: doc.prefs.all }]

  const list = (field: ListField): Explained<string[]> => {
    if (own[field]) return { value: [...own[field]], source: { kind: 'here' } }
    const setting = groups.filter((g) => g.prefs[field] !== undefined)
    if (setting.length)
      return {
        value: [...new Set(setting.flatMap((g) => g.prefs[field]!))],
        source: { kind: 'groups', names: setting.map((g) => g.name) },
      }
    if (all[0]?.prefs[field]) return { value: [...all[0].prefs[field]], source: { kind: 'all' } }
    return { value: undefined, source: { kind: 'default' } }
  }

  const single = (pick: (p: Prefs) => string | undefined): Explained<string> => {
    const here = pick(own)
    if (here !== undefined) return { value: here, source: { kind: 'here' } }
    const group = groups.find((g) => pick(g.prefs) !== undefined)
    if (group) return { value: pick(group.prefs), source: { kind: 'groups', names: [group.name] } }
    const top = all[0] ? pick(all[0].prefs) : undefined
    if (top !== undefined) return { value: top, source: { kind: 'all' } }
    return { value: undefined, source: { kind: 'default' } }
  }
  const field = (name: SingleField) => single((p) => p[name])

  const options: ExplainedPrefs['options'] = {}
  for (const prefs of [own, ...groups.map((g) => g.prefs), ...all.map((a) => a.prefs)]) {
    for (const [model, chosen] of Object.entries(prefs.options ?? {})) {
      for (const name of Object.keys(chosen)) {
        options[model] ??= {}
        options[model][name] ??= single((p) => p.options?.[model]?.[name])
      }
    }
  }

  return {
    crops: list('crops'),
    models: list('models'),
    hiddenModels: list('hiddenModels'),
    planting: field('planting'),
    layer: field('layer'),
    options,
    parents: [...groups, ...all],
  }
}

/** Whether a site's pages show a model under its preferences (null: an unsaved site, which shows every model): not
 * hidden, and in its chosen models, else for one of its chosen crops, else shown */
export function modelShown(
  prefs: Pick<EffectivePrefs, 'crops' | 'models' | 'hiddenModels'> | null,
  model: { id: string; crops: readonly string[] },
): boolean {
  if (!prefs) return true
  if (prefs.hiddenModels.includes(model.id)) return false
  if (prefs.models) return prefs.models.includes(model.id)
  if (prefs.crops) return model.crops.some((c) => prefs.crops!.includes(c))
  return true
}

/** "A and B", "A, B and C" */
export function joinWords(words: readonly string[]): string {
  if (words.length <= 1) return words.join('')
  return `${words.slice(0, -1).join(', ')} and ${words[words.length - 1]}`
}

/** Where a value comes from, in words, for a line such as "From your choices for all sites." */
export function sourceWords(source: Source, level: PrefsLevel): string {
  switch (source.kind) {
    case 'here':
      return level.kind === 'all' ? 'Your choice' : `Set for this ${level.kind}`
    case 'groups':
      return `From ${source.names.length === 1 ? 'the group' : 'the groups'} ${joinWords(source.names)}`
    case 'all':
      return 'From your choices for all sites'
    case 'default':
      return 'AgWeather’s default'
  }
}

/** The panel's opening sentences: what this level follows and how to change it */
export function inheritanceWords(doc: SitesDoc, level: PrefsLevel): string {
  if (level.kind === 'all')
    return 'These choices apply to every site you save, unless a group or the site itself changes them. With nothing chosen, each site shows the models in season and developed for its region.'
  if (level.kind === 'group') {
    const name = doc.groups.find((g) => g.id === level.id)?.name ?? 'this group'
    return `Sites in ${name} follow these choices, over your choices for all sites. A site in more than one group shows the crops of every group it’s in and hides the models any of them hides. Change a choice here to override your choices for all sites.`
  }
  const groups = groupsWith(doc, level.key).map((g) => g.name)
  if (!groups.length)
    return 'This site follows your choices for all sites. Change a choice here to override it for this site only.'
  return `This site follows its ${groups.length === 1 ? 'group' : 'groups'}: ${joinWords(groups)}. Change a choice here to override ${groups.length === 1 ? 'it' : 'them'} for this site only.`
}

/** Whether a level sets anything of its own */
export function hasOwn(prefs: Prefs): boolean {
  return Object.values(prefs).some((value) => value !== undefined)
}

/** A patch for one model's option at a level: the level's options with `name` set to `value`, or removed (null) */
export function optionPatch(
  own: Prefs,
  model: string,
  name: string,
  value: string | null,
): { options: Prefs['options'] | null } {
  const options = structuredClone(own.options ?? {})
  const chosen = { ...options[model] }
  if (value === null || value === '') delete chosen[name]
  else chosen[name] = value
  if (Object.keys(chosen).length) options[model] = chosen
  else delete options[model]
  return { options: Object.keys(options).length ? options : null }
}

/** A list toggled: `id` added or removed. An empty list is null (the level follows the one above again) unless
 * `keepEmpty`: hiding no models here, over a level above that hides some, is a choice of its own. */
export function toggled(
  list: readonly string[] | undefined,
  id: string,
  on: boolean,
  keepEmpty = false,
): string[] | null {
  const next = on ? [...new Set([...(list ?? []), id])] : (list ?? []).filter((x) => x !== id)
  return next.length || keepEmpty ? next : null
}

/** What a level's hidden models become with one shown or hidden: the list it has now (its own, else what it
 * follows) changed; empty, it stays an empty list only while a level above hides something */
export function hiddenPatch(explained: ExplainedPrefs, id: string, hide: boolean): string[] | null {
  const above =
    explained.hiddenModels.source.kind === 'here' ? inheritedHidden(explained) : explained.hiddenModels.value
  return toggled(explained.hiddenModels.value, id, hide, (above ?? []).length > 0)
}

/** The hidden models a level would follow without its own */
function inheritedHidden(explained: ExplainedPrefs): string[] | undefined {
  const groups = explained.parents.filter((p) => p.name !== null && p.prefs.hiddenModels !== undefined)
  if (groups.length) return [...new Set(groups.flatMap((g) => g.prefs.hiddenModels!))]
  return explained.parents.find((p) => p.name === null)?.prefs.hiddenModels
}
