<!-- Ported from WISP 3: app/frontend/lib/components/Dialog.svelte -->
<script lang="ts">
  import { type Snippet, tick } from 'svelte'
  import { Dialog } from 'bits-ui'

  import { type Change, ChangeTracker, describeChanges } from '@/lib/formChanges'
  import { changesMessage, confirmHistoryMoves } from '@/lib/unsaved.svelte'

  import Button from './Button.svelte'

  let {
    open = $bindable(false),
    title,
    description,
    children,
    wide = false,
    widest = false,
    guard = false,
  }: {
    open?: boolean
    title: string
    description?: string
    children: Snippet
    wide?: boolean
    /** As wide as the window allows, for a wide table */
    widest?: boolean
    /**
     * For a dialog holding a form: Escape, a click outside or ✕ with changes made asks first, in the
     * dialog (Save changes, Discard, Keep editing). Closing it from code (after a save,
     * a delete) never asks.
     */
    guard?: boolean
  } = $props()

  // The form's part of the dialog, hidden (not unmounted, so its values stay) while asking
  let body = $state<HTMLElement>()
  let asking = $state<Change[] | null>(null)
  let question = $state<HTMLElement>()
  const tracker = new ChangeTracker(() => body)

  $effect(() => {
    if (!guard || !open) return
    tracker.reset()
    tracker.start()
    // The browser's Back would take the page, and the dialog's changes with it
    const offHistory = confirmHistoryMoves(() => changesMessage(tracker.changes()))
    return () => {
      offHistory()
      tracker.stop()
      asking = null
    }
  })

  /** The changes made in a guarded dialog's form (for a link out of it to ask about) */
  export function changes(): Change[] {
    return guard && open ? tracker.changes() : []
  }

  /** Escape, a click outside or ✕: closes, unless there are changes to ask about */
  function requestClose() {
    if (asking) return keepEditing()
    const changes = guard ? tracker.changes() : []
    if (!changes.length) {
      open = false
      return
    }
    asking = changes
    tick().then(() => question?.focus())
  }

  async function keepEditing() {
    const first = asking?.[0]?.control
    asking = null
    await tick()
    if (first?.isConnected) first.focus()
  }

  async function save() {
    asking = null
    await tick()
    // A refused save shows the form again with its errors; a saved one closes the dialog from code
    body?.querySelector('form')?.requestSubmit()
  }

  function discard() {
    asking = null
    open = false
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-40 bg-black/40" />
    <!-- No scroll lock: hiding the page's scrollbar shifted and shook the page, so the
         page behind still scrolls, and the dialog scrolls on its own without dragging it -->
    <Dialog.Content
      preventScroll={false}
      onEscapeKeydown={(event) => {
        if (!guard) return
        event.preventDefault()
        requestClose()
      }}
      onInteractOutside={(event) => {
        if (!guard) return
        event.preventDefault()
        if (!asking) requestClose()
      }}
      class="fixed top-1/2 left-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] -translate-1/2 overflow-y-auto overscroll-contain
        rounded-lg border border-line bg-surface-raised p-6 shadow-xl {widest
        ? 'max-w-6xl'
        : wide
          ? 'max-w-2xl'
          : 'max-w-lg'}"
    >
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <Dialog.Title class="text-lg font-medium">{title}</Dialog.Title>
          {#if description}<Dialog.Description class="text-sm text-ink-muted">{description}</Dialog.Description>{/if}
        </div>
        <button type="button" class="text-ink-muted hover:text-ink" aria-label="Close" onclick={requestClose}>✕</button>
      </div>
      <div bind:this={body} hidden={asking !== null}>
        {@render children()}
      </div>
      {#if asking}
        <section class="space-y-4" aria-labelledby="dialog-unsaved-heading">
          <h3 id="dialog-unsaved-heading" bind:this={question} tabindex="-1" class="font-medium focus:outline-none">
            Save your changes?
          </h3>
          <ul class="list-disc space-y-1 pl-5 text-sm">
            {#each describeChanges(asking) as line, index (index)}<li>{line}</li>{/each}
          </ul>
          <div class="flex flex-wrap-reverse items-center justify-between gap-3 border-t border-line pt-4">
            <Button variant="ghost" class="-ml-4" onclick={keepEditing}>Keep editing</Button>
            <div class="ml-auto flex flex-wrap items-center gap-3">
              <Button variant="secondary" onclick={discard}>Discard</Button>
              <Button onclick={save}>Save changes</Button>
            </div>
          </div>
        </section>
      {/if}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
