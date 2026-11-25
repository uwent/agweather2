<!-- Placeholder for WISP 3: app/frontend/lib/components/Dialog.svelte, so the charts' DataDialog runs in wave 1 (b).
     Wave 1 (a) ports the real one (with its unsaved-changes guard); on merging, keep (a)'s file. -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import { Dialog } from 'bits-ui'

  let {
    open = $bindable(false),
    title,
    description,
    children,
    wide = false,
    widest = false,
  }: {
    open?: boolean
    title: string
    description?: string
    children: Snippet
    wide?: boolean
    widest?: boolean
  } = $props()
</script>

<Dialog.Root bind:open>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-40 bg-black/40" />
    <Dialog.Content
      preventScroll={false}
      class="border-line bg-surface-raised fixed top-1/2 left-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] -translate-1/2
        overflow-y-auto overscroll-contain rounded-lg border p-6 shadow-xl {widest
        ? 'max-w-6xl'
        : wide
          ? 'max-w-2xl'
          : 'max-w-lg'}"
    >
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <Dialog.Title class="text-lg font-medium">{title}</Dialog.Title>
          {#if description}<Dialog.Description class="text-ink-muted text-sm">{description}</Dialog.Description>{/if}
        </div>
        <button type="button" class="text-ink-muted hover:text-ink" aria-label="Close" onclick={() => (open = false)}
          >✕</button
        >
      </div>
      {@render children()}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
