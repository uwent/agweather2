<!-- Groups, minimal for now (track 3 step 8 brings their preferences): make one, rename or delete it, and choose its
     sites. A site can be in several groups. -->
<script lang="ts">
  import Button from '@/lib/components/Button.svelte'
  import {
    addGroup,
    groups,
    removeGroup,
    renameGroup,
    setInGroup,
    siteLabel,
    sites,
    sitesState,
  } from '@/lib/sites.svelte'

  let newName = $state('')
  let message = $state<string | null>(null)
  let choosing = $state<string | null>(null) // the group whose sites are listed
  let renaming = $state<{ id: string; name: string } | null>(null)

  function create(event: SubmitEvent) {
    event.preventDefault()
    const result = addGroup(newName)
    message = result.ok ? null : result.message
    if (result.ok) {
      newName = ''
      choosing = result.value.id
    }
  }

  function rename(event: SubmitEvent) {
    event.preventDefault()
    if (!renaming) return
    const result = renameGroup(renaming.id, renaming.name)
    message = result.ok ? null : result.message
    if (result.ok) renaming = null
  }
</script>

<div class="space-y-3 text-sm">
  {#if groups.length}
    <ul class="divide-y divide-line rounded-md border border-line bg-surface-raised">
      {#each groups as group (group.id)}
        <li class="space-y-2 p-3">
          {#if renaming?.id === group.id}
            <form class="flex flex-wrap items-center gap-2" onsubmit={rename}>
              <label for="rename-{group.id}" class="sr-only">New name for {group.name}</label>
              <input id="rename-{group.id}" class="rounded-md text-sm" bind:value={renaming.name} />
              <Button type="submit" class="px-3 py-1">Save</Button>
              <Button variant="ghost" class="px-3 py-1" onclick={() => (renaming = null)}>Cancel</Button>
            </form>
          {:else}
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span class="font-medium">{group.name}</span>
              <span class="text-ink-muted">
                {group.siteKeys.length === 1 ? '1 site' : `${group.siteKeys.length} sites`}
              </span>
              {#if !sitesState.readOnly}
                <span class="ml-auto flex gap-3">
                  <button
                    type="button"
                    class="relative underline"
                    aria-expanded={choosing === group.id}
                    onclick={() => (choosing = choosing === group.id ? null : group.id)}
                  >
                    Choose sites<span class="sr-only"> for {group.name}</span>
                  </button>
                  <button
                    type="button"
                    class="relative underline"
                    onclick={() => (renaming = { id: group.id, name: group.name })}
                  >
                    Rename<span class="sr-only"> {group.name}</span>
                  </button>
                  <button
                    type="button"
                    class="relative text-danger-ink underline"
                    onclick={() => removeGroup(group.id)}
                  >
                    Delete<span class="sr-only"> {group.name}</span>
                  </button>
                </span>
              {/if}
            </div>
          {/if}
          {#if choosing === group.id}
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
              {/each}
            </fieldset>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <p class="text-ink-muted">
      Groups gather sites, such as a farm’s fields or a client’s. A site can be in more than one group.
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
</div>
