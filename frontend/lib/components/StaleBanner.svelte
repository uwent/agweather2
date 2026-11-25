<!-- The stale-data banner (docs/frontend.md, States and feedback): shown on every page while the shared `status` prop
     says observations or the forecast are behind -->
<script lang="ts">
  import { page } from '@inertiajs/svelte'

  import { staleMessages } from '@/lib/dataStatus'

  const messages = $derived(staleMessages(page.props.status))
</script>

{#if messages.length}
  <div class="border-b border-line bg-brand-50 text-ink" role="status">
    <div class="mx-auto max-w-6xl space-y-1 px-4 py-2 text-sm">
      {#each messages as message (message)}
        <p>{message}</p>
      {/each}
    </div>
  </div>
{/if}
