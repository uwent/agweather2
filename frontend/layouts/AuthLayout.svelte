<!-- Ported from WISP 3 (adapted): app/frontend/layouts/AuthLayout.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'

  import BrandBar from '@/lib/components/BrandBar.svelte'
  import FlashMessages from '@/lib/components/FlashMessages.svelte'
  import Logo from '@/lib/components/Logo.svelte'

  // Sign-in and the other signed-out pages (Auth/…, D122): a centered card under the brand bar
  let { children }: { children: Snippet } = $props()
</script>

<BrandBar />
<main id="main" class="flex min-h-[calc(100dvh-2.25rem)] flex-col items-center justify-center px-4 py-10">
  <div class="w-full max-w-md space-y-6">
    <div class="text-center">
      <a href="/" class="text-ink"><Logo class="text-2xl" /></a>
      <p class="mt-1 text-sm text-ink-muted">Weather and crop models for the Upper Midwest</p>
    </div>

    <FlashMessages />

    <div class="space-y-6 rounded-lg border border-line bg-surface-raised p-6 shadow-sm sm:p-8">
      {@render children()}
    </div>
  </div>
</main>
