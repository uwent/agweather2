<script lang="ts">
  import { page } from '@inertiajs/svelte'

  import type { HomeProps } from '@/types'

  let { api_docs_url }: HomeProps = $props()
</script>

<svelte:head>
  <title>AgWeather</title>
</svelte:head>

<section class="space-y-3">
  <h1 class="text-3xl font-semibold">AgWeather</h1>
  <p class="text-ink-muted max-w-prose">
    Hourly weather, degree days, and crop disease and insect risk for the Upper Midwest. The new AgWeather is being
    built for the 2027 growing season.
  </p>
  <p class="max-w-prose">
    Developers can try the <a href={api_docs_url} class="text-brand-600 hover:text-brand-700 underline">version 2 API</a
    >
    as it takes shape.
  </p>
  <p class="text-ink-muted text-xs">Version {page.props.app.version} · {page.props.app.service_box}</p>
</section>
