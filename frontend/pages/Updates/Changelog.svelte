<!-- The changelog (/changelog, D112; Phase 7 step 7.3): entries newest first, filtered by kind (`?kind=outage`, through
     lib/viewState), each with an anchor (`#entry-12`) and a Copy link button; the Atom feed for feed readers -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'
  import { onDestroy } from 'svelte'

  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import { longDate } from '@/lib/models/format'
  import { routes } from '@/lib/routes'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { ChangelogProps } from '@/types'

  let { entries, kinds }: ChangelogProps = $props()

  // svelte-ignore state_referenced_locally
  const kindValues = ['all', ...kinds.map((k) => k.value)]
  const view = viewState({ kind: field(codecs.oneOf(kindValues), 'all') })
  onDestroy(() => view.destroy())

  const counts = $derived(
    entries.reduce<Record<string, number>>((found, e) => ({ ...found, [e.kind]: (found[e.kind] ?? 0) + 1 }), {}),
  )
  const options = $derived([
    { value: 'all', label: `All (${entries.length})` },
    ...kinds.filter((k) => counts[k.value]).map((k) => ({ value: k.value, label: `${k.label} (${counts[k.value]})` })),
  ])
  const kind = $derived($view.kind)
  const listed = $derived(kind === 'all' ? entries : entries.filter((e) => e.kind === kind))
  const kindLabel = $derived(kinds.find((k) => k.value === kind)?.label)

  let copied = $state<number | null>(null)
  let copyStatus = $state('')
  async function copyLink(id: number) {
    const url = `${window.location.origin}${routes.changelog()}#entry-${id}`
    try {
      await navigator.clipboard.writeText(url)
      copied = id
      copyStatus = 'Copied the link to this entry.'
    } catch {
      copied = null
      copyStatus = `Your browser didn’t let us copy. The link is ${url}`
    }
  }

  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>Changes and announcements · AgWeather</title>
  <meta
    name="description"
    content="Changes to AgWeather's data, models and API, and notices of outages, newest first, with an Atom feed."
  />
  <link
    rel="alternate"
    type="application/atom+xml"
    title="AgWeather changes and announcements"
    href={routes.changelogFeed()}
  />
</svelte:head>

<section class="max-w-prose space-y-6">
  <header class="space-y-3">
    <h1 class="text-3xl font-semibold">Changes and announcements</h1>
    <p>
      This page lists changes to AgWeather’s data, models and API, and notices of outages, newest first. To follow them
      in a feed reader, use the <a href={routes.changelogFeed()} class={link}>Atom feed</a>. For how current the data
      are right now, see the <Link href={routes.status()} class={link}>data status</Link> page. If you use the API, please
      <Link href={routes.apiUse()} class={link}>tell us how you use it</Link>.
    </p>
  </header>

  {#if entries.length === 0}
    <p class="text-ink-muted">No entries yet.</p>
  {:else}
    {#if options.length > 2}
      <SegmentedChoice
        legend="Show"
        name="changelog-kind"
        showLegend
        {options}
        value={kind}
        onchange={(value) => view.patch({ kind: value })}
      />
    {/if}
    <p class="sr-only" role="status">{copyStatus}</p>

    {#if listed.length === 0}
      <p class="text-ink-muted">
        {`No entries of the kind “${kindLabel ?? kind}”. `}<button
          type="button"
          class="cursor-pointer {link}"
          onclick={() => view.patch({ kind: 'all' })}
        >
          Show all entries
        </button>.
      </p>
    {/if}
    <ol class="space-y-6">
      {#each listed as entry (entry.id)}
        <li
          id={`entry-${entry.id}`}
          class="scroll-mt-24 space-y-2 border-t border-line pt-4 target:-mx-3 target:rounded-md target:bg-brand-50 target:px-3 target:pb-3"
        >
          <p class="flex flex-wrap items-center justify-between gap-x-3 text-sm text-ink-muted">
            <span><time datetime={entry.date}>{longDate(entry.date)}</time>{` · ${entry.kind_label}`}</span>
            <span class="flex items-center gap-3">
              <a href={`#entry-${entry.id}`} class="underline hover:text-ink">Link</a>
              <button
                type="button"
                class="cursor-pointer underline hover:text-ink"
                aria-label={`Copy the link to “${entry.title}”`}
                onclick={() => copyLink(entry.id)}
              >
                {copied === entry.id ? 'Copied' : 'Copy link'}
              </button>
            </span>
          </p>
          <h2 class="text-xl font-semibold">{entry.title}</h2>
          <!-- Rendered on the server with raw HTML escaped (updates/render.py) -->
          <!-- eslint-disable-next-line svelte/no-at-html-tags -->
          <div class="prose">{@html entry.body_html}</div>
          {#if entry.model || entry.endpoint}
            <p class="text-sm text-ink-muted">
              {#if entry.model}
                {'Model: '}<Link href={routes.model({ model_id: entry.model })} class={link}>{entry.model}</Link>
              {/if}
              {#if entry.model && entry.endpoint}{' · '}{/if}
              {#if entry.endpoint}
                {'API: '}<a href={`/api/v2/docs`} class={link}>{entry.endpoint}</a>
              {/if}
            </p>
          {/if}
        </li>
      {/each}
    </ol>
  {/if}
</section>
