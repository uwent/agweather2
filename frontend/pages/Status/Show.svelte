<!-- Data status (/status, Phase 7 step 7.2): /api/v2/status in words. The server sends the answer to show first
     (web.statuspage); the page asks again every minute while it's visible, and at once when it comes back into view
     after that. -->
<script lang="ts">
  import { onDestroy } from 'svelte'

  import { ApiError, get, isAbort, NETWORK_MESSAGE } from '@/lib/api'
  import { cstTime } from '@/lib/dataStatus'
  import { longDate } from '@/lib/models/format'
  import { routes } from '@/lib/routes'
  import { gapRows, gapsSummary, headline, sourceRows } from '@/lib/status/statusWords'
  import type { StatusPageProps } from '@/types'
  import type { StatusData, StatusResponse } from '@/types/api'

  let props: StatusPageProps = $props()

  // svelte-ignore state_referenced_locally
  let report = $state<StatusData>(props.report)
  let checkedAt = $state(new Date())
  let failure = $state<string | null>(null)
  let checking = $state(false)

  const rows = $derived(sourceRows(report, props.sources, checkedAt))
  const lead = $derived(headline(report, rows))
  const gaps = $derived(gapRows(report, props.sources))
  const forecast = $derived(report.forecast)

  let controller: AbortController | null = null
  async function check() {
    controller?.abort()
    controller = new AbortController()
    checking = true
    try {
      const body = await get<StatusResponse>('/status', undefined, { signal: controller.signal })
      report = body.data
      checkedAt = new Date()
      failure = null
    } catch (error) {
      if (isAbort(error)) return
      failure =
        error instanceof ApiError && error.status
          ? `We couldn’t check the status just now: ${error.message}`
          : `We couldn’t check the status just now. ${NETWORK_MESSAGE}`
    } finally {
      checking = false
    }
  }

  // Every minute while the page is visible; on coming back into view, at once if a check is due
  let timer: ReturnType<typeof setInterval> | undefined
  function start() {
    clearInterval(timer)
    timer = setInterval(check, props.refresh_seconds * 1000)
  }
  function visibility() {
    if (document.hidden) {
      clearInterval(timer)
      timer = undefined
      return
    }
    if (Date.now() - checkedAt.getTime() >= props.refresh_seconds * 1000) void check()
    start()
  }
  $effect(() => {
    if (!document.hidden) start()
    return () => clearInterval(timer)
  })
  onDestroy(() => controller?.abort())

  const clock = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Etc/GMT+6',
    hour: 'numeric',
    minute: '2-digit',
  })
  /** "10:36 p.m." on the grid's clock */
  function minuteText(when: Date): string {
    return clock.format(when).replace('AM', 'a.m.').replace('PM', 'p.m.')
  }

  const LEVEL_STYLES = {
    ok: 'border-success bg-surface-raised',
    late: 'border-brand-500 bg-brand-50',
    down: 'border-danger bg-surface-raised',
  }
  const STATE_STYLES = {
    'on-time': 'text-success',
    late: 'font-semibold text-danger',
    none: 'text-ink-muted',
  }
  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:document onvisibilitychange={visibility} />

<svelte:head>
  <title>Data status · AgWeather</title>
  <meta
    name="description"
    content="How current AgWeather's weather data are: the newest hour from each source, the forecast in use, and any recent gaps or outages."
  />
</svelte:head>

<article class="max-w-4xl space-y-8">
  <header class="space-y-4">
    <h1 class="text-3xl font-semibold">Data status</h1>
    <div class="rounded-lg border-l-4 p-4 {LEVEL_STYLES[lead.level]}" role="status" aria-live="polite">
      <p class="text-lg">{lead.text}</p>
    </div>
    <p class="text-sm text-ink-muted">
      {`Checked at ${minuteText(checkedAt)} CST. This page checks again every minute while it is open.`}
      {#if checking}<span class="sr-only">Checking…</span>{/if}
    </p>
    {#if failure}
      <p class="text-sm text-danger-ink" role="alert">{failure}</p>
    {/if}
  </header>

  <section aria-labelledby="sources-title" class="space-y-3">
    <h2 id="sources-title" class="text-2xl font-semibold">Weather observations</h2>
    <p class="max-w-prose">
      Each source sends its hours some time after they end. A source is late when its newest hour is older than it
      usually is. Times are Central Standard Time, which AgWeather uses all year; each hour is named by its end.
    </p>

    <!-- Phones: a card per source -->
    <ul class="space-y-3 sm:hidden">
      {#each rows as row (row.id)}
        <li class="space-y-1 rounded-lg border border-line bg-surface-raised p-3">
          <p class="flex items-baseline justify-between gap-3">
            <a href={row.url} class="font-semibold {link}">{row.name}</a>
            <span class="shrink-0 text-sm {STATE_STYLES[row.state]}">{row.stateLabel}</span>
          </p>
          <p class="text-sm">{row.provides}</p>
          <p class="text-sm text-ink-muted">
            {row.newest ? `Newest hour: ${row.newest}; usually ${row.normally}.` : 'No hours received yet.'}
          </p>
        </li>
      {/each}
    </ul>

    <div class="hidden overflow-x-auto sm:block">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-line text-ink-muted">
          <tr>
            <th scope="col" class="py-2 pr-4 font-medium">Source</th>
            <th scope="col" class="py-2 pr-4 font-medium">Provides</th>
            <th scope="col" class="py-2 pr-4 font-medium">Newest hour</th>
            <th scope="col" class="py-2 pr-4 font-medium">Usually</th>
            <th scope="col" class="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row (row.id)}
            <tr class="border-b border-line align-top">
              <th scope="row" class="py-2 pr-4 font-normal"><a href={row.url} class={link}>{row.name}</a></th>
              <td class="py-2 pr-4">{row.provides}</td>
              <td class="py-2 pr-4 whitespace-nowrap">{row.newest ?? 'None yet'}</td>
              <td class="py-2 pr-4 whitespace-nowrap">{row.normally}</td>
              <td class="py-2 whitespace-nowrap {STATE_STYLES[row.state]}">{row.stateLabel}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section aria-labelledby="forecast-title" class="space-y-3">
    <h2 id="forecast-title" class="text-2xl font-semibold">Forecast</h2>
    <dl class="grid gap-x-6 gap-y-2 sm:grid-cols-[12rem_minmax(0,1fr)]">
      <dt class="font-medium">Forecast in use</dt>
      <dd>
        {#if forecast.cycle}
          {`Issued ${cstTime(forecast.cycle)}`}{forecast.last_hour
            ? `, running through ${cstTime(forecast.last_hour)}.`
            : '.'}
        {:else}
          None yet.
        {/if}
      </dd>
      <dt class="font-medium">Status</dt>
      <dd>
        {#if forecast.in_use}
          Current. We use each forecast for 12 hours after it is issued.
        {:else if forecast.fallback === 'openmeteo'}
          Out of date. Until it updates, forecasts for locations inside our area come from Open-Meteo, and maps show no
          forecast.
        {:else if forecast.cycle}
          Out of date. Until it updates, forecast days may be missing.
        {:else}
          No forecast has been published yet.
        {/if}
      </dd>
    </dl>
  </section>

  <section aria-labelledby="daily-title" class="space-y-3">
    <h2 id="daily-title" class="text-2xl font-semibold">Daily values and downloads</h2>
    <dl class="grid gap-x-6 gap-y-2 sm:grid-cols-[12rem_minmax(0,1fr)]">
      <dt class="font-medium">Daily values</dt>
      <dd>
        {report.archive.daily_through
          ? `Complete through ${longDate(report.archive.daily_through)}. Each day runs from midnight to midnight CST; models read these values.`
          : 'None yet.'}
      </dd>
      <dt class="font-medium">Yearly data files</dt>
      <dd>
        {#if report.downloads.files}
          {`${report.downloads.files.toLocaleString('en-US')} files, the newest made ${report.downloads.built_at ? cstTime(report.downloads.built_at) : 'recently'}. `}<a
            href={routes.data()}
            class={link}
          >
            Download them
          </a>.
        {:else}
          None yet.
        {/if}
      </dd>
    </dl>
  </section>

  <section aria-labelledby="gaps-title" class="space-y-3">
    <h2 id="gaps-title" class="text-2xl font-semibold">Missing hours in the last 30 days</h2>
    <p class="max-w-prose">{gapsSummary(gaps, report.gaps.first)}</p>
    {#if gaps.some((g) => g.days.length)}
      <ul class="space-y-3">
        {#each gaps as gap (gap.variable)}
          <li class="rounded-lg border border-line bg-surface-raised p-3">
            <p class="font-semibold">{gap.kind}</p>
            <p class="text-sm text-ink-muted">{`From ${gap.sources}`}</p>
            <p class="mt-1 text-sm">
              {gap.days.length ? gap.days.map((d) => d.text).join(', ') : 'No missing hours.'}
            </p>
          </li>
        {/each}
      </ul>
      <p class="max-w-prose text-sm text-ink-muted">
        Charts and maps show a missing hour as a gap. Running totals, such as degree days, fill short gaps with an
        estimate and say so; precipitation is never estimated. <a href={`${routes.methods()}#gaps`} class={link}>
          How we handle missing data
        </a>.
      </p>
    {/if}
  </section>

  <section aria-labelledby="outages-title" class="space-y-3">
    <h2 id="outages-title" class="text-2xl font-semibold">Recent outages</h2>
    {#if props.outages.length}
      <ul class="space-y-4">
        {#each props.outages as entry (entry.id)}
          <li class="space-y-1 border-t border-line pt-3">
            <p class="text-sm text-ink-muted"><time datetime={entry.date}>{longDate(entry.date)}</time></p>
            <h3 class="text-lg font-semibold">
              <a href={`${routes.changelog()}#entry-${entry.id}`} class={link}>{entry.title}</a>
            </h3>
            <!-- Rendered on the server with raw HTML escaped (updates/render.py) -->
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            <div class="prose">{@html entry.body_html}</div>
          </li>
        {/each}
      </ul>
    {:else}
      <p>We haven’t reported any outages in the last 90 days.</p>
    {/if}
    <p class="text-sm text-ink-muted">
      Outages and delays are also announced in the <a href={`${routes.changelog()}?kind=outage`} class={link}>
        changelog
      </a>
      and its <a href={routes.changelogFeed()} class={link}>Atom feed</a>. Programs can read this page’s facts from
      <a href="/api/v2/status" class={link}>/api/v2/status</a>.
    </p>
  </section>
</article>
