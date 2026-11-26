<!-- The tools (track 5): a card for each tool built (lib/tools/catalog.ts), led by the question it answers. -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import { routes } from '@/lib/routes'
  import { TOOLS } from '@/lib/tools/catalog'
</script>

<svelte:head>
  <title>Tools · AgWeather</title>
</svelte:head>

<div class="space-y-6">
  <div class="space-y-2">
    <h1 class="text-2xl font-semibold sm:text-3xl">Tools</h1>
    <p class="max-w-prose">
      Each tool answers one question for a place you choose, from the same weather data as our maps and models.
    </p>
  </div>

  <ul class="grid gap-4 sm:grid-cols-2">
    {#each TOOLS as tool (tool.href)}
      <li class="space-y-2 rounded-lg border border-line bg-surface-raised p-4">
        <h2 class="text-lg font-semibold">
          <Link href={tool.href} class="text-brand-600 underline hover:text-brand-700">{tool.title}</Link>
        </h2>
        <p class="font-medium">{tool.question}</p>
        <p class="text-sm text-ink-muted">{tool.text}</p>
      </li>
    {/each}
  </ul>

  <p class="max-w-prose text-sm text-ink-muted">
    For weather and crop risk across the region, open the <Link href={routes.map()} class="underline hover:text-ink">
      map
    </Link>; for one place over time, open a place’s page from <Link
      href={routes.sites()}
      class="underline hover:text-ink"
    >
      your sites
    </Link>.
  </p>
</div>
