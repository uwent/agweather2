<!-- The groups one saved site is in, as checkboxes, with a field to make a new group and put the site in it (a site can
     be in several groups). Used on its card on /sites, in its page's header and in the map's cell panel. -->
<script lang="ts">
  import { addGroup, groups, setInGroup, sitesState } from '@/lib/sites.svelte'

  let { siteKey, label }: { siteKey: string; label: string } = $props()

  const uid = $derived(`sg-${siteKey.replace(/[^\w-]/g, '_')}`)
  let newName = $state('')
  let message = $state('')

  function create(event: SubmitEvent) {
    event.preventDefault()
    const made = addGroup(newName)
    if (!made.ok) {
      message = made.message
      return
    }
    setInGroup(made.value.id, siteKey, true)
    message = `${label} added to ${made.value.name}.`
    newName = ''
  }

  function toggle(id: string, name: string, member: boolean) {
    const result = setInGroup(id, siteKey, member)
    message = result.ok ? `${label} ${member ? 'added to' : 'taken out of'} ${name}.` : result.message
  }
</script>

<div class="space-y-2 text-sm">
  {#if groups.length}
    <fieldset class="space-y-1" disabled={sitesState.readOnly}>
      <legend class="sr-only">Groups for {label}</legend>
      {#each groups as group (group.id)}
        <label class="flex items-center gap-2">
          <input
            type="checkbox"
            class="rounded-sm"
            checked={group.siteKeys.includes(siteKey)}
            onchange={(event) => toggle(group.id, group.name, event.currentTarget.checked)}
          />
          {group.name}
        </label>
      {/each}
    </fieldset>
  {:else}
    <p class="text-ink-muted">You have no groups yet. A group gathers sites, such as a farm’s fields.</p>
  {/if}
  {#if !sitesState.readOnly}
    <form class="flex flex-wrap items-center gap-2" onsubmit={create}>
      <label for="{uid}-new" class="sr-only">New group for {label}</label>
      <input id="{uid}-new" class="min-w-0 flex-1 rounded-md text-sm" placeholder="New group" bind:value={newName} />
      <button
        type="submit"
        class="rounded-md border border-line bg-surface-raised px-2.5 py-1 font-medium hover:bg-surface"
        aria-label="Add a new group with {label} in it"
      >
        Add
      </button>
    </form>
  {/if}
  <p role="status" class="text-ink-muted">{message}</p>
</div>
