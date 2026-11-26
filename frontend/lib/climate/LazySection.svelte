<script lang="ts">
  import type { Snippet } from 'svelte'

  // A climate section that starts its requests only as it scrolls into view (track 6.2): its heading shows at
  // once, its body (`children`, which loads when it mounts) once the section comes within a screen of the
  // window. Without IntersectionObserver (a test, an old browser) the body shows at once.
  let {
    title,
    id,
    children,
  }: {
    title: string
    /** The heading's anchor */
    id: string
    children: Snippet
  } = $props()

  let section: HTMLElement | undefined = $state()
  let seen = $state(false)
  $effect(() => {
    if (!section || seen) return
    if (typeof IntersectionObserver === 'undefined') {
      seen = true
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          seen = true
          observer.disconnect()
        }
      },
      { rootMargin: '0px 0px 50% 0px' },
    )
    observer.observe(section)
    return () => observer.disconnect()
  })
</script>

<section bind:this={section} class="space-y-3" aria-labelledby={id}>
  <h2 {id} class="scroll-mt-4 text-lg font-semibold">{title}</h2>
  {#if seen}
    {@render children()}
  {:else}
    <div class="h-48 rounded-lg bg-surface-raised" aria-hidden="true"></div>
  {/if}
</section>
