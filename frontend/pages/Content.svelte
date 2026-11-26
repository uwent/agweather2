<!-- A page of text from content/pages (/about, /accessibility, /contact): a stub (2026-11-26) until track 7 builds it. -->
<script lang="ts">
  import type { ContentPageProps } from '@/types'

  let { title }: ContentPageProps = $props()
</script>

<svelte:head>
  <title>{title} · AgWeather</title>
</svelte:head>

<div class="mx-auto max-w-3xl px-4 py-8">
  <h1 class="text-2xl font-semibold text-ink">{title}</h1>
  <p class="mt-4 text-ink-muted">We are building this page.</p>
</div>
