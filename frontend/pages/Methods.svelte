<!-- How the data is made (/methods, track 4): generated from the code and data (web.methodspage, D92), the same as
     the API's /methods and /variables, so it changes when the code does. Nothing here states a method by hand: the
     sources, corrections, scores, variables, the grid and the day come from the props. -->
<script lang="ts">
  import Term from '@/lib/components/Term.svelte'
  import { clockHour, dateSpan, kmText, ofKind, ROLES, scoreText, variableAnchor } from '@/lib/methods'
  import { longDate, unitLabel } from '@/lib/models/format'
  import { currentUnits } from '@/lib/units'
  import type { MethodsProps, MethodsVariable } from '@/types'

  let props: MethodsProps = $props()

  const system = $derived(currentUnits().system)
  const g = $derived(props.grid)

  const byName = $derived(new Map(props.variables.map((v) => [`${v.kind}:${v.name}`, v])))
  const sourceNames = $derived(new Map(props.sources.map((s) => [s.source, s.name])))
  const correctionTitles = $derived(new Map(props.corrections.map((c) => [c.id, c.title])))
  const roles = $derived(
    ROLES.map((r) => ({ ...r, sources: props.sources.filter((s) => s.role === r.id) })).filter((r) => r.sources.length),
  )
  const kinds = $derived(
    (
      [
        {
          id: 'hourly',
          name: 'Hourly values',
          about: 'Each hour’s value, as the sources give it or computed from them.',
        },
        {
          id: 'daily',
          name: 'Daily values',
          about: 'Each day’s values, made from the hours of the day. Models read these.',
        },
        {
          id: 'cumulative',
          name: 'Running totals',
          about: 'Totals from the start of the year (or of the chill season) to each day.',
        },
      ] as const
    ).map((k) => ({ ...k, variables: ofKind(props.variables, k.id) })),
  )

  /** A variable as a source or correction names it: an hourly one, else a daily one (the normals') */
  function named(name: string): MethodsVariable | undefined {
    return byName.get(`hourly:${name}`) ?? byName.get(`daily:${name}`)
  }

  const unit = (symbol: string) => {
    const label = unitLabel(symbol, system)
    return label ? ` (${label})` : ''
  }

  const STATISTICS: Record<string, string> = { min: 'lowest', max: 'highest', mean: 'mean', sum: 'total' }
  function madeFrom(v: MethodsVariable): string {
    const hourly = v.hourly_sources.map((n) => byName.get(`hourly:${n}`)?.long_name ?? n)
    if (v.statistic && hourly.length === 1)
      return `The day’s ${STATISTICS[v.statistic] ?? v.statistic} of: ${hourly[0]}.`
    if (v.computed_from.length) {
      const from = v.computed_from.map((n) => byName.get(`${v.kind}:${n}`)?.long_name ?? n)
      return `Computed from: ${from.join('; ')}.`
    }
    if (hourly.length) return `Made from the day’s hours of: ${hourly.join('; ')}.`
    return ''
  }

  function gapText(v: MethodsVariable): string {
    if (v.gap_fill === 'interpolate')
      return `A model that reads it estimates a missing day by a straight line between the days on either side, across gaps of up to ${g.interpolate_days} days.`
    if (v.gap_fill === 'zero')
      return 'A model that reads it counts a missing day as zero and reports how many days were missing.'
    return ''
  }

  const contents = [
    { id: 'grid', title: 'The grid and the day' },
    { id: 'sources', title: 'Where the weather comes from' },
    { id: 'corrections', title: 'Our corrections' },
    { id: 'gaps', title: 'Missing data' },
    { id: 'variables', title: 'The variables' },
  ]

  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>Methods · AgWeather</title>
  <meta
    name="description"
    content="Where AgWeather's weather data come from, how we correct them, how days and missing data are handled, and what each variable means."
  />
</svelte:head>

<article class="space-y-8">
  <header class="max-w-prose space-y-3">
    <h1 class="text-3xl font-semibold">Methods</h1>
    <p class="text-lg">
      This page describes where AgWeather’s weather data come from, how we correct them, and what each value means. It
      is made from the code that does the work, so it changes when the code does.
    </p>
    <p class="text-sm text-ink-muted">
      The same information is available from the API at <a href={props.api_methods_url} class={link}>
        {props.api_methods_url}
      </a>. The technical reports linked below are on GitHub, with the data and code behind each check.
    </p>
  </header>

  <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
    <div class="max-w-prose min-w-0 space-y-10">
      <section id="grid" aria-labelledby="grid-title" class="scroll-mt-24 space-y-3">
        <h2 id="grid-title" class="text-2xl font-semibold">The grid and the day</h2>
        <p>
          {`AgWeather keeps its weather on a grid of cells about ${kmText(g.cell_km)} on a side: the grid NOAA uses for its national forecasts (${g.name}). A map shows one value for each cell, and a location takes the values of the cell it is in, so a value describes the cell as a whole rather than one field.`}
        </p>
        <p>
          {`Every day runs from midnight to midnight ${g.day_zone} (${g.day_zone_abbreviation}) all year, ${String(g.day_start_utc).padStart(2, '0')}:00 to ${String(g.day_start_utc).padStart(2, '0')}:00 UTC, the same hours in every cell, so neighboring cells on a map cover the same day. ${g.day_zone_abbreviation === 'CST' ? `In summer that is ${clockHour(1)} to ${clockHour(1)} Central Daylight Time. ` : ''}For a location’s weather or models, you can ask the API for days on the location’s own clock instead.`}
        </p>
        <p>
          {`Models that count hours at night take night as ${clockHour(g.evening_hour)} to ${clockHour(g.evening_hour + 12)} ${g.day_zone_abbreviation}, and those that need a full day starting in the evening take ${clockHour(g.evening_hour)} the evening before to ${clockHour(g.evening_hour)}. The overnight low runs from ${clockHour(g.overnight_hour)} the day before to ${clockHour(g.overnight_hour)}.`}
        </p>
      </section>

      <section id="sources" aria-labelledby="sources-title" class="scroll-mt-24 space-y-6">
        <h2 id="sources-title" class="text-2xl font-semibold">Where the weather comes from</h2>
        {#each roles as role (role.id)}
          <section id="sources-{role.id}" aria-labelledby="sources-{role.id}-title" class="scroll-mt-24 space-y-3">
            <h3 id="sources-{role.id}-title" class="text-xl font-semibold">{role.name}</h3>
            <p class="text-ink-muted">{role.about}</p>
            <ul class="space-y-4">
              {#each role.sources as source, k (`${source.source}-${k}`)}
                <li class="space-y-1 rounded-lg border border-line bg-surface-raised p-4">
                  <p class="font-semibold"><a href={source.url} class={link}>{source.name}</a></p>
                  <p>{source.description}</p>
                  {#if dateSpan(source.first, source.last)}
                    <p class="text-sm font-medium">{dateSpan(source.first, source.last)}</p>
                  {/if}
                  <p class="text-sm text-ink-muted">
                    {'For: '}{#each source.variables as name, i (name)}{i ? ', ' : ''}<a
                        href="#{variableAnchor(name, named(name)?.kind)}"
                        class="underline hover:text-ink"
                      >
                        {named(name)?.long_name ?? name}
                      </a>{/each}.
                  </p>
                </li>
              {/each}
            </ul>
          </section>
        {/each}
      </section>

      <section id="corrections" aria-labelledby="corrections-title" class="scroll-mt-24 space-y-6">
        <h2 id="corrections-title" class="text-2xl font-semibold">Our corrections</h2>
        <p>
          Where a source reads consistently high or low against measurements, we correct it. Where we give scores, we
          fitted the correction on one period and tested it on another it hadn’t seen.
        </p>
        {#each props.corrections as c (c.id)}
          <section id="correction-{c.id}" aria-labelledby="correction-{c.id}-title" class="scroll-mt-24 space-y-2">
            <h3 id="correction-{c.id}-title" class="text-xl font-semibold">{c.title}</h3>
            <p>{c.summary}</p>
            {#if c.scores.length}
              <h4 class="font-semibold">How much it helps</h4>
              <ul class="space-y-2 text-sm">
                {#each c.scores as s (s.measure)}
                  <li>
                    <span class="font-medium">{s.measure}</span>:
                    {` ${scoreText(s.before, s.unit, system)} before the correction, ${scoreText(s.after, s.unit, system)} after.`}
                    <span class="block text-ink-muted">{`Tested on ${s.tested}.`}</span>
                  </li>
                {/each}
              </ul>
            {/if}
            <p class="text-sm text-ink-muted">
              {`Version ${c.version}${c.fitted ? `, fitted ${longDate(c.fitted)}` : ''}. `}
              {#each c.evidence as url, i (url)}{i ? ' · ' : ''}<a href={url} class={link}>
                  {c.evidence.length > 1 ? `Technical report ${i + 1}` : 'Technical report'}
                </a>{/each}
            </p>
          </section>
        {/each}
      </section>

      <section id="gaps" aria-labelledby="gaps-title" class="scroll-mt-24 space-y-3">
        <h2 id="gaps-title" class="text-2xl font-semibold">Missing data</h2>
        <p>
          When a source has no value for an hour or a day, AgWeather shows it as missing on maps, in charts and in
          downloads. We never show a missing value as zero.
        </p>
        <p>
          {`A model needs every day, so before it runs, a missing day of a value such as temperature or humidity is estimated by a straight line between the days on either side, across gaps of up to ${g.interpolate_days} days. Precipitation is never estimated: a missing day counts as no rain. Each model reports how many of its days were estimated or missing.`}
        </p>
        <p>
          {`Running totals, such as `}<Term id="growing_degree_days">
            degree days
          </Term>{` since January 1, bridge a gap of up to ${g.bridge_days} days the same way and count the days they estimated, so a total can say “includes 2 estimated days”. A longer gap leaves those days out of the total and counts them as missing.`}
        </p>
      </section>

      <section id="variables" aria-labelledby="variables-title" class="scroll-mt-24 space-y-6">
        <h2 id="variables-title" class="text-2xl font-semibold">The variables</h2>
        <p>
          Every value AgWeather stores or computes, with the unit it is shown in. Your settings choose US or metric
          units.
        </p>
        {#each kinds as kind (kind.id)}
          <section id="variables-{kind.id}" aria-labelledby="variables-{kind.id}-title" class="scroll-mt-24 space-y-3">
            <h3 id="variables-{kind.id}-title" class="text-xl font-semibold">{kind.name}</h3>
            <p class="text-ink-muted">{kind.about}</p>
            <dl class="divide-y divide-line border-y border-line">
              {#each kind.variables as v (v.name)}
                <div id={variableAnchor(v.name, v.kind)} class="scroll-mt-24 space-y-1 py-3">
                  <dt class="font-medium">{v.long_name}{unit(v.unit)}</dt>
                  <dd class="space-y-1 text-sm">
                    {#if v.notes}<p>{v.notes}</p>{/if}
                    {#if madeFrom(v)}<p class="text-ink-muted">{madeFrom(v)}</p>{/if}
                    {#if v.sources.length}
                      <p class="text-ink-muted">
                        {`Source: ${v.sources.map((s) => sourceNames.get(s) ?? s).join('; ')}.`}
                      </p>
                    {/if}
                    {#if v.corrections.length}
                      <p class="text-ink-muted">
                        {'Corrected: '}{#each v.corrections as id, i (id)}{i ? '; ' : ''}<a
                            href="#correction-{id}"
                            class="underline hover:text-ink"
                          >
                            {correctionTitles.get(id) ?? id}
                          </a>{/each}.
                      </p>
                    {/if}
                    {#if gapText(v)}<p class="text-ink-muted">{gapText(v)}</p>{/if}
                    <p class="text-xs text-ink-muted">{`In the API: ${v.name}`}</p>
                  </dd>
                </div>
              {/each}
            </dl>
          </section>
        {/each}
      </section>
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
