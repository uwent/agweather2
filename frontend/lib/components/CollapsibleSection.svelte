<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/CollapsibleSection.svelte -->
<script lang="ts">
  import { onMount, type Snippet } from 'svelte'
  import { slide } from 'svelte/transition'

  import { motion } from '../motion'
  import { readStored, writeStored } from '../storage'

  // A page section under an h2 that opens and closes from its heading (a disclosure button with
  // a chevron). storageKey remembers the choice in this browser; without one it opens as `open`
  // says. Arriving at the page with the section's id in the URL's hash, or following a link to it
  // later, opens it. actions: controls beside the heading (shown while open).
  let {
    title,
    id,
    open = $bindable(true),
    storageKey,
    actions,
    children,
  }: {
    title: string
    id?: string
    open?: boolean
    storageKey?: string
    actions?: Snippet
    children: Snippet
  } = $props()

  const uid = $props.id()
  const key = () => storageKey && `agweather-section:${storageKey}`
  const linked = () => !!id && typeof location !== 'undefined' && location.hash === `#${id}`

  // Before the first render, so a section remembered closed doesn't open and then close
  function remembered(): boolean | null {
    const k = key()
    if (!k) return null
    const stored = readStored(k)
    return typeof stored === 'boolean' ? stored : null // Nothing saved or storage blocked: keep the default
  }
  open = linked() || (remembered() ?? open)

  function toggle() {
    open = !open
    const k = key()
    if (!k) return
    writeStored(k, open) // Storage blocked: only this page view remembers
  }

  onMount(() => {
    const reveal = () => {
      if (linked()) open = true
    }
    addEventListener('hashchange', reveal)
    return () => removeEventListener('hashchange', reveal)
  })
</script>

<section {id} class="scroll-mt-4 space-y-3">
  <div class="flex flex-wrap items-center justify-between gap-2">
    <h2 class="text-lg font-medium">
      <button
        type="button"
        class="-ml-1 inline-flex cursor-pointer items-center gap-1.5 rounded-md px-1 text-left hover:text-brand-600 focus-visible:outline-2 focus-visible:outline-brand-600"
        aria-expanded={open}
        aria-controls="{uid}-body"
        data-section-toggle
        onclick={toggle}
      >
        <svg
          viewBox="0 0 20 20"
          class="size-5 shrink-0 text-ink-muted transition-transform motion-reduce:transition-none {open
            ? 'rotate-90'
            : ''}"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M7.2 14.8a.75.75 0 0 1 0-1.06L10.94 10 7.2 6.27a.75.75 0 1 1 1.06-1.06l4.27 4.26a.75.75 0 0 1 0 1.06l-4.27 4.27a.75.75 0 0 1-1.06 0Z"
            clip-rule="evenodd"
          />
        </svg>
        {title}
      </button>
    </h2>
    {#if open && actions}{@render actions()}{/if}
  </div>
  {#if open}
    <div id="{uid}-body" class="space-y-3" transition:slide={{ duration: motion(200) }}>
      {@render children()}
    </div>
  {/if}
</section>
