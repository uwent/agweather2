<!-- A page of text (/about, /accessibility, /contact, track 7 step 7.4): content/pages/<id>.md, its Markdown rendered on
     the server with raw HTML off (web.contentpages), so its text is edited without code. -->
<script lang="ts">
  import { longDate } from '@/lib/models/format'
  import type { ContentPageProps } from '@/types'

  let props: ContentPageProps = $props()

  const lead = $derived(props.sections.find((s) => s.id === 'introduction'))
  const body = $derived(props.sections.filter((s) => s.id !== 'introduction'))
</script>

<svelte:head>
  <title>{props.title} · AgWeather</title>
  {#if props.summary}<meta name="description" content={props.summary} />{/if}
</svelte:head>

<article class="space-y-8">
  <header class="max-w-prose space-y-3">
    <h1 class="text-3xl font-semibold">{props.title}</h1>
    {#if props.draft}
      <p class="rounded-md border border-line bg-surface-raised px-3 py-2 text-sm">
        <strong class="font-semibold">Draft.</strong> This page’s text is a draft and may change.
      </p>
    {/if}
  </header>

  <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
    <div class="max-w-prose min-w-0 space-y-8">
      {#if lead}
        <!-- Rendered on the server with raw HTML escaped (web/modelpages.py) -->
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        <div class="prose max-w-none">{@html lead.html}</div>
      {/if}

      {#each body as s (s.id)}
        <section id={s.id} aria-labelledby="{s.id}-title" class="scroll-mt-24 space-y-3">
          <h2 id="{s.id}-title" class="text-2xl font-semibold">{s.title}</h2>
          <!-- eslint-disable-next-line svelte/no-at-html-tags -->
          <div class="prose max-w-none">{@html s.html}</div>
        </section>
      {/each}

      {#if props.updated}
        <p class="text-xs text-ink-muted">{`This page’s text was last changed on ${longDate(props.updated)}.`}</p>
      {/if}
    </div>

    {#if body.length > 1}
      <nav aria-label="On this page" class="hidden lg:block">
        <div class="sticky top-sticky space-y-2 pt-1 text-sm">
          <p class="font-semibold">On this page</p>
          <ul class="space-y-1">
            {#each body as s (s.id)}
              <li><a href="#{s.id}" class="text-ink-muted hover:text-ink hover:underline">{s.title}</a></li>
            {/each}
          </ul>
        </div>
      </nav>
    {/if}
  </div>
</article>
