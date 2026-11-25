<!-- Ported from WISP 3 (adapted): app/frontend/layouts/AppLayout.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import { Link, page } from '@inertiajs/svelte'

  import BrandBar from '@/lib/components/BrandBar.svelte'
  import FlashMessages from '@/lib/components/FlashMessages.svelte'
  import Logo from '@/lib/components/Logo.svelte'
  import SettingsDialog from '@/lib/components/SettingsDialog.svelte'
  import { routes } from '@/lib/routes'
  import StaleBanner from '@/lib/components/StaleBanner.svelte'

  let { children }: { children: Snippet } = $props()

  // The sections (docs/frontend.md, Navigation). Plain paths until lib/routes.ts lands; `also` marks
  // the section current on its pages below it. WISP 3's account menu (bits-ui) comes with sign-in.
  const nav: { label: string; href: string; also?: (string | RegExp)[] }[] = [
    { label: 'Map', href: routes.map() },
    { label: 'Sites', href: routes.sites(), also: ['/sites/'] },
    { label: 'Models', href: routes.models(), also: ['/models/', '/topics/'] },
    { label: 'Tools', href: '/tools', also: ['/tools/', '/calendar'] },
    { label: 'Climate', href: '/climate', also: ['/climate/'] },
    { label: 'Data', href: '/data', also: ['/data/'] },
  ]

  const footerLinks = [
    { label: 'About', href: '/about' },
    { label: 'Methods', href: '/methods' },
    { label: 'Changelog', href: '/changelog' },
    { label: 'API', href: '/api/v2/docs' },
    { label: 'Status', href: '/status' },
    { label: 'Accessibility', href: '/accessibility' },
    { label: 'Contact', href: '/contact' },
  ]

  // On phones the nav scrolls sideways: fade the edge that has more sections past it, and bring the
  // current one into view after each visit
  let navEl = $state<HTMLElement>()
  let moreLeft = $state(false)
  let moreRight = $state(false)
  function measureNav() {
    if (!navEl) return
    moreLeft = navEl.scrollLeft > 1
    moreRight = navEl.scrollLeft + navEl.clientWidth < navEl.scrollWidth - 1
  }
  $effect(() => {
    if (!navEl) return
    const observer = new ResizeObserver(measureNav)
    observer.observe(navEl)
    return () => observer.disconnect()
  })
  $effect(() => {
    void page.url
    const current = navEl?.querySelector<HTMLElement>('[aria-current="page"]')
    if (navEl && current && navEl.scrollWidth > navEl.clientWidth) {
      navEl.scrollLeft = current.offsetLeft - (navEl.clientWidth - current.offsetWidth) / 2
    }
    measureNav()
  })
  const fade = '2.5rem'
  const navMask = $derived(
    moreLeft || moreRight
      ? `linear-gradient(to right, ${moreLeft ? `transparent, black ${fade}` : 'black'}, ${
          moreRight ? `black calc(100% - ${fade}), transparent` : 'black'
        })`
      : undefined,
  )

  // The map pages run edge to edge: their first screen fills the window below the header, sized from --chrome-h
  // (the brand bar's and header's height), and the page scrolls on to their detail and the footer
  const wide = $derived(page.component.startsWith('Map/'))
  let chromeHeight = $state(0)

  const isCurrent = (url: string, also: (string | RegExp)[] = []) =>
    page.url === url ||
    page.url.startsWith(`${url}?`) ||
    also.some((match) => (typeof match === 'string' ? page.url.startsWith(match) : match.test(page.url)))

  let settingsOpen = $state(false)
</script>

<div class="flex min-h-dvh flex-col" style:--chrome-h="{chromeHeight}px">
  <!-- The first stop for keyboard users, past the branding and the nav (WCAG 2.4.1) -->
  <a
    href="#main"
    class="sr-only rounded-md bg-surface-raised px-3 py-2 text-sm font-medium text-brand-600 shadow-lg focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-60"
  >
    Skip to main content
  </a>
  <div bind:clientHeight={chromeHeight}>
    <BrandBar />
    <header class="border-b-4 border-frame bg-surface-raised">
      <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" class="flex text-ink"><Logo /></Link>

        <!-- On phones: logo, search and settings on one row, the nav below -->
        <nav
          bind:this={navEl}
          aria-label="Main"
          class="order-3 -mx-1 flex w-full overflow-x-auto sm:order-2 sm:w-auto sm:gap-1"
          style:mask-image={navMask}
          onscroll={measureNav}
        >
          {#each nav as item (item.label)}
            <Link
              href={item.href}
              class="shrink-0 rounded-md px-2 py-1.5 text-sm font-medium sm:px-3
              {isCurrent(item.href, item.also) ? 'bg-brand-100 text-brand-700' : 'text-ink-muted hover:text-ink'}"
              aria-current={isCurrent(item.href, item.also) ? 'page' : undefined}
            >
              {item.label}
            </Link>
          {/each}
        </nav>

        <div class="order-2 ml-auto flex items-center gap-2 sm:order-3">
          <!-- Place search (PlaceSearch.svelte, from WISP 3's lib/map) goes here -->
          <button
            type="button"
            class="inline-flex size-9 items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-500"
            aria-label="Settings"
            title="Settings"
            aria-haspopup="dialog"
            onclick={() => (settingsOpen = true)}
          >
            <!-- A gear (Lucide's settings icon, ISC license) -->
            <svg
              viewBox="0 0 24 24"
              class="size-5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path
                d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"
              />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  </div>

  <StaleBanner />

  <SettingsDialog bind:open={settingsOpen} />

  {#if wide}
    <main id="main" tabindex="-1" class="flex min-h-0 flex-1 flex-col outline-none">
      <FlashMessages />
      {@render children()}
    </main>
  {:else}
    <main id="main" tabindex="-1" class="mx-auto w-full max-w-6xl flex-1 space-y-4 px-4 py-6 outline-none">
      <FlashMessages />
      {@render children()}
    </main>
  {/if}

  <footer class="border-t-4 border-frame bg-surface-raised text-xs text-ink-muted">
    <div class="mx-auto max-w-6xl space-y-3 px-4 py-5">
      <nav aria-label="Site">
        <ul class="flex flex-wrap gap-x-4 gap-y-1">
          {#each footerLinks as link (link.href)}
            <li><a href={link.href} class="underline hover:text-ink">{link.label}</a></li>
          {/each}
        </ul>
      </nav>
      <p>
        AgWeather is a service of <a href="https://extension.wisc.edu/" class="underline hover:text-ink">
          University of Wisconsin–Madison Extension
        </a>
        and the
        <a href="https://cals.wisc.edu/" class="underline hover:text-ink">
          College of Agricultural and Life Sciences
        </a>. Weather data come from NOAA's National Weather Service, Open-Meteo, the European Centre for Medium-Range
        Weather Forecasts and the Copernicus Climate Change Service, and gridMET.
      </p>
    </div>
  </footer>
</div>
