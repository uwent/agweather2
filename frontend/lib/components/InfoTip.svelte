<!-- Ported from WISP 3: app/frontend/lib/components/InfoTip.svelte -->
<script lang="ts">
  import { Popover } from 'bits-ui'

  import type { GlossaryEntry } from '@/lib/glossary'

  // An (i) button with an explanation: shown while a mouse hovers it, and toggled by click, tap,
  // Enter or Space (a click pins a hovered one); Escape or a click elsewhere closes it. The popup is
  // portalled, so a scrolling dialog doesn't clip it, never takes focus, and describes the button
  // while it's open. A form's tip may add a glossary term's definition below its own text.
  let { text, term, label = 'About this' }: { text: string; term?: GlossaryEntry; label?: string } = $props()

  const uid = $props.id()
  let open = $state(false)
</script>

<Popover.Root bind:open>
  <Popover.Trigger
    aria-label={label}
    aria-describedby={open ? `tip-${uid}` : undefined}
    openOnHover
    openDelay={150}
    class="-my-1 inline-flex size-6 shrink-0 cursor-help items-center justify-center rounded-full text-ink-muted hover:bg-surface
      hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600 data-[state=open]:text-ink"
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
      class="z-50 w-72 max-w-[calc(100vw-2rem)] rounded-md border border-line bg-surface-raised p-3 text-xs/relaxed
        font-normal text-ink shadow-lg"
    >
      <p>{text}</p>
      {#if term}
        <p class="mt-2 border-t border-line pt-2 text-ink-muted">
          <strong class="font-semibold text-ink">{`${term.term}:`}</strong>{` ${term.definition}`}
        </p>
      {/if}
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
