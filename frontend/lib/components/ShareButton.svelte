<script lang="ts">
  import { Popover } from 'bits-ui'

  // Share (D118): the link to the view on screen, with its settings, in a small popover with Copy. The address
  // bar stays on the page's plain path, so this is how a reader sends a view. `url` is read as the popover
  // opens (pass `() => view.shareUrl()`), so the link is the view as it is then.
  let { url, class: className = '' }: { url: string | (() => string); class?: string } = $props()

  const uid = $props.id()
  let open = $state(false)
  let link = $state('')
  let status = $state('')
  let field = $state<HTMLInputElement | null>(null)

  function opened(next: boolean) {
    if (next) {
      link = typeof url === 'function' ? url() : url
      status = ''
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(link)
      status = 'Copied the link.'
    } catch {
      field?.select()
      status = 'Your browser didn’t let us copy. The link is selected: copy it with Ctrl+C, or ⌘C on a Mac.'
    }
  }
</script>

<Popover.Root bind:open onOpenChange={opened}>
  <Popover.Trigger
    class="border-line bg-surface-raised text-ink hover:border-frame focus-visible:outline-brand-600 inline-flex items-center gap-1.5 rounded-md border px-2.5
      py-1 text-sm focus-visible:outline-2 {className}"
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
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
    Share
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Content
      side="bottom"
      align="end"
      sideOffset={4}
      collisionPadding={16}
      aria-labelledby="share-{uid}"
      onOpenAutoFocus={(event) => {
        event.preventDefault()
        field?.focus()
        field?.select()
      }}
      class="border-line bg-surface-raised text-ink z-50 w-80 max-w-[calc(100vw-2rem)] rounded-md border p-3 text-sm
        shadow-lg"
    >
      <label id="share-{uid}" for="share-link-{uid}" class="block font-semibold">Link to this view</label>
      <p class="text-ink-muted mt-1 text-xs">Anyone with this link sees the page with your current settings.</p>
      <div class="mt-2 flex gap-2">
        <input
          bind:this={field}
          id="share-link-{uid}"
          type="text"
          readonly
          value={link}
          class="border-line bg-surface text-ink min-w-0 flex-1 rounded-md border px-2 py-1 text-xs"
          onfocus={(event) => event.currentTarget.select()}
        />
        <button
          type="button"
          class="bg-brand-600 text-surface hover:bg-brand-700 focus-visible:outline-brand-600 rounded-md px-3 py-1 text-sm
            font-semibold focus-visible:outline-2 focus-visible:outline-offset-2"
          onclick={copy}
        >
          Copy
        </button>
      </div>
      <p class="text-ink-muted mt-2 text-xs" role="status">{status}</p>
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
