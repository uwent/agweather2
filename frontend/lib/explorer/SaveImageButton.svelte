<script lang="ts">
  import { Popover } from 'bits-ui'

  // Save image (frontend.md F13): the map as a PNG with its title, legend and credits, made in the browser. Beside
  // Share in the controls' toolbar; a small popover says what the image holds and, when the reader has saved sites,
  // offers to name those in view.
  let {
    save,
    sites = 0,
    disabled = false,
    compact = false,
  }: {
    /** Makes and downloads the image; rejects with a message for the reader */
    save: (options: { labels: boolean }) => Promise<void>
    /** How many sites the reader has saved */
    sites?: number
    disabled?: boolean
    /** The icon alone, on a phone's crowded bar */
    compact?: boolean
  } = $props()

  const uid = $props.id()
  let open = $state(false)
  let labels = $state(true)
  let busy = $state(false)
  let status = $state('')

  async function run() {
    busy = true
    status = 'Making the image…'
    try {
      await save({ labels: sites > 0 && labels })
      status = 'Saved. Look for the image in your downloads.'
    } catch (error) {
      status = error instanceof Error ? error.message : String(error)
    } finally {
      busy = false
    }
  }
</script>

<Popover.Root bind:open onOpenChange={(next) => next && (status = '')}>
  <Popover.Trigger
    {disabled}
    aria-label="Save image"
    class="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-raised px-2.5 py-1 text-sm text-ink
      hover:border-frame focus-visible:outline-2 focus-visible:outline-brand-600 disabled:opacity-50"
  >
    <svg
      viewBox="0 0 24 24"
      class="size-4"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </svg>
    {#if !compact}Save image{/if}
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Content
      side="bottom"
      align="end"
      sideOffset={4}
      collisionPadding={16}
      aria-labelledby="save-image-{uid}"
      class="z-50 w-80 max-w-[calc(100vw-2rem)] space-y-2 rounded-md border border-line bg-surface-raised p-3 text-sm
        text-ink shadow-lg"
    >
      <p id="save-image-{uid}" class="font-semibold">Save the map as an image</p>
      <p class="text-xs text-ink-muted">
        You get a PNG of the map as you see it now, with its title, date, legend and sources, for a report or a
        newsletter.
      </p>
      {#if sites > 0}
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={labels} class="accent-brand-600" />
          Name my saved sites on the map
        </label>
      {/if}
      <button
        type="button"
        class="rounded-md bg-brand-600 px-3 py-1 text-sm font-semibold text-surface hover:bg-brand-700
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60"
        disabled={busy}
        onclick={run}
        data-testid="save-image"
      >
        Save PNG
      </button>
      <p class="text-xs text-ink-muted" role="status">{status}</p>
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
