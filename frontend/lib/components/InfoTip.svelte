<!-- Placeholder for WISP 3: app/frontend/lib/components/InfoTip.svelte, so ChartCard runs in wave 1 (b).
     Wave 1 (a) ports the real one (with its glossary term); on merging, keep (a)'s file. -->
<script lang="ts">
  import { Popover } from 'bits-ui'

  let { text, label = 'About this' }: { text: string; label?: string } = $props()

  const uid = $props.id()
  let open = $state(false)
</script>

<Popover.Root bind:open>
  <Popover.Trigger
    aria-label={label}
    aria-describedby={open ? `tip-${uid}` : undefined}
    openOnHover
    openDelay={150}
    class="text-ink-muted hover:bg-surface hover:text-ink focus-visible:outline-brand-600 data-[state=open]:text-ink -my-1 inline-flex size-6 shrink-0 cursor-help
      items-center justify-center rounded-full focus-visible:outline-2"
  >
    <svg
      viewBox="0 0 24 24"
      class="size-4"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </svg>
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Content
      id="tip-{uid}"
      role="tooltip"
      side="bottom"
      align="end"
      sideOffset={4}
      collisionPadding={16}
      trapFocus={false}
      onOpenAutoFocus={(event) => event.preventDefault()}
      onCloseAutoFocus={(event) => event.preventDefault()}
      class="border-line bg-surface-raised text-ink z-50 w-72 max-w-[calc(100vw-2rem)] rounded-md border p-3
        text-xs/relaxed font-normal shadow-lg"
    >
      <p>{text}</p>
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
