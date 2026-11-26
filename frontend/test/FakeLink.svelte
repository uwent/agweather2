<!-- Ported from WISP 3: app/frontend/test/FakeLink.svelte -->
<script lang="ts">
  // A stand-in for Inertia's <Link> in component tests: a plain link to its href
  import type { Snippet } from 'svelte'

  let { href, children, ...rest }: { href: string | { url: string }; children?: Snippet; [key: string]: unknown } =
    $props()
</script>

<a href={typeof href === 'string' ? href : href.url} {...rest}>{@render children?.()}</a>
