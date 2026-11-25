<!-- A model's page (/models/{id}, track 4): generated from its spec and its Markdown page (web.modelpages, D117), so
     nothing here is written by hand about one model. The Markdown comes rendered from the server with raw HTML off. -->
<script lang="ts">
  import { Link } from '@inertiajs/svelte'

  import GlossaryText from '@/lib/components/GlossaryText.svelte'
  import Term from '@/lib/components/Term.svelte'
  import { andList, CHECK_KINDS, longDate, modelMapUrl, monthDay, seasonText, unitLabel } from '@/lib/models/format'
  import OpenAtSite from '@/lib/models/OpenAtSite.svelte'
  import StatusBadge from '@/lib/models/StatusBadge.svelte'
  import { riskColor } from '@/lib/riskLevels'
  import { routes } from '@/lib/routes'
  import { currentUnits } from '@/lib/units'
  import type { ModelPageProps, ModelSection } from '@/types'

  let props: ModelPageProps = $props()

  const system = $derived(currentUnits().system)
  const unit = (symbol: string) => {
    const label = unitLabel(symbol, system)
    return label ? ` (${label})` : ''
  }

  // The Markdown page's sections, each placed beside the generated section it belongs with; any others follow
  // "How it works"
  const PLACED = ['introduction', 'what-it-predicts', 'how-to-read-it', 'how-it-works', 'validation-and-caveats']
  const section = (id: string): ModelSection | undefined => props.sections.find((s) => s.id === id)
  const extra = $derived(props.sections.filter((s) => !PLACED.includes(s.id)))

  const contents = $derived([
    { id: 'what-it-predicts', title: 'What it predicts' },
    { id: 'how-to-read-it', title: 'How to read it' },
    { id: 'where-and-when', title: 'Where and when it applies' },
    ...(section('how-it-works') ? [{ id: 'how-it-works', title: 'How it works' }] : []),
    ...extra.map((s) => ({ id: s.id, title: s.title })),
    { id: 'inputs', title: 'The weather it uses' },
    { id: 'checks', title: 'How it was checked' },
    { id: 'versions', title: 'Version and changes' },
    { id: 'sources', title: 'Sources' },
    ...(props.acknowledgments ? [{ id: 'acknowledgments', title: 'Acknowledgments' }] : []),
  ])

  const trainedPlaces = $derived(props.trained ? [...props.trained.states, ...props.trained.counties] : [])
  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>{props.name} · AgWeather</title>
  <meta name="description" content={props.summary} />
</svelte:head>

{#snippet markdown(s: ModelSection | undefined)}
  {#if s}
    <!-- Rendered on the server with raw HTML escaped (web/modelpages.py) -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="prose max-w-none">{@html s.html}</div>
  {/if}
{/snippet}

<article class="space-y-8">
  <header class="space-y-3">
    <p class="text-sm">
      <Link href={routes.models()} class={link}>Models</Link>
      <span class="text-ink-muted">{` / ${props.group_name}`}</span>
    </p>
    <div class="flex flex-wrap items-center gap-3">
      <h1 class="text-3xl font-semibold">{props.name}</h1>
      <StatusBadge status={props.model_status} />
    </div>
    {#if props.crops.length}
      <p class="text-sm text-ink-muted">{`For ${andList(props.crops.map((c) => c.name.toLowerCase()))}`}</p>
    {/if}
    <GlossaryText paragraphs={[props.summary]} class="max-w-prose text-lg" />
    {#if props.model_status === 'beta'}
      <p class="max-w-prose rounded-md border border-line bg-surface-raised px-3 py-2 text-sm">
        <strong class="font-semibold">Beta.</strong> We are still checking this model, so its results may change. Use it
        alongside your own scouting{props.draft ? ', and note that this page’s text is a draft' : ''}.
      </p>
    {/if}
    <div class="flex flex-wrap gap-3 pt-1">
      {#if props.map_layer}
        <a
          href={modelMapUrl(props.map_layer)}
          class="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white
            hover:bg-brand-700 dark:text-surface"
        >
          See the map
        </a>
      {/if}
      <a
        href="#open-at-a-site"
        class="inline-flex items-center rounded-md border border-line bg-surface-raised px-4 py-2 text-sm font-medium
          text-ink hover:bg-surface"
      >
        Open at a site
      </a>
    </div>
  </header>

  <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
    <div class="max-w-prose min-w-0 space-y-8">
      <section id="what-it-predicts" aria-labelledby="what-it-predicts-title" class="scroll-mt-24 space-y-3">
        <h2 id="what-it-predicts-title" class="text-2xl font-semibold">What it predicts</h2>
        {@render markdown(section('introduction'))}
        {#if section('what-it-predicts')}
          {@render markdown(section('what-it-predicts'))}
        {:else}
          <p>{props.summary}</p>
        {/if}
      </section>

      <section id="how-to-read-it" aria-labelledby="how-to-read-it-title" class="scroll-mt-24 space-y-3">
        <h2 id="how-to-read-it-title" class="text-2xl font-semibold">How to read it</h2>
        {#if props.risk}
          <h3 class="font-semibold">Risk levels</h3>
          <ul class="flex flex-wrap gap-x-4 gap-y-2" aria-label="Risk levels, lowest first">
            {#each props.risk.levels as level, k (level)}
              <li class="flex items-center gap-2 text-sm">
                <span
                  class="size-3.5 shrink-0 rounded-full border border-line"
                  style:background-color={riskColor(k, props.risk.levels.length)}
                  aria-hidden="true"
                ></span>
                {level}
              </li>
            {/each}
          </ul>
          <GlossaryText paragraphs={[`How the levels are set: ${props.risk.criteria}`]} class="text-sm" />
        {:else}
          <p>This model has no risk levels: it estimates dates and stages rather than a risk.</p>
        {/if}
        {@render markdown(section('how-to-read-it'))}
        {#if props.outputs.length}
          <h3 class="font-semibold">What it shows</h3>
          <ul class="list-disc space-y-1 pl-5 text-sm">
            {#each props.outputs as output (output.label)}
              <li>
                {output.label}{unit(output.unit)}{output.description ? `: ${output.description}` : ''}
              </li>
            {/each}
          </ul>
        {/if}
      </section>

      <section id="where-and-when" aria-labelledby="where-and-when-title" class="scroll-mt-24 space-y-3">
        <h2 id="where-and-when-title" class="text-2xl font-semibold">Where and when it applies</h2>
        <dl class="space-y-3">
          <div>
            <dt class="font-semibold">Where</dt>
            <dd>
              {#if props.region.length}
                {`${andList(props.region.map((r) => r.name))}.`}
              {:else}
                Anywhere AgWeather has weather data.
              {/if}
            </dd>
          </div>
          <div>
            <dt class="font-semibold">When</dt>
            <dd>
              {seasonText(props.season)}
              {#if props.seasonal_appears}
                {` It makes one map a season, first shown on ${monthDay(props.seasonal_appears)}.`}
              {/if}
            </dd>
          </div>
          {#if props.susceptible}
            <div>
              <dt class="font-semibold">Crop stages</dt>
              <dd>
                {`Risk is shown while the crop is from ${props.susceptible.first} to ${props.susceptible.last}, as `}<Link
                  href={routes.model({ model_id: props.susceptible.crop_model.id })}
                  class={link}
                >
                  {props.susceptible.crop_model.name}
                </Link>{` estimates them, or from the planting date you give. Source: ${props.susceptible.source}.`}
                {#if props.susceptible.note}{` ${props.susceptible.note}`}{/if}
              </dd>
            </div>
          {/if}
          {#if props.biofix}
            <div>
              <dt class="font-semibold">Start date</dt>
              <dd>
                {#if props.biofix.fixed}
                  {`The model counts from ${monthDay(props.biofix.default)} each year.`}
                {:else}
                  The model’s <Term id="biofix">biofix</Term>{`: ${props.biofix.label}.`}
                  {#if props.biofix.stage_model}
                    {`Without a date of yours, it starts when `}<Link
                      href={routes.model({ model_id: props.biofix.stage_model.id })}
                      class={link}
                    >
                      {props.biofix.stage_model.name}
                    </Link>{` estimates stage ${props.biofix.stage}.`}
                  {:else}
                    {` Without a date of yours, it starts on ${monthDay(props.biofix.default)}.`}
                  {/if}
                {/if}
              </dd>
            </div>
          {/if}
          {#if props.trained}
            <div>
              <dt class="font-semibold">Where its data came from</dt>
              <dd class="space-y-2">
                <p>
                  {`${props.name} was fitted to ${props.trained.description}, ${props.trained.years[0]}–${props.trained.years[1]}.`}
                  {#if trainedPlaces.length}{` That area is ${andList(trainedPlaces)}.`}{/if}
                </p>
                <p>
                  AgWeather runs it elsewhere too, but outside that area its timing is less certain, and the map and
                  site pages say so.{props.trained.calendar_curve
                    ? ' Its calendar curve describes a typical year where the data came from; degree days follow the weather at your location.'
                    : ''}
                </p>
              </dd>
            </div>
          {/if}
        </dl>
      </section>

      {#if section('how-it-works')}
        <section id="how-it-works" aria-labelledby="how-it-works-title" class="scroll-mt-24 space-y-3">
          <h2 id="how-it-works-title" class="text-2xl font-semibold">How it works</h2>
          {@render markdown(section('how-it-works'))}
        </section>
      {/if}

      {#each extra as s (s.id)}
        <section id={s.id} aria-labelledby="{s.id}-title" class="scroll-mt-24 space-y-3">
          <h2 id="{s.id}-title" class="text-2xl font-semibold">{s.title}</h2>
          {@render markdown(s)}
        </section>
      {/each}

      <section id="inputs" aria-labelledby="inputs-title" class="scroll-mt-24 space-y-3">
        <h2 id="inputs-title" class="text-2xl font-semibold">The weather it uses</h2>
        <p>
          {props.inputs.length
            ? 'The model reads these daily values from AgWeather’s weather data for each location.'
            : 'The model reads no weather: it needs only the date.'}
        </p>
        <ul class="space-y-2">
          {#each props.inputs as input (input.name)}
            <li>
              <span class="font-medium">{input.label}</span>{unit(input.unit)}{input.description
                ? `, ${input.description}`
                : ''}
              {#if input.definition}<span class="block text-sm text-ink-muted">{input.definition}</span>{/if}
            </li>
          {/each}
        </ul>
        <!-- TODO (track 4): link each input to its entry on the methods page once /methods is built -->
      </section>

      <section id="checks" aria-labelledby="checks-title" class="scroll-mt-24 space-y-3">
        <h2 id="checks-title" class="text-2xl font-semibold">How it was checked</h2>
        {#if props.checks.length}
          <ul class="space-y-4">
            {#each props.checks as check (check.report_url)}
              <li class="space-y-1">
                <h3 class="font-semibold">{CHECK_KINDS[check.kind] ?? check.kind}</h3>
                <p class="text-sm text-ink-muted">{check.against}</p>
                <p>{check.result}</p>
                <p class="text-sm"><a href={check.report_url} class={link}>The details of this check</a></p>
              </li>
            {/each}
          </ul>
        {:else}
          <p>This model hasn’t been checked yet.</p>
        {/if}
        {#if section('validation-and-caveats')}
          <h3 class="font-semibold">Limits</h3>
          {@render markdown(section('validation-and-caveats'))}
        {/if}
        <p class="text-sm">
          <a href={props.report_url} class={link}>Read the full validation report</a>
          <span class="text-ink-muted"> (on GitHub, with the data and code behind each check)</span>
        </p>
      </section>

      <section id="versions" aria-labelledby="versions-title" class="scroll-mt-24 space-y-3">
        <h2 id="versions-title" class="text-2xl font-semibold">Version and changes</h2>
        <p>{`Version ${props.version}, ${props.model_status === 'beta' ? 'beta' : props.model_status}.`}</p>
        {#if props.changelog.length}
          <ul class="space-y-2">
            {#each props.changelog as change (change.version)}
              <li>
                <span class="font-medium">{`Version ${change.version}`}</span><span class="text-sm text-ink-muted">
                  {`, ${longDate(change.date)}`}
                </span>
                <span class="block">{change.note}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </section>

      <section id="sources" aria-labelledby="sources-title" class="scroll-mt-24 space-y-3">
        <h2 id="sources-title" class="text-2xl font-semibold">Sources</h2>
        {#if props.sources.length}
          <ol class="list-decimal space-y-2 pl-5">
            {#each props.sources as source (source.key)}
              <li id="source-{source.key}" class="scroll-mt-24">
                {source.text}
                {#if source.url}<a href={source.url} class={link}>Read it</a>{/if}
              </li>
            {/each}
          </ol>
        {/if}
        <ul class="space-y-2">
          {#each props.citations as citation (citation.text)}
            <li>
              {citation.text}
              {#if citation.doi && citation.url}
                <a href={citation.url} class="break-all {link}">{`doi:${citation.doi}`}</a>
              {:else if citation.url}
                <a href={citation.url} class={link}>Read it</a>
              {/if}
            </li>
          {/each}
        </ul>
      </section>

      {#if props.acknowledgments}
        <section id="acknowledgments" aria-labelledby="acknowledgments-title" class="scroll-mt-24 space-y-3">
          <h2 id="acknowledgments-title" class="text-2xl font-semibold">Acknowledgments</h2>
          <!-- Rendered on the server with raw HTML escaped (web/modelpages.py) -->
          <!-- eslint-disable-next-line svelte/no-at-html-tags -->
          <div class="prose max-w-none">{@html props.acknowledgments}</div>
        </section>
      {/if}

      <section
        id="open-at-a-site"
        aria-labelledby="open-at-a-site-title"
        class="scroll-mt-24 space-y-3 rounded-lg border border-line bg-surface-raised p-4"
      >
        <h2 id="open-at-a-site-title" class="text-xl font-semibold">Open at a site</h2>
        <p class="text-sm">See this model’s results through the season and the forecast for one location.</p>
        <OpenAtSite modelId={props.id} feed={!!props.risk} />
      </section>

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
