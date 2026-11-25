<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import type { ChangelogProps } from '@/types'

  // A minimal page (D112); Phase 7 designs it
  let { entries }: ChangelogProps = $props()

  const longDate = new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
  const written = (iso: string) => longDate.format(new Date(`${iso}T00:00:00Z`))
</script>

<svelte:head>
  <title>Changes and announcements · AgWeather</title>
  <link
    rel="alternate"
    type="application/atom+xml"
    title="AgWeather changes and announcements"
    href="/changelog.atom"
  />
</svelte:head>

<section class="max-w-prose space-y-6">
  <header class="space-y-2">
    <h1 class="text-3xl font-semibold">Changes and announcements</h1>
    <p>
      This page lists changes to AgWeather's data, models and API, and notices of outages, newest first. To follow them
      in a feed reader, use the <a href="/changelog.atom" class="text-brand-600 hover:text-brand-700 underline"
        >Atom feed</a
      >. If you use the API, please
      <Link href="/api-use" class="text-brand-600 hover:text-brand-700 underline">tell us how you use it</Link>.
    </p>
  </header>

  {#if entries.length === 0}
    <p class="text-ink-muted">No entries yet.</p>
  {:else}
    <ol class="space-y-6">
      {#each entries as entry (entry.id)}
        <li id={`entry-${entry.id}`} class="border-line space-y-2 border-t pt-4">
          <p class="text-ink-muted text-sm">
            <time datetime={entry.date}>{written(entry.date)}</time>{` · ${entry.kind_label}`}
          </p>
          <h2 class="text-xl font-semibold">{entry.title}</h2>
          <!-- Rendered on the server with raw HTML escaped (updates/render.py) -->
          <!-- eslint-disable-next-line svelte/no-at-html-tags -->
          <div class="prose">{@html entry.body_html}</div>
        </li>
      {/each}
    </ol>
  {/if}
</section>
