<!-- The pests and diseases (/topics, track 4): every topic page by crop, then the crop itself, diseases, insects and
     field management. Filtered by crop and words in the browser; the list is the page's props (web.topicpages,
     D117). -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import SearchFilter from '@/lib/components/SearchFilter.svelte'
  import SelectField from '@/lib/components/SelectField.svelte'
  import { routes } from '@/lib/routes'
  import { topicCount, topicSections } from '@/lib/topics'
  import type { TopicsIndexProps } from '@/types'

  let { topics, crops, kinds }: TopicsIndexProps = $props()

  let crop = $state('')
  let query = $state('')

  const sections = $derived(topicSections(topics, crops, kinds, { crop, query }))
  const count = $derived(topicCount(sections))
  const filtered = $derived(Boolean(crop || query.trim()))

  const cropOptions = $derived([
    { value: '', label: 'All crops' },
    ...crops.map((c) => ({ value: c.id, label: c.name })),
    { value: 'other', label: 'Other topics' },
  ])

  function clear() {
    crop = ''
    query = ''
  }

  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>Pests and diseases · AgWeather</title>
  <meta
    name="description"
    content="How to recognize crop pests and diseases, how they develop and how to manage them, with the AgWeather models for each."
  />
</svelte:head>

<div class="space-y-6">
  <header class="max-w-prose space-y-2">
    <p class="text-sm">
      <Link href={routes.models()} class={link}>Models</Link>
    </p>
    <h1 class="text-3xl font-semibold">Pests and diseases</h1>
    <p>
      Each page explains how to recognize a pest or disease, how it develops, the damage it does and how to manage it,
      with the AgWeather models that predict it. Pages for some crops describe their growth stages.
    </p>
  </header>

  <form
    class="flex flex-wrap items-end gap-4 rounded-lg border border-line bg-surface-raised p-4"
    role="search"
    aria-label="Filter the topics"
    onsubmit={(event) => event.preventDefault()}
  >
    <div class="w-full sm:w-56"><SelectField label="Crop" name="crop" options={cropOptions} bind:value={crop} /></div>
    <div class="w-full space-y-1 sm:w-64">
      <span class="block text-sm font-medium" aria-hidden="true">Search</span>
      <div class="[&_input]:w-full">
        <SearchFilter bind:value={query} placeholder="A pest, disease or crop" label="Search the topics" />
      </div>
    </div>
  </form>

  <p class="text-sm text-ink-muted" aria-live="polite">
    {count === 1 ? '1 topic' : `${count} topics`}{filtered ? ' match.' : '.'}
    {#if filtered}
      <button type="button" class="ml-2 {link}" onclick={clear}>Show all topics</button>
    {/if}
  </p>

  {#if sections.length === 0}
    <p>No topics match. Try another crop or fewer words.</p>
  {:else if sections.length > 3}
    <nav aria-label="Crops on this page">
      <ul class="flex flex-wrap gap-x-3 gap-y-1 text-sm">
        {#each sections as section (section.id)}
          <li><a href="#crop-{section.id}" class={link}>{section.name}</a></li>
        {/each}
      </ul>
    </nav>
  {/if}

  {#each sections as section (section.id)}
    <section class="space-y-3 border-t border-line pt-4" aria-labelledby="crop-{section.id}">
      <h2 id="crop-{section.id}" class="scroll-mt-24 text-xl font-semibold">{section.name}</h2>
      <div class="grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
        {#each section.groups as entry (entry.kind.id)}
          <section aria-labelledby="crop-{section.id}-{entry.kind.id}">
            <h3
              id="crop-{section.id}-{entry.kind.id}"
              class="mb-2 text-sm font-semibold tracking-wide text-ink-muted uppercase"
            >
              {entry.kind.name}
            </h3>
            <ul class="space-y-2">
              {#each entry.topics as topic (topic.id)}
                <li>
                  <Link href={routes.topic({ topic_id: topic.id })} class="font-medium {link}">{topic.title}</Link>
                  {#if topic.scientific_name && topic.kind !== 'crop'}
                    <span class="block text-sm text-ink-muted italic">{topic.scientific_name}</span>
                  {/if}
                </li>
              {/each}
            </ul>
          </section>
        {/each}
      </div>
    </section>
  {/each}
</div>
