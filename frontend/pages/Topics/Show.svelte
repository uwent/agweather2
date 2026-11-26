<!-- A topic page (/topics/{id}, track 4): a pest, disease or crop from content/topics/<id>.md, its Markdown rendered
     on the server with raw HTML off (web.topicpages, D117), and the models that name it. Nothing here is written by
     hand about one topic. -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import { andList, longDate, modelMapUrl } from '@/lib/models/format'
  import StatusBadge from '@/lib/models/StatusBadge.svelte'
  import { routes } from '@/lib/routes'
  import type { ModelSection, TopicPageProps } from '@/types'

  let props: TopicPageProps = $props()

  // The section the generated list of models joins: the Markdown's own, or one of ours at the end
  const MODELS = 'agweathers-models'
  const lead = $derived(props.sections.find((s) => s.id === 'introduction'))
  const body = $derived(props.sections.filter((s) => s.id !== 'introduction'))
  const modelsSection = $derived(props.sections.find((s) => s.id === MODELS))

  const contents = $derived([
    ...body.map((s) => ({ id: s.id, title: s.title })),
    ...(!modelsSection && props.models.length ? [{ id: MODELS, title: 'AgWeather’s models' }] : []),
    ...(props.sources.length ? [{ id: 'sources', title: 'Sources' }] : []),
  ])

  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>{props.title} · AgWeather</title>
  {#if props.summary}<meta name="description" content={props.summary} />{/if}
</svelte:head>

{#snippet markdown(s: ModelSection | undefined)}
  {#if s}
    <!-- Rendered on the server with raw HTML escaped (web/modelpages.py) -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="prose max-w-none">{@html s.html}</div>
  {/if}
{/snippet}

{#snippet models()}
  <ul class="space-y-3" aria-label="Models for {props.title}">
    {#each props.models as model (model.id)}
      <li class="rounded-lg border border-line bg-surface-raised p-3">
        <div class="flex flex-wrap items-center gap-x-2">
          <Link href={routes.model({ model_id: model.id })} class="font-medium {link}">{model.name}</Link>
          <StatusBadge status={model.model_status} />
        </div>
        <p class="text-sm text-ink-muted">{model.summary}</p>
        {#if model.map_layer}
          <p class="mt-1 text-sm">
            <a href={modelMapUrl(model.map_layer)} class={link} aria-label="See the map of {model.name}">See the map</a>
          </p>
        {/if}
      </li>
    {/each}
  </ul>
{/snippet}

<article class="space-y-8">
  <header class="grid gap-6 md:grid-cols-[minmax(0,1fr)_20rem]">
    <div class="max-w-prose space-y-3">
      <p class="text-sm">
        <Link href={routes.models()} class={link}>Models</Link>
        <span class="text-ink-muted">{' / '}</span>
        <Link href={routes.topics()} class={link}>Pests and diseases</Link>
      </p>
      <h1 class="text-3xl font-semibold">{props.title}</h1>
      {#if props.scientific_name && props.kind !== 'crop'}
        <p class="text-ink-muted"><i>{props.scientific_name}</i>{` · ${props.kind_name}`}</p>
      {:else}
        <p class="text-ink-muted">{props.kind_name}</p>
      {/if}
      {#if props.crops.length && props.kind !== 'crop'}
        <p class="text-sm text-ink-muted">{`On ${andList(props.crops.map((c) => c.name.toLowerCase()))}`}</p>
      {/if}
      {#if props.summary}<p class="text-lg">{props.summary}</p>{/if}
      {#if props.draft}
        <p class="rounded-md border border-line bg-surface-raised px-3 py-2 text-sm">
          <strong class="font-semibold">Draft.</strong> This page’s text is a draft and may change. Check management choices
          against the sources below or with your local extension office.
        </p>
      {/if}
    </div>
    {#if props.image_url}
      <figure class="space-y-2 md:pt-8">
        <img
          src={props.image_url}
          alt={props.image_alt}
          class="w-full rounded-lg border border-line object-cover"
          loading="lazy"
        />
        <figcaption class="text-xs text-ink-muted">{props.image_credit}</figcaption>
      </figure>
    {/if}
  </header>

  <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
    <div class="max-w-prose min-w-0 space-y-8">
      {@render markdown(lead)}

      {#each body as s (s.id)}
        <section id={s.id} aria-labelledby="{s.id}-title" class="scroll-mt-24 space-y-3">
          <h2 id="{s.id}-title" class="text-2xl font-semibold">{s.title}</h2>
          {@render markdown(s)}
          {#if s.id === MODELS && props.models.length}{@render models()}{/if}
        </section>
      {/each}

      {#if !modelsSection && props.models.length}
        <section id={MODELS} aria-labelledby="{MODELS}-title" class="scroll-mt-24 space-y-3">
          <h2 id="{MODELS}-title" class="text-2xl font-semibold">AgWeather’s models</h2>
          {@render models()}
        </section>
      {/if}

      {#if props.sources.length}
        <section id="sources" aria-labelledby="sources-title" class="scroll-mt-24 space-y-3">
          <h2 id="sources-title" class="text-2xl font-semibold">Sources</h2>
          <ol class="list-decimal space-y-2 pl-5">
            {#each props.sources as source (source.key)}
              <li id="source-{source.key}" class="scroll-mt-24">
                {source.text}
                {#if source.url}<a href={source.url} class={link}>Read it</a>{/if}
              </li>
            {/each}
          </ol>
        </section>
      {/if}

      {#if props.updated}
        <p class="text-xs text-ink-muted">{`This page’s text was last changed on ${longDate(props.updated)}.`}</p>
      {/if}
    </div>

    <nav aria-label="On this page" class="hidden lg:block">
      <div class="sticky top-sticky space-y-2 pt-1 text-sm">
        <p class="font-semibold">On this page</p>
        <ul class="space-y-1">
          {#each contents as item (item.id)}
            <li><a href="#{item.id}" class="text-ink-muted hover:text-ink hover:underline">{item.title}</a></li>
          {/each}
        </ul>
      </div>
    </nav>
  </div>
</article>
