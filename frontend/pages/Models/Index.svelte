<!-- The model catalog (/models, track 4): every model by crop, then disease, insect, crop stage or other, each with
     its one-line summary and a link to its page. Filtered by crop, group and words in the browser; the list is the
     page's props (web.modelpages, D117). -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import SearchFilter from '@/lib/components/SearchFilter.svelte'
  import SelectField from '@/lib/components/SelectField.svelte'
  import { catalogSections, modelCount } from '@/lib/models/catalog'
  import StatusBadge from '@/lib/models/StatusBadge.svelte'
  import { routes } from '@/lib/routes'
  import type { ModelsIndexProps } from '@/types'

  let { models, crops, groups }: ModelsIndexProps = $props()

  let crop = $state('')
  let group = $state('')
  let query = $state('')

  const sections = $derived(catalogSections(models, crops, groups, { crop, group, query }))
  const count = $derived(modelCount(sections))
  const filtered = $derived(Boolean(crop || group || query.trim()))

  const cropOptions = $derived([
    { value: '', label: 'All crops' },
    ...crops.map((c) => ({ value: c.id, label: c.name })),
    { value: 'other', label: 'Other models' },
  ])
  const groupOptions = $derived([
    { value: '', label: 'All kinds' },
    ...groups.map((g) => ({ value: g.id, label: g.name })),
  ])

  function clear() {
    crop = ''
    group = ''
    query = ''
  }
</script>

<svelte:head>
  <title>Crop disease and insect models · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <header class="max-w-prose space-y-2">
    <h1 class="text-3xl font-semibold">Crop disease and insect models</h1>
    <p>
      Each model uses weather data to estimate disease risk, insect development or a crop’s growth stage. Choose a model
      to see what it predicts, how to read it and where it applies, then see it on the map or at your own fields.
    </p>
    <p class="text-sm text-ink-muted">
      Every model is in beta while we check it against field observations and other systems. Its results may change
      before it is marked stable.
    </p>
  </header>

  <form
    class="flex flex-wrap items-end gap-4 rounded-lg border border-line bg-surface-raised p-4"
    role="search"
    aria-label="Filter the models"
    onsubmit={(event) => event.preventDefault()}
  >
    <div class="w-full sm:w-56"><SelectField label="Crop" name="crop" options={cropOptions} bind:value={crop} /></div>
    <div class="w-full sm:w-48">
      <SelectField label="Kind of model" name="group" options={groupOptions} bind:value={group} />
    </div>
    <div class="w-full space-y-1 sm:w-64">
      <span class="block text-sm font-medium" aria-hidden="true">Search</span>
      <div class="[&_input]:w-full">
        <SearchFilter bind:value={query} placeholder="A pest, disease or crop" label="Search the models" />
      </div>
    </div>
  </form>

  <p class="text-sm text-ink-muted" aria-live="polite">
    {count === 1 ? '1 model' : `${count} models`}{filtered ? ' match.' : '.'}
    {#if filtered}
      <button type="button" class="ml-2 text-brand-600 underline hover:text-brand-700" onclick={clear}>
        Show all models
      </button>
    {/if}
  </p>

  {#if sections.length === 0}
    <p>No models match. Try another crop or fewer words.</p>
  {:else if sections.length > 3}
    <nav aria-label="Crops on this page">
      <ul class="flex flex-wrap gap-x-3 gap-y-1 text-sm">
        {#each sections as section (section.id)}
          <li><a href="#crop-{section.id}" class="text-brand-600 underline hover:text-brand-700">{section.name}</a></li>
        {/each}
      </ul>
    </nav>
  {/if}

  {#each sections as section (section.id)}
    <section class="space-y-3 border-t border-line pt-4" aria-labelledby="crop-{section.id}">
      <h2 id="crop-{section.id}" class="scroll-mt-24 text-xl font-semibold">{section.name}</h2>
      <div class="grid gap-x-8 gap-y-4 lg:grid-cols-2">
        {#each section.groups as entry (entry.group.id)}
          <section aria-labelledby="crop-{section.id}-{entry.group.id}">
            <h3
              id="crop-{section.id}-{entry.group.id}"
              class="mb-2 text-sm font-semibold tracking-wide text-ink-muted uppercase"
            >
              {entry.group.name}
            </h3>
            <ul class="space-y-3">
              {#each entry.models as model (model.id)}
                <li>
                  <div class="flex flex-wrap items-center gap-x-2">
                    <Link
                      href={routes.model({ model_id: model.id })}
                      class="font-medium text-brand-600 underline hover:text-brand-700"
                    >
                      {model.name}
                    </Link>
                    <StatusBadge status={model.status} />
                  </div>
                  <p class="text-sm text-ink-muted">{model.summary}</p>
                </li>
              {/each}
            </ul>
          </section>
        {/each}
      </div>
    </section>
  {/each}
</div>
