<script lang="ts">
  // A section's request that failed: the API's own words, and Try again when waiting could help (a 429 or
  // 503 says how long)
  let {
    message,
    retryable,
    retryAfter = null,
    retry,
  }: { message: string; retryable: boolean; retryAfter?: number | null; retry: () => void } = $props()

  const wait = $derived(
    retryAfter
      ? ` Try again in ${retryAfter < 90 ? `${retryAfter} seconds` : `${Math.ceil(retryAfter / 60)} minutes`}.`
      : '',
  )
</script>

<div class="rounded-md border border-danger/40 bg-surface-raised px-3 py-2 text-sm" role="alert">
  <p>{message}{wait}</p>
  {#if retryable}
    <button type="button" class="mt-1 cursor-pointer text-brand-600 underline hover:text-brand-700" onclick={retry}>
      Try again
    </button>
  {/if}
</div>
