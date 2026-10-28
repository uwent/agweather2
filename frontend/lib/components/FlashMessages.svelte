<script lang="ts">
  import { page } from '@inertiajs/svelte'

  // Django's messages (inertia-django sends them as flash.messages). Dismissed messages stay hidden until
  // the server sends new ones.
  let dismissed = $state(false)
  let lastFlash: unknown = null

  $effect(() => {
    if (page.flash !== lastFlash) {
      lastFlash = page.flash
      dismissed = false
    }
  })

  const messages = $derived(dismissed ? [] : (page.flash?.messages ?? []))
</script>

{#each messages as message, index (index)}
  {@const isError = message.level === 'error' || message.level === 'warning'}
  <div
    role={isError ? 'alert' : 'status'}
    class="flex items-start justify-between gap-4 rounded-md border px-4 py-3 text-sm
      {isError ? 'border-danger/40 bg-danger/10' : 'border-success/40 bg-success/10'}"
  >
    <p>{message.message}</p>
    <button
      type="button"
      class="text-ink-muted hover:text-ink"
      aria-label="Dismiss message"
      onclick={() => (dismissed = true)}>✕</button
    >
  </div>
{/each}
