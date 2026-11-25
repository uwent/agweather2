<!-- Groups on /sites (track 3 step 8): make one, rename, delete or reorder it, choose its sites, set its preferences
     and show it on the map. A site can be in several groups. The order matters where two groups a site is in set a
     different planting date or model setting: the higher one's wins. -->
<script lang="ts">
  import { tick } from 'svelte'

  import Button from '@/lib/components/Button.svelte'
  import {
    addGroup,
    groups,
    moveGroup,
    removeGroup,
    renameGroup,
    setInGroup,
    siteLabel,
    sites,
    sitesSnapshot,
    sitesState,
    type Group,
  } from '@/lib/sites.svelte'
  import type { ModelSettings } from '@/types'

  import { groupMapUrl } from './groupMap'
  import { explainPrefs } from './prefs'
  import PrefsPanel from './PrefsPanel.svelte'

  let {
    models,
    crops,
    settings,
  }: {
    models: readonly { id: string; name: string; crops: string[] }[]
    crops: readonly { id: string; name: string }[]
    settings: readonly ModelSettings[]
  } = $props()

  let newName = $state('')
  let message = $state<string | null>(null)
  let announcement = $state('')
  // What's open under each group: its sites, or its preferences
  let open = $state<{ id: string; part: 'sites' | 'prefs' } | null>(null)
  let renaming = $state<{ id: string; name: string } | null>(null)
  let deleting = $state<string | null>(null)

  function create(event: SubmitEvent) {
    event.preventDefault()
    const result = addGroup(newName)
    message = result.ok ? null : result.message
    if (result.ok) {
      newName = ''
      open = { id: result.value.id, part: 'sites' }
      announcement = `${result.value.name} added. Choose its sites below.`
    }
  }

  function rename(event: SubmitEvent) {
    event.preventDefault()
    if (!renaming) return
    const result = renameGroup(renaming.id, renaming.name)
    message = result.ok ? null : result.message
    if (result.ok) renaming = null
  }

  function remove(group: Group) {
    removeGroup(group.id)
    deleting = null
    announcement = `${group.name} deleted. Its sites are still saved.`
  }

  async function move(group: Group, to: number) {
    const up = to < groups.indexOf(group)
    moveGroup(group.id, to)
    announcement = `${group.name} moved to position ${to + 1} of ${groups.length}.`
    await tick()
    for (const name of [`Move ${group.name} ${up ? 'up' : 'down'}`, `Move ${group.name} ${up ? 'down' : 'up'}`]) {
      const button = document.querySelector<HTMLButtonElement>(`button[aria-label="${CSS.escape(name)}"]`)
      if (button && !button.disabled) {
        button.focus()
        break
      }
    }
  }

  const toggle = (id: string, part: 'sites' | 'prefs') =>
    (open = open?.id === id && open.part === part ? null : { id, part })

  // The map link: the group's sites, and its map layer (its own preference, else all sites')
  const mapUrl = (group: Group) =>
    groupMapUrl(group, sites, explainPrefs(sitesSnapshot(), { kind: 'group', id: group.id }).layer.value)

  const action = 'underline hover:text-ink'
</script>

<div class="space-y-3 text-sm">
  {#if groups.length}
    <p class="max-w-prose text-ink-muted">
      Where two groups a site is in set a different planting date or model setting, the group higher in this list wins.
      Their crops and hidden models are combined.
    </p>
    <ul class="divide-y divide-line rounded-md border border-line bg-surface-raised" aria-label="Your groups">
      {#each groups as group, index (group.id)}
        <li class="space-y-3 p-3" data-testid="group-{group.name}">
          {#if renaming?.id === group.id}
            <form class="flex flex-wrap items-center gap-2" onsubmit={rename}>
              <label for="rename-{group.id}" class="sr-only">New name for {group.name}</label>
              <input id="rename-{group.id}" class="rounded-md text-sm" bind:value={renaming.name} />
              <Button type="submit" class="px-3 py-1">Save</Button>
              <Button variant="ghost" class="px-3 py-1" onclick={() => (renaming = null)}>Cancel</Button>
            </form>
          {:else}
            <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
              {#if !sitesState.readOnly && groups.length > 1}
                <span class="flex gap-1">
                  <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink disabled:opacity-40"
                    aria-label="Move {group.name} up"
                    title="Move up"
                    disabled={index === 0}
                    onclick={() => move(group, index - 1)}
                  >
                    <span aria-hidden="true">↑</span>
                  </button>
                  <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink disabled:opacity-40"
                    aria-label="Move {group.name} down"
                    title="Move down"
                    disabled={index === groups.length - 1}
                    onclick={() => move(group, index + 1)}
                  >
                    <span aria-hidden="true">↓</span>
                  </button>
                </span>
              {/if}
              <span class="font-medium">{group.name}</span>
              <span class="text-ink-muted">
                {group.siteKeys.length === 1 ? '1 site' : `${group.siteKeys.length} sites`}
              </span>
              <span class="flex flex-wrap gap-x-3 gap-y-1 text-ink-muted sm:ml-auto">
                {#if group.siteKeys.length}
                  <a href={mapUrl(group)} class="text-brand-600 underline hover:text-brand-700">Show on the map</a>
                {/if}
                {#if !sitesState.readOnly}
                  <button
                    type="button"
                    class={action}
                    aria-label="Choose sites for {group.name}"
                    aria-expanded={open?.id === group.id && open.part === 'sites'}
                    onclick={() => toggle(group.id, 'sites')}
                  >
                    Choose sites
                  </button>
                {/if}
                <button
                  type="button"
                  class={action}
                  aria-label="Preferences for {group.name}"
                  aria-expanded={open?.id === group.id && open.part === 'prefs'}
                  onclick={() => toggle(group.id, 'prefs')}
                >
                  Preferences
                </button>
                {#if !sitesState.readOnly}
                  <button
                    type="button"
                    class={action}
                    aria-label="Rename {group.name}"
                    onclick={() => (renaming = { id: group.id, name: group.name })}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    class="text-danger-ink underline"
                    aria-label="Delete {group.name}"
                    onclick={() => (deleting = group.id)}
                  >
                    Delete
                  </button>
                {/if}
              </span>
            </div>
            {#if deleting === group.id}
              <p class="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>{`Delete ${group.name} and its preferences? Its sites stay saved.`}</span>
                <button
                  type="button"
                  class="font-medium text-danger-ink underline"
                  aria-label="Delete {group.name} now"
                  onclick={() => remove(group)}
                >
                  Delete
                </button>
                <button type="button" class="underline" onclick={() => (deleting = null)}>Keep</button>
              </p>
            {/if}
          {/if}
          {#if open?.id === group.id && open.part === 'sites'}
            <fieldset class="grid gap-1 sm:grid-cols-2">
              <legend class="sr-only">Sites in {group.name}</legend>
              {#each sites as site (site.key)}
                <label class="flex items-center gap-2">
                  <input
                    type="checkbox"
                    class="rounded-sm"
                    checked={group.siteKeys.includes(site.key)}
                    onchange={(event) => setInGroup(group.id, site.key, event.currentTarget.checked)}
                  />
                  {siteLabel(site)}
                </label>
              {:else}
                <p class="text-ink-muted">Save a site first, then put it in this group.</p>
              {/each}
            </fieldset>
          {/if}
          {#if open?.id === group.id && open.part === 'prefs'}
            <div class="rounded-md border border-line bg-surface p-3">
              <h3 class="mb-2 text-base font-semibold">{`Preferences for ${group.name}`}</h3>
              <PrefsPanel level={{ kind: 'group', id: group.id }} {models} {crops} {settings} />
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <p class="max-w-prose text-ink-muted">
      Groups gather sites, such as a farm’s fields or a client’s. A site can be in more than one group. A group can have
      its own crops, models and settings, and you can show its sites together on the map.
    </p>
  {/if}
  {#if !sitesState.readOnly}
    <form class="flex flex-wrap items-end gap-2" onsubmit={create}>
      <div>
        <label for="new-group" class="mb-1 block font-medium">New group</label>
        <input id="new-group" class="rounded-md text-sm" bind:value={newName} placeholder="Such as North farm" />
      </div>
      <Button type="submit" variant="secondary">Add group</Button>
    </form>
  {/if}
  {#if message}<p class="text-danger-ink" role="alert">{message}</p>{/if}
  <p class="sr-only" role="status" aria-live="polite">{announcement}</p>
</div>
