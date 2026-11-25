<!-- Ported from WISP 3: app/frontend/lib/components/Term.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import { Popover } from 'bits-ui'

  import { glossaryEntry, type GlossaryEntry } from '@/lib/glossary'

  // A glossary term in running text: underlined with dots, with its definition shown while a mouse
  // hovers it, and toggled by click, tap, Enter or Space (a click pins a hovered one). The popup
  // never takes focus, and stays on screen at any width. While it's open the term is described by it,
  // so a screen reader reads the definition.
  let { id, entry: given, children }: { id?: string; entry?: GlossaryEntry; children?: Snippet } = $props()

  const entry = $derived(given ?? glossaryEntry(id!))
  const uid = $props.id()
  let open = $state(false)
</script>

<!-- No whitespace between the tags: it would show as a space after the term, before punctuation -->
<Popover.Root bind:open>
  <Popover.Trigger
    aria-describedby={open ? `term-${uid}` : undefined}
    openOnHover
    openDelay={150}
    class="cursor-help rounded-sm underline decoration-ink-muted decoration-dotted underline-offset-3 hover:decoration-ink
      focus-visible:outline-2 focus-visible:outline-brand-600"
  >
    {#if children}{@render children()}{:else}{entry.term}{/if}
  </Popover.Trigger><Popover.Portal>
    <Popover.Content
      id="term-{uid}"
      role="tooltip"
      side="bottom"
      align="start"
      sideOffset={4}
      collisionPadding={16}
      trapFocus={false}
      onOpenAutoFocus={(event) => event.preventDefault()}
      class="z-50 w-72 max-w-[calc(100vw-2rem)] rounded-md border border-line bg-surface-raised p-3 text-xs/relaxed
        font-normal text-ink shadow-lg"
    >
      <p class="font-medium">{entry.term}</p>
      <p class="mt-1 text-ink-muted">{entry.definition}</p>
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
