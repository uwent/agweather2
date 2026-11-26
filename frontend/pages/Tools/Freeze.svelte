<!-- Freeze dates and odds (track 5): at a place, this year's (or a past year's) last spring and first fall freeze
     against the typical dates, a row per threshold with the season's length, the chance of a freeze by date (the
     shared FreezeOdds chart), and the chance of a freeze after or by a date the reader chooses. The year's dates
     (`/freeze`, ~0.3 s) show first while the period's (`/climate/frost`, `/climate/frost/chances`, 1–4 s) load;
     FreezeOdds asks for those and hands them back, so they're asked once. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { get, warningsOf } from '@/lib/api'
  import { freezeChances, freezeDates, yearFreezes } from '@/lib/charts/climateCharts'
  import FreezeOdds, { type FreezeAnswers } from '@/lib/climate/FreezeOdds.svelte'
  import PeriodChoice from '@/lib/climate/PeriodChoice.svelte'
  import { DEFAULT_PERIOD, NORMAL_PERIODS, periodWords, periodYears, type Period } from '@/lib/climate/periods'
  import { shareOfYears, temperatureText, thresholdLabel } from '@/lib/climate/words'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { formatDate, today as gridToday } from '@/lib/dates'
  import { monthDay } from '@/lib/models/format'
  import { routes } from '@/lib/routes'
  import Failed from '@/lib/components/Failed.svelte'
  import { request } from '@/lib/request.svelte'
  import {
    coldestLow,
    CUSTOM_RANGE_F,
    cropFreezes,
    freezeAnswer,
    freezeMapUrl,
    freezeNoun,
    fromOpenMeteo,
    lookUp,
    lookUpWords,
    mapThreshold,
    MAP_THRESHOLDS_F,
    stageOf,
    thresholdsFor,
    toolRows,
  } from '@/lib/tools/freeze'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeView } from '@/lib/tools/place'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { FreezeToolProps } from '@/types'
  import type { LocateResponse, PresetsResponse, TableResponse } from '@/types/api'

  let { years: archiveYears }: FreezeToolProps = $props()

  const today = $derived(gridToday())
  const thisYear = $derived(Number(today.slice(0, 4)))
  const units = $derived(currentUnits())

  // Past years back to the 30-year period's first; those before our archive come from Open-Meteo
  const yearOptions = $derived(Array.from({ length: 31 }, (_, k) => thisYear - k))
  const ownArchive = (y: number) => y === thisYear || archiveYears.includes(y)
  const firstArchiveYear = $derived(archiveYears.length ? Math.min(...archiveYears) : thisYear)

  const view = viewState({
    ...PLACE_FIELDS,
    temps: field(codecs.oneOf(['standard', 'crop', 'custom'] as const), 'standard'),
    crop: field(codecs.string, ''),
    temp: field(codecs.number({ digits: 1, min: CUSTOM_RANGE_F.min, max: CUSTOM_RANGE_F.max }), null),
    period: field(codecs.oneOf(NORMAL_PERIODS), DEFAULT_PERIOD),
    year: field(codecs.integer({ min: 1900, max: 2100 }), null),
    on: field(codecs.date, null),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))
  const year = $derived($view.year !== null && yearOptions.includes($view.year) ? $view.year : thisYear)
  const period = $derived<Period>($view.period)
  const stage = $derived(stageOf(year, today))

  // --- Where the place is: inside our area the period's dates and odds come; outside, only the year's

  const locate = request<LocateResponse>()
  const pointKey = $derived(place ? `${place.lat},${place.lng}` : '')
  $effect(() => {
    if (!pointKey) return
    const point = untrack(() => ({ lat: place!.lat, lng: place!.lng }))
    untrack(() => locate.load((signal) => get<LocateResponse>('/locate', point, { signal })))
  })
  const location = $derived(pointKey ? (locate.value.data?.data ?? null) : null)
  const inBox = $derived(location?.in_box ?? null)

  // --- The thresholds: 32, 28 and 24 °F, a crop's killing freeze, or the reader's own

  const presets = request<PresetsResponse>()
  function loadPresets() {
    return presets.load((signal) => get<PresetsResponse>('/degree-days/presets', undefined, { signal }))
  }
  // Asked once, when a crop is first wanted
  let presetsAsked = false
  $effect(() => {
    if ($view.temps !== 'crop' || presetsAsked) return
    presetsAsked = true
    untrack(loadPresets)
  })
  const crops = $derived(presets.value.data ? cropFreezes(presets.value.data.data) : [])
  const crop = $derived(crops.find((c) => c.id === $view.crop) ?? null)
  const thresholds = $derived(thresholdsFor({ choice: $view.temps, crop, custom: $view.temp }))
  const thresholdsKey = $derived(JSON.stringify(thresholds))

  let customText = $state('')
  // Written again when the temperature or the reader's units change (28 °F becomes -2.2 °C, not 28 read as °C)
  $effect(() => {
    const [t, u] = [$view.temp, units]
    untrack(() => {
      customText = u.input('degF', t, u.system === 'metric' ? 1 : 0)
    })
  })
  const customError = $derived.by(() => {
    if ($view.temps !== 'custom' || customText.trim() === '') return null
    const parsed = units.parse('degF', customText)
    if (!parsed.ok) return parsed.error
    const f = parsed.value
    if (f === null || f < CUSTOM_RANGE_F.min || f > CUSTOM_RANGE_F.max)
      return `Choose a temperature from ${temperatureText(CUSTOM_RANGE_F.min, units)} to ${temperatureText(CUSTOM_RANGE_F.max, units)}.`
    return null
  })
  function setCustom(text: string) {
    customText = text
    const parsed = units.parse('degF', text)
    if (!parsed.ok || parsed.value === null) return
    const f = Math.round(parsed.value * 10) / 10
    if (f >= CUSTOM_RANGE_F.min && f <= CUSTOM_RANGE_F.max) view.patch({ temp: f })
  }

  // --- The year's own dates (`/freeze`), first; the forecast's coldest low this year

  const freeze = request<TableResponse>()
  const daily = request<TableResponse>()
  const yearQuery = $derived(
    place && thresholds
      ? {
          lat: place.lat,
          lng: place.lng,
          thresholds,
          units: 'us',
          start: `${year}-01-01`,
          end: year < thisYear ? `${year}-12-31` : undefined,
        }
      : null,
  )
  const yearKey = $derived(JSON.stringify(yearQuery))
  function loadYear() {
    const params = untrack(() => yearQuery)
    if (params) return freeze.load((signal) => get<TableResponse>('/freeze', params, { signal }))
  }
  $effect(() => {
    void yearKey
    untrack(loadYear)
  })
  const dailyKey = $derived(place && year === thisYear ? `${place.lat},${place.lng},${today}` : '')
  function loadDaily() {
    const p = untrack(() => place)
    if (!p) return
    const params = { lat: p.lat, lng: p.lng, start: untrack(() => today), vars: 'air_temperature_min', units: 'us' }
    return daily.load((signal) => get<TableResponse>('/weather/daily', params, { signal }))
  }
  $effect(() => {
    if (dailyKey) untrack(loadDaily)
  })
  onDestroy(() => [locate, presets, freeze, daily].forEach((r) => r.cancel()))

  // The answer belongs to the query it was asked with: an older one isn't shown while a new one loads
  const own = $derived(freeze.value.status === 'done' && yearQuery ? yearFreezes(freeze.value.data) : null)
  const openMeteo = $derived(freeze.value.status === 'done' ? fromOpenMeteo(freeze.value.data) : false)
  const coldest = $derived(
    year === thisYear && daily.value.status === 'done' ? coldestLow(daily.value.data, today) : null,
  )

  // --- The period's dates and odds, as FreezeOdds loads them

  // FreezeOdds is keyed on the place, period and thresholds, so a new one reports from the start
  let answers = $state<FreezeAnswers | null>(null)
  const frostBody = $derived(answers?.frost.status === 'done' ? answers.frost.data : null)
  const chancesBody = $derived(answers?.chances.status === 'done' ? answers.chances.data : null)
  const dates = $derived(frostBody ? freezeDates(frostBody) : null)
  const chances = $derived(chancesBody ? freezeChances(chancesBody) : null)
  const periodShown = $derived(dates?.years ?? chances?.years ?? periodYears(period, today))

  const rows = $derived(thresholds ? toolRows({ thresholds, own, dates, year, today }) : [])
  const lead = $derived(rows[0] ?? null)
  const answer = $derived(
    lead && lead.own
      ? freezeAnswer({
          fahrenheit: lead.fahrenheit,
          own: lead.own,
          typical: lead.typical,
          year,
          today,
          units,
          coldest,
        })
      : null,
  )

  // --- Look up a date

  const lookDate = $derived($view.on ?? today)
  const looked = $derived(chances ? lookUp(chances, lookDate) : null)

  // --- Words for the rows

  function ownDate(date: string | null, season: 'spring' | 'fall'): string {
    if (date) return `${formatDate(date)}${date > today ? ' (forecast)' : ''}`
    const open = year === thisYear && (season === 'fall' || stage === 'spring')
    return open ? 'None yet' : 'None'
  }
  function typicalText(row: (typeof rows)[number], season: 'spring' | 'fall'): string | null {
    const t = row.typical
    if (!t) return null
    const median = season === 'spring' ? t.lastSpring[50] : t.firstFall[50]
    const without = season === 'spring' ? t.withoutSpring : t.withoutFall
    const counted = season === 'spring' ? t.yearsSpring : t.yearsFall
    if (!median) {
      return counted > 0
        ? `None in ${without} of ${counted} years, too many to give a typical date`
        : 'Not enough years with data'
    }
    const lo = season === 'spring' ? t.lastSpring[10] : t.firstFall[10]
    const hi = season === 'spring' ? t.lastSpring[90] : t.firstFall[90]
    const range =
      lo && hi ? `; ${shareOfYears(10)} before ${formatDate(lo)}, ${shareOfYears(10)} after ${formatDate(hi)}` : ''
    return `Typical ${formatDate(median)}${range}`
  }
  const climateLoading = $derived(inBox !== false && !dates && answers?.frost.status !== 'failed')

  const freezeWarnings = $derived(freeze.value.status === 'done' ? warningsOf(freeze.value.data) : [])
  const mapSeason = $derived<'spring' | 'fall'>(stage === 'spring' ? 'spring' : 'fall')
  const mapF = $derived(mapThreshold(thresholds?.[0] ?? 32))
</script>

<svelte:head>
  <title>Freeze dates and odds · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <header class="space-y-3">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.tools()} class="underline hover:text-ink">Tools</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">Freeze dates and odds</li>
      </ol>
    </nav>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold sm:text-3xl">Freeze dates and odds</h1>
      {#if place}<ShareButton url={() => view.shareUrl()} />{/if}
    </div>
    <p class="max-w-prose">
      When did the last freeze of spring or the first freeze of fall come this year, and how does that compare with a
      typical year? Choose a location to see its freeze dates, how long the season without a freeze usually lasts, and
      the chance of a freeze by any date.
    </p>
  </header>

  <section aria-labelledby="freeze-place" class="space-y-3">
    <h2 id="freeze-place" class="sr-only">Location</h2>
    <PlacePicker {place} {location} onpick={(picked) => view.patch(placeView(picked))} />
  </section>

  {#if place}
    <!-- The answer -->
    <section aria-labelledby="freeze-answer" class="rounded-lg border border-line bg-surface-raised p-4">
      <h2 id="freeze-answer" class="sr-only">The answer</h2>
      <div aria-live="polite" class="space-y-2">
        {#if answer}
          <p class="text-lg font-semibold">{answer}</p>
        {:else if !thresholds}
          <p>Choose a crop or a temperature below to see its freeze dates.</p>
        {:else if freeze.value.status === 'loading'}
          <div class="h-8 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
        {/if}
        {#if openMeteo}
          <p class="max-w-prose text-sm">
            {`Our own records begin in ${firstArchiveYear}, so ${year}’s dates come from Open-Meteo’s historical weather for this location, which is coarser than our 2.5 km grid.`}
          </p>
        {/if}
      </div>
      {#if freeze.value.status === 'failed'}
        <Failed {...freeze.value} retry={loadYear} />
      {/if}
      {#if freezeWarnings.length}
        <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on this year’s dates">
          {#each freezeWarnings as warning (warning)}<li>{warning}</li>{/each}
        </ul>
      {/if}
      <p class="mt-2 text-xs text-ink-muted">
        A freeze is a day whose lowest temperature on our 2.5 km grid reached the threshold. Low spots such as valleys
        and frost pockets can freeze when the grid cell around them doesn’t.
      </p>
    </section>

    <!-- Settings -->
    <section aria-labelledby="freeze-settings" class="space-y-4">
      <h2 id="freeze-settings" class="text-lg font-semibold">Settings</h2>
      <div class="flex flex-wrap items-start gap-x-8 gap-y-4">
        <fieldset class="space-y-2 text-sm">
          <legend class="mb-1 font-medium">Temperatures</legend>
          <label class="flex items-center gap-2">
            <input
              type="radio"
              name="freeze-temps"
              value="standard"
              checked={$view.temps === 'standard'}
              onchange={() => view.patch({ temps: 'standard' })}
            />
            {`Frost, hard freeze and killing freeze (${[32, 28, 24].map((f) => temperatureText(f, units)).join(', ')})`}
          </label>
          <div class="flex flex-wrap items-center gap-2">
            <label class="flex items-center gap-2">
              <input
                type="radio"
                name="freeze-temps"
                value="crop"
                checked={$view.temps === 'crop'}
                onchange={() => view.patch({ temps: 'crop' })}
              />
              A crop’s killing freeze
            </label>
            {#if $view.temps === 'crop'}
              <select
                aria-label="Crop"
                class="rounded-md border border-line bg-surface px-2 py-1"
                value={$view.crop}
                onchange={(event) => view.patch({ crop: event.currentTarget.value })}
              >
                <option value="">Choose a crop</option>
                {#each crops as c (c.id)}
                  <option value={c.id}>{`${c.label} (${temperatureText(c.fahrenheit, units)})`}</option>
                {/each}
              </select>
            {/if}
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <label class="flex items-center gap-2">
              <input
                type="radio"
                name="freeze-temps"
                value="custom"
                checked={$view.temps === 'custom'}
                onchange={() => view.patch({ temps: 'custom' })}
              />
              Your own
            </label>
            {#if $view.temps === 'custom'}
              <label class="flex items-center gap-1">
                <input
                  type="text"
                  aria-label="Temperature"
                  inputmode="decimal"
                  class="w-20 rounded-md border border-line bg-surface px-2 py-1"
                  value={customText}
                  aria-invalid={customError ? 'true' : undefined}
                  aria-describedby={customError ? 'freeze-custom-error' : undefined}
                  onchange={(event) => setCustom(event.currentTarget.value)}
                />
                <span class="text-ink-muted">{`${units.label('degF')} or colder`}</span>
              </label>
            {/if}
          </div>
          {#if customError}
            <p id="freeze-custom-error" class="text-danger-ink">{customError}</p>
          {/if}
          {#if presets.value.status === 'failed'}
            <Failed {...presets.value} retry={loadPresets} />
          {/if}
          {#if $view.temps === 'crop' && crop}
            <p class="max-w-prose text-ink-muted">
              {`${crop.label}: ${temperatureText(crop.fahrenheit, units)} or colder.${crop.note ? ` ${crop.note}` : ''}`}
              {#each crop.citations as citation (citation.text)}
                {' '}{#if citation.url}<a href={citation.url} class="text-brand-600 underline hover:text-brand-700">
                    {citation.text}
                  </a>{:else}{citation.text}{/if}
              {/each}
            </p>
          {/if}
        </fieldset>

        <label class="flex flex-col gap-1 text-sm">
          <span class="font-medium">Year</span>
          <select
            class="rounded-md border border-line bg-surface px-2 py-1"
            value={String(year)}
            onchange={(event) => {
              const y = Number(event.currentTarget.value)
              view.patch({ year: y === thisYear ? null : y })
            }}
          >
            {#each yearOptions as y (y)}
              <option value={String(y)}>{ownArchive(y) ? String(y) : `${y} (Open-Meteo)`}</option>
            {/each}
          </select>
        </label>

        <div class="space-y-1 text-sm">
          <PeriodChoice value={period} {today} onchange={(p) => view.patch({ period: p })} name="freeze-period" />
          <p class="max-w-xs text-xs text-ink-muted">The years the typical dates and the odds come from.</p>
        </div>
      </div>
    </section>

    {#if thresholds}
      <!-- A row per threshold -->
      <section aria-labelledby="freeze-dates" class="space-y-3">
        <h2 id="freeze-dates" class="text-lg font-semibold">{`Freeze dates in ${year} and in a typical year`}</h2>
        <p class="max-w-prose text-sm text-ink-muted">
          {inBox === false
            ? `Typical dates are available only inside the area we cover.`
            : `Typical dates are from ${periodWords(periodShown)}: half the years had had their freeze by the typical date, and 1 year in 10 came before or after the early and late dates.`}
        </p>
        <ul class="space-y-3">
          {#each rows as row (row.fahrenheit)}
            <li class="rounded-lg border border-line p-4">
              <h3 class="font-semibold">{thresholdLabel(row.fahrenheit, units)}</h3>
              <dl class="mt-2 grid gap-4 text-sm sm:grid-cols-3">
                {#each ['spring', 'fall'] as const as season (season)}
                  {@const mine = row.own ? (season === 'spring' ? row.own.spring : row.own.fall) : null}
                  <div>
                    <dt class="text-ink-muted">
                      {season === 'spring' ? 'Last freeze in spring' : 'First freeze in fall'}
                    </dt>
                    <dd>
                      <span class="block font-medium">
                        {`${year}: ${row.own ? ownDate(mine, season) : freeze.value.status === 'loading' ? '…' : '—'}`}
                      </span>
                      {#if row.own && !mine && year === thisYear && coldest && (season === 'fall' || stage === 'spring')}
                        <span class="block text-ink-muted">
                          {`Coldest low in the forecast: ${temperatureText(coldest.fahrenheit, units)}, ${formatDate(coldest.date, { weekday: true })}`}
                        </span>
                      {/if}
                      {#if inBox !== false}
                        <span class="block text-ink-muted">
                          {typicalText(row, season) ?? (climateLoading ? '…' : '')}
                        </span>
                      {/if}
                    </dd>
                  </div>
                {/each}
                <div>
                  <dt class="text-ink-muted">Season without it</dt>
                  <dd>
                    <span class="block font-medium">
                      {`${year}: ${row.season ? `${row.season.days} days${row.season.soFar ? ' so far' : ''}` : stage === 'spring' ? 'Not over yet' : row.own ? '—' : '…'}`}
                    </span>
                    {#if inBox !== false}
                      {#if row.typical?.seasonDays[50] != null}
                        <span class="block text-ink-muted">
                          {`Typical ${row.typical.seasonDays[50]} days${row.typical.seasonDays[10] != null && row.typical.seasonDays[90] != null ? `; ${row.typical.seasonDays[10]} to ${row.typical.seasonDays[90]} in 8 years of 10` : ''}`}
                        </span>
                      {:else if climateLoading}
                        <span class="block text-ink-muted">…</span>
                      {/if}
                    {/if}
                  </dd>
                </div>
              </dl>
            </li>
          {/each}
        </ul>
      </section>

      {#if inBox !== false}
        <!-- The odds -->
        <section aria-labelledby="freeze-odds" class="space-y-3">
          <h2 id="freeze-odds" class="text-lg font-semibold">Freeze odds through the year</h2>
          {#key `${pointKey}|${period}|${thresholdsKey}`}
            <FreezeOdds
              lat={place.lat}
              lng={place.lng}
              {today}
              {period}
              {thresholds}
              thisYear={null}
              table={false}
              onanswers={(a) => (answers = a)}
            />
          {/key}
        </section>

        <!-- Look up a date -->
        <section aria-labelledby="freeze-lookup" class="space-y-3">
          <h2 id="freeze-lookup" class="text-lg font-semibold">Look up a date</h2>
          <p class="max-w-prose text-sm">
            For a date from January through June, the chance that a freeze still came after it; from July through
            December, the chance that the first freeze of fall had come by it. Only the month and day count.
          </p>
          <label class="flex flex-wrap items-center gap-2 text-sm">
            <span class="text-ink-muted">Date</span>
            <input
              type="date"
              class="rounded-md border border-line bg-surface px-2 py-1"
              value={lookDate}
              onchange={(event) => {
                const value = event.currentTarget.value
                if (value) view.patch({ on: value === today ? null : value })
              }}
            />
          </label>
          {#if looked}
            <ul class="max-w-prose list-disc space-y-1 pl-5" aria-live="polite">
              {#each looked.chances as found (found.fahrenheit)}
                <li>{lookUpWords(found, looked.date, looked.season, units)}</li>
              {/each}
            </ul>
            <p class="text-xs text-ink-muted">{`Over ${periodWords(periodShown)}.`}</p>
          {:else if chances === null && answers?.chances.status !== 'failed'}
            <div class="h-12 animate-pulse rounded-md bg-surface-raised" aria-hidden="true"></div>
          {/if}
        </section>

        <!-- The map -->
        <section aria-labelledby="freeze-map" class="space-y-2">
          <h2 id="freeze-map" class="text-lg font-semibold">On the map</h2>
          <ul class="list-disc space-y-1 pl-5">
            <li>
              <a
                href={freezeMapUrl({ layer: 'freeze_dates', fahrenheit: mapF, period, season: mapSeason, at: place })}
                class="text-brand-600 underline hover:text-brand-700"
              >
                {`The typical ${mapSeason === 'spring' ? 'last spring' : 'first fall'} ${freezeNoun(mapF, units)} across the region`}
              </a>
            </li>
            <li>
              <a
                href={freezeMapUrl({
                  layer: 'freeze_chance',
                  fahrenheit: mapF,
                  period,
                  season: mapSeason,
                  date: lookDate,
                  at: place,
                })}
                class="text-brand-600 underline hover:text-brand-700"
              >
                {`The chance of a ${freezeNoun(mapF, units)} ${lookDate.slice(5) < '07-01' ? 'after' : 'by'} ${monthDay(lookDate.slice(5, 10))} across the region`}
              </a>
            </li>
          </ul>
          {#if thresholds[0] !== mapF}
            <p class="text-sm text-ink-muted">
              {`The maps hold ${MAP_THRESHOLDS_F.map((f) => temperatureText(f, units)).join(', ')} only, so these open at ${temperatureText(mapF, units)}, the nearest.`}
            </p>
          {/if}
        </section>
      {:else if inBox === false}
        <p class="max-w-prose text-sm">
          The chance of a freeze by date and the typical dates come from our own records, which cover only our area.
          This location’s dates above come from Open-Meteo’s weather.
        </p>
      {/if}
    {/if}
  {/if}

  <section aria-labelledby="freeze-about" class="space-y-2">
    <h2 id="freeze-about" class="text-lg font-semibold">About these dates</h2>
    <p class="max-w-prose">
      {`A frost here is a low of ${temperatureText(32, units)} or colder, a hard freeze ${temperatureText(28, units)} and a killing freeze ${temperatureText(24, units)}. The last freeze of spring is the last such day from January through June; the first freeze of fall, the first from July through December. The forecast’s days count toward this year’s dates. Typical dates and odds describe past years’ weather; they are guidance for planning, not a forecast.`}
    </p>
    <p class="text-sm">
      <a href={routes.methods()} class="text-brand-600 underline hover:text-brand-700">How we make our weather data</a>
    </p>
  </section>
</div>
