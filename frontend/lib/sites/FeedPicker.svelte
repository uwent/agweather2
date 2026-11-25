<!-- "One model across your sites" on /sites: choose a model with risk levels and go to its feed (/sites/models/{id}) -->
<script lang="ts">
  import { router } from '@inertiajs/svelte'

  import { routes } from '../routes'

  let { models }: { models: { id: string; name: string; status: string; risk_levels: string[] }[] } = $props()

  const id = $props.id()
  const choices = $derived(
    models
      .filter((m) => m.status !== 'retired' && m.risk_levels.length)
      .toSorted((a, b) => a.name.localeCompare(b.name)),
  )
  let chosen = $state('')

  function go(event: SubmitEvent) {
    event.preventDefault()
    const model = chosen || choices[0]?.id
    if (model) router.visit(routes.sitesModelFeed({ model_id: model }))
  }
</script>

<form class="flex flex-wrap items-end gap-2" onsubmit={go}>
  <label class="flex flex-col gap-1 text-sm">
    <span class="font-medium">One model across your sites</span>
    <select id="{id}-model" class="max-w-full min-w-0 rounded-md text-sm" bind:value={chosen}>
      {#each choices as model (model.id)}<option value={model.id}>{model.name}</option>{/each}
    </select>
  </label>
  <button
    type="submit"
    class="cursor-pointer rounded-md border border-line bg-surface-raised px-3 py-2 text-sm font-medium hover:bg-surface focus-visible:outline-2 focus-visible:outline-brand-600"
  >
    Show
  </button>
</form>
