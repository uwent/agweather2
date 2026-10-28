<script lang="ts">
  import type { Snippet } from 'svelte'
  import { Link, page } from '@inertiajs/svelte'

  import BrandBar from '@/lib/components/BrandBar.svelte'
  import FlashMessages from '@/lib/components/FlashMessages.svelte'
  import Logo from '@/lib/components/Logo.svelte'

  let { children }: { children: Snippet } = $props()

  // Inertia pages; the API docs are a plain link (a Django Ninja page, not Inertia)
  const nav = [{ label: 'Home', href: '/' }]

  const isCurrent = (href: string) => page.url === href || page.url.startsWith(`${href}?`)
</script>

<div class="flex min-h-dvh flex-col">
  <!-- The first stop for keyboard users, past the branding and the nav (WCAG 2.4.1) -->
  <a
    href="#main"
    class="bg-surface-raised text-brand-600 sr-only rounded-md px-3 py-2 text-sm font-medium shadow-lg focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-60"
    >Skip to main content</a
  >
  <BrandBar />
  <header class="border-frame bg-surface-raised border-b-4">
    <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
      <Link href="/" class="text-ink flex"><Logo /></Link>

      <nav aria-label="Main" class="-mx-1 flex gap-1 overflow-x-auto">
        {#each nav as item (item.href)}
          <Link
            href={item.href}
            class="shrink-0 rounded-md px-3 py-1.5 text-sm font-medium
              {isCurrent(item.href) ? 'bg-brand-100 text-brand-700' : 'text-ink-muted hover:text-ink'}"
            aria-current={isCurrent(item.href) ? 'page' : undefined}
          >
            {item.label}
          </Link>
        {/each}
        <a href="/api/v2/docs" class="text-ink-muted hover:text-ink shrink-0 rounded-md px-3 py-1.5 text-sm font-medium"
          >API</a
        >
      </nav>
    </div>
  </header>

  <main id="main" tabindex="-1" class="mx-auto w-full max-w-6xl flex-1 space-y-4 px-4 py-6 outline-none">
    <FlashMessages />
    {@render children()}
  </main>

  <footer class="border-frame bg-surface-raised text-ink-muted space-y-1 border-t-4 px-4 py-4 text-center text-xs">
    <p>AgWeather</p>
    <p>
      Developed by the <a href="https://cals.wisc.edu/" class="hover:text-ink underline"
        >College of Agricultural and Life Sciences</a
      > at the University of Wisconsin–Madison.
    </p>
  </footer>
</div>
