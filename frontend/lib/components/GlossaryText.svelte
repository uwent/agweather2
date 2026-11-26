<!-- Ported from WISP 3: app/frontend/lib/components/GlossaryText.svelte -->
<script lang="ts">
  import { markTerms } from '@/lib/glossary'

  import Term from './Term.svelte'

  // Paragraphs of plain text with their glossary terms marked, each the first time it appears in
  // the block
  let { paragraphs, class: className = '' }: { paragraphs: string[]; class?: string } = $props()

  const marked = $derived.by(() => {
    const seen = new Set<string>()
    return paragraphs.map((text) => markTerms(text, seen))
  })
</script>

{#each marked as segments, p (p)}
  <p class={className}>
    {#each segments as segment, i (i)}{#if segment.entry}<Term entry={segment.entry}>
          {segment.text}
        </Term>{:else}{segment.text}{/if}{/each}
  </p>
{/each}
