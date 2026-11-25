<!-- Ported from WISP 3: app/frontend/lib/components/FormFooter.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  import Button from './Button.svelte'

  // An edit form's last row: Delete at the left, when there's something to
  // delete and the user may (owners, Q8), and Save at the right, so the two are far apart
  let {
    ondelete,
    deleteLabel = 'Delete',
    children,
  }: {
    /** Asks first and deletes; leave out for a new record or someone who may not delete */
    ondelete?: () => void
    deleteLabel?: string
    /** The submit button, and anything beside it */
    children: Snippet
  } = $props()
</script>

<div class="flex flex-wrap-reverse items-center justify-between gap-3 border-t border-line pt-4">
  {#if ondelete}
    <Button type="button" variant="danger-ghost" class="-ml-4" onclick={ondelete}>{deleteLabel}</Button>
  {:else}
    <span></span>
  {/if}
  <div class="ml-auto flex flex-wrap items-center gap-3">{@render children()}</div>
</div>
