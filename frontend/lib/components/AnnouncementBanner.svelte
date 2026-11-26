<!-- The changelog's announcements as banners on every page (beside StaleBanner in AppLayout), each until its
     `banner_until`, closed per entry in this browser (lib/announcements) -->
<script lang="ts">
  import { page } from '@inertiajs/svelte'

  import { dismiss, dismissedIds, shown } from '@/lib/announcements'
  import { routes } from '@/lib/routes'

  let dismissed = $state<number[]>(dismissedIds())
  const all = $derived(page.props.announcements ?? [])
  const visible = $derived(shown(all, dismissed, new Date()))

  function close(id: number) {
    dismissed = dismiss(
      id,
      all.map((a) => a.id),
    )
  }
</script>

{#if visible.length}
  <div class="border-b border-line bg-surface-raised text-ink">
    <div class="mx-auto max-w-6xl space-y-2 px-4 py-2">
      {#each visible as entry (entry.id)}
        <section
          aria-label={entry.kind === 'outage' ? 'Outage notice' : 'Announcement'}
          class="flex items-start gap-3 border-l-4 py-1 pl-3 text-sm {entry.kind === 'outage'
            ? 'border-danger'
            : 'border-brand-500'}"
        >
          <div class="min-w-0 flex-1 space-y-1">
            <p class="font-semibold">
              <a href={`${routes.changelog()}#entry-${entry.id}`} class="underline hover:text-brand-700">
                {entry.title}
              </a>
            </p>
            {#if entry.body_html}
              <!-- Rendered on the server with raw HTML escaped (updates/render.py) -->
              <!-- eslint-disable-next-line svelte/no-at-html-tags -->
              <div class="prose prose-sm">{@html entry.body_html}</div>
            {/if}
          </div>
          <button
            type="button"
            class="inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-muted hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-500"
            aria-label={`Dismiss “${entry.title}”`}
            title="Dismiss"
            onclick={() => close(entry.id)}
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
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </section>
      {/each}
    </div>
  </div>
{/if}
