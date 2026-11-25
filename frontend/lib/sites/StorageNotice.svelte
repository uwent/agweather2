<!-- Says when saved sites can't be kept (storage blocked), are read-only (saved by a newer version), or couldn't be
     read; nothing otherwise -->
<script lang="ts">
  import { sitesState } from '@/lib/sites.svelte'

  const message = $derived(
    sitesState.readOnly
      ? 'Your sites were saved by a newer version of AgWeather, so you can see them here but not change them. Reload the page to get the newer version.'
      : !sitesState.persistent
        ? 'This browser isn’t letting AgWeather save your sites (as in a private window), so the sites you add last only until you leave this page. Export them to keep a copy.'
        : sitesState.unreadable
          ? 'We couldn’t read the sites saved in this browser, so the list starts empty. Sites you add now replace them.'
          : null,
  )
</script>

{#if message}
  <p class="rounded-md border border-line bg-brand-50 px-3 py-2 text-sm" role="status">{message}</p>
{/if}
