<!-- The crop GDD outlook (track 5 P1): at a place, growing degree days since planting for a crop, when it reaches
     maturity (corn's black layer for the hybrid chosen, another crop's at the degree days the reader types) and its
     other stages, with the range from past years' weather after the forecast, the chance of a fall freeze before
     then, the normal year and up to three past years. Corn runs the corn stage model (`/models/corn-stages/run`,
     with `end` on December 31 so its projection runs past the model's season); a planting the model can't project
     from (past the forecast) and other crops go through `/degree-days` with `targets=`. The normal comes from
     `/climate/compare` from the planting date, the freeze chance from `/climate/frost/chances`. -->
<script lang="ts">
  import { onDestroy, untrack } from 'svelte'

  import { get } from '@/lib/api'
  import ChartCard from '@/lib/charts/ChartCard.svelte'
  import { compareTable, freezeChances } from '@/lib/charts/climateCharts'
  import PeriodChoice from '@/lib/climate/PeriodChoice.svelte'
  import { DEFAULT_PERIOD, NORMAL_PERIODS, periodWords, type Period } from '@/lib/climate/periods'
  import { temperatureText } from '@/lib/climate/words'
  import ShareButton from '@/lib/components/ShareButton.svelte'
  import { formatDate, today as gridToday } from '@/lib/dates'
  import { routes } from '@/lib/routes'
  import Failed from '@/lib/sites/Failed.svelte'
  import { request } from '@/lib/sites/request.svelte'
  import {
    CHART_STAGES,
    comparisonYears,
    cropChoices,
    cropGddOption,
    cropGddRows,
    cropGddSummary,
    dateReaching,
    DEFAULT_FREEZE_F,
    fallChance,
    fallChances,
    FREEZE_RANGE_F,
    latestTotal,
    MATURITY,
    MAX_YEARS,
    normalCurve,
    outlookAnswer,
    outlookFromDegreeDays,
    outlookFromRun,
    plantingDate,
    stageRows,
    stageTargets,
    subjectWords,
    TARGET_RANGE_F,
    yearCurve,
    yearsCodec,
    type Outlook,
    type Target,
  } from '@/lib/tools/cropGdd'
  import PlacePicker from '@/lib/tools/PlacePicker.svelte'
  import { PLACE_FIELDS, placeOf, placeView } from '@/lib/tools/place'
  import { currentUnits } from '@/lib/units'
  import { codecs, field, viewState } from '@/lib/viewState'
  import type { CropGddToolProps } from '@/types'
  import type { LocateResponse, PresetsResponse, TableResponse } from '@/types/api'

  let { model, years: archiveYears }: CropGddToolProps = $props()

  const today = $derived(gridToday())
  const thisYear = $derived(Number(today.slice(0, 4)))
  const end = $derived(`${thisYear}-12-31`)
  const units = $derived(currentUnits())
  const firstArchiveYear = $derived(archiveYears.length ? Math.min(...archiveYears) : thisYear)
  const ownArchive = (y: number) => archiveYears.includes(y)

  const maturityOption = $derived(model.options.find((o) => o.name === 'black_layer_gdd') ?? null)
  const hybrids = $derived(maturityOption?.choices ?? [])

  const view = viewState({
    ...PLACE_FIELDS,
    crop: field(codecs.string, 'corn'),
    hybrid: field(codecs.string, ''),
    target: field(codecs.number({ digits: 0, min: TARGET_RANGE_F.min, max: TARGET_RANGE_F.max }), null),
    planting: field(codecs.date, null),
    freeze: field(codecs.number({ digits: 1, min: FREEZE_RANGE_F.min, max: FREEZE_RANGE_F.max }), null),
    period: field(codecs.oneOf(NORMAL_PERIODS), DEFAULT_PERIOD),
    years: field(yearsCodec, []),
  })
  onDestroy(() => view.destroy())

  const place = $derived(placeOf($view))
  const period = $derived<Period>($view.period)
  const hybrid = $derived(
    hybrids.find((h) => h.value === $view.hybrid)?.value ?? maturityOption?.default ?? hybrids[0]?.value ?? '2500',
  )

  // --- Where the place is, and its typical planting dates

  const locate = request<LocateResponse>()
  const pointKey = $derived(place ? `${place.lat},${place.lng}` : '')
  $effect(() => {
    if (!pointKey) return
    const point = untrack(() => ({ lat: place!.lat, lng: place!.lng }))
    untrack(() => locate.load((signal) => get<LocateResponse>('/locate', point, { signal })))
  })
  const location = $derived(pointKey ? (locate.value.data?.data ?? null) : null)
  const inBox = $derived(location?.in_box ?? null)

  // --- The crops (the degree-day presets counted from planting)

  const presets = request<PresetsResponse>()
  function loadPresets() {
    return presets.load((signal) => get<PresetsResponse>('/degree-days/presets', undefined, { signal }))
  }
  loadPresets()
  const crops = $derived(presets.value.data ? cropChoices(presets.value.data.data) : [])
  const crop = $derived(crops.find((c) => c.id === $view.crop) ?? crops[0] ?? null)
  const isCorn = $derived(crop?.model === model.id)
  const setting = $derived(crop?.setting ?? 'modified_50_86')

  const typical = $derived(location?.planting?.find((p) => p.crop === crop?.id) ?? null)
  const planting = $derived(
    plantingDate({
      chosen: $view.planting,
      typical: typical?.typical ?? null,
      fallback: isCorn ? (model.biofix?.default ?? null) : null,
      year: thisYear,
    }),
  )
  const freezeF = $derived($view.freeze ?? crop?.freezeF ?? DEFAULT_FREEZE_F)

  // --- The reader's own maturity (other crops) and freeze temperature, typed in their units

  let targetText = $state('')
  $effect(() => {
    const t = $view.target
    untrack(() => {
      targetText = t === null ? '' : units.input('degF_day', t, 0)
    })
  })
  const targetError = $derived.by(() => {
    if (isCorn || targetText.trim() === '') return null
    const parsed = units.parse('degF_day', targetText)
    if (!parsed.ok) return parsed.error
    const f = parsed.value
    if (f === null || f < TARGET_RANGE_F.min || f > TARGET_RANGE_F.max)
      return `Choose a total from ${units.format('degF_day', TARGET_RANGE_F.min, { digits: 0 })} to ${units.format('degF_day', TARGET_RANGE_F.max, { digits: 0 })}.`
    return null
  })
  function setTarget(text: string) {
    targetText = text
    if (text.trim() === '') return view.patch({ target: null })
    const parsed = units.parse('degF_day', text)
    if (!parsed.ok || parsed.value === null) return
    const f = Math.round(parsed.value)
    if (f >= TARGET_RANGE_F.min && f <= TARGET_RANGE_F.max) view.patch({ target: f })
  }

  let freezeText = $state('')
  $effect(() => {
    const f = freezeF
    untrack(() => {
      freezeText = units.input('degF', f, units.system === 'metric' ? 1 : 0)
    })
  })
  const freezeError = $derived.by(() => {
    const parsed = units.parse('degF', freezeText)
    if (!parsed.ok) return parsed.error
    const f = parsed.value
    if (f === null || f < FREEZE_RANGE_F.min || f > FREEZE_RANGE_F.max)
      return `Choose a temperature from ${temperatureText(FREEZE_RANGE_F.min, units)} to ${temperatureText(FREEZE_RANGE_F.max, units)}.`
    return null
  })
  function setFreeze(text: string) {
    freezeText = text
    const parsed = units.parse('degF', text)
    if (!parsed.ok || parsed.value === null) return
    const f = Math.round(parsed.value * 10) / 10
    if (f < FREEZE_RANGE_F.min || f > FREEZE_RANGE_F.max) return
    view.patch({ freeze: f === crop?.freezeF || (crop?.freezeF == null && f === DEFAULT_FREEZE_F) ? null : f })
  }

  // --- This season: corn's stage model, else (or when it can't project) degree days with targets

  const run = request<TableResponse>()
  const degreeDays = request<TableResponse>()
  const runQuery = $derived(
    place && crop && isCorn
      ? {
          lat: place.lat,
          lng: place.lng,
          planting_date: planting.date,
          black_layer_gdd: hybrid,
          projection: true,
          end,
          units: 'us',
        }
      : null,
  )
  const runKey = $derived(JSON.stringify(runQuery))
  function loadRun() {
    const params = untrack(() => runQuery)
    if (params) return run.load((signal) => get<TableResponse>(`/models/${model.id}/run`, params, { signal }))
  }
  $effect(() => {
    void runKey
    untrack(loadRun)
  })
  const runBody = $derived(runQuery && run.value.status === 'done' ? run.value.data : null)
  const fromRun = $derived(runBody ? outlookFromRun(runBody) : null)

  // The targets `/degree-days` is asked for: corn's stages (from the run, for the hybrid), or the reader's total
  const ownTarget = $derived<Target | null>(
    $view.target !== null ? { code: 'target', name: 'Your target', gdd: $view.target, estimated: false } : null,
  )
  const ddTargets = $derived<Target[] | null>(
    isCorn ? (runBody && !fromRun ? stageTargets(runBody) : null) : ownTarget ? [ownTarget] : [],
  )
  const ddQuery = $derived(
    place && crop && ddTargets
      ? {
          lat: place.lat,
          lng: place.lng,
          dd: setting,
          biofix: planting.date,
          projection: true,
          end,
          targets: ddTargets.length ? ddTargets.map((t) => t.gdd) : undefined,
          units: 'us',
        }
      : null,
  )
  const ddKey = $derived(JSON.stringify(ddQuery))
  function loadDegreeDays() {
    const params = untrack(() => ddQuery)
    if (params) return degreeDays.load((signal) => get<TableResponse>('/degree-days', params, { signal }))
  }
  $effect(() => {
    void ddKey
    untrack(loadDegreeDays)
  })

  const outlook = $derived.by<Outlook | null>(() => {
    if (isCorn && fromRun) return fromRun
    if (!ddQuery || !ddTargets || degreeDays.value.status !== 'done') return null
    return outlookFromDegreeDays({ body: degreeDays.value.data, setting, planting: planting.date, targets: ddTargets })
  })
  const main = $derived(isCorn && (!runBody || fromRun) ? run : degreeDays)
  const retryMain = () => (main === run ? loadRun() : loadDegreeDays())

  // --- The normal from planting, and the fall freeze chance (inside our area)

  const compare = request<TableResponse>()
  const compareQuery = $derived(
    place && crop && inBox
      ? { lat: place.lat, lng: place.lng, dd: setting, start: planting.date, vars: '', period, units: 'us' }
      : null,
  )
  const compareKey = $derived(JSON.stringify(compareQuery))
  function loadCompare() {
    const params = untrack(() => compareQuery)
    if (params) return compare.load((signal) => get<TableResponse>('/climate/compare', params, { signal }))
  }
  $effect(() => {
    void compareKey
    untrack(loadCompare)
  })
  const normalTable = $derived(
    compareQuery && compare.value.status === 'done' ? compareTable(compare.value.data) : null,
  )
  const normal = $derived(
    normalTable && outlook ? normalCurve({ table: normalTable, setting, dates: outlook.dates }) : null,
  )

  const frost = request<TableResponse>()
  const frostQuery = $derived(
    place && inBox ? { lat: place.lat, lng: place.lng, thresholds: freezeF, period, units: 'us' } : null,
  )
  const frostKey = $derived(JSON.stringify(frostQuery))
  function loadFrost() {
    const params = untrack(() => frostQuery)
    if (params) return frost.load((signal) => get<TableResponse>('/climate/frost/chances', params, { signal }))
  }
  $effect(() => {
    void frostKey
    untrack(loadFrost)
  })
  const chances = $derived(frostQuery && frost.value.status === 'done' ? freezeChances(frost.value.data) : null)

  // --- Comparison years: a request each, fetched when added (those before our archive from Open-Meteo)

  const slots = Array.from({ length: MAX_YEARS }, () => request<TableResponse>())
  onDestroy(() => [locate, presets, run, degreeDays, compare, frost, ...slots].forEach((r) => r.cancel()))
  const chosenYears = $derived(($view.years ?? []).filter((y) => y < thisYear).slice(0, MAX_YEARS))
  const yearQueries = $derived(
    chosenYears.map((y) =>
      place && crop
        ? {
            lat: place.lat,
            lng: place.lng,
            dd: setting,
            biofix: `${y}-${planting.date.slice(5)}`,
            end: `${y}-12-31`,
            units: 'us',
          }
        : null,
    ),
  )
  const yearKeys = $derived(Array.from({ length: MAX_YEARS }, (_, k) => JSON.stringify(yearQueries[k] ?? null)))
  function loadYear(k: number) {
    const params = untrack(() => yearQueries[k])
    if (params) return slots[k].load((signal) => get<TableResponse>('/degree-days', params, { signal }))
  }
  for (let k = 0; k < MAX_YEARS; k++) {
    $effect(() => {
      void yearKeys[k]
      untrack(() => loadYear(k))
    })
  }
  const yearCurves = $derived(
    outlook
      ? chosenYears.flatMap((y, k) => {
          const loaded = slots[k].value
          if (!yearQueries[k] || loaded.status !== 'done') return []
          const curve = yearCurve({ body: loaded.data, setting, dates: outlook.dates })
          return curve.year === y ? [curve] : []
        })
      : [],
  )
  let yearToAdd = $state('')
  const yearChoices = $derived(comparisonYears(thisYear).filter((y) => !chosenYears.includes(y)))
  function addYear() {
    const y = Number(yearToAdd)
    if (!y || chosenYears.includes(y) || chosenYears.length >= MAX_YEARS) return
    view.patch({ years: [...chosenYears, y] })
    yearToAdd = ''
  }
  const removeYear = (y: number) => view.patch({ years: chosenYears.filter((other) => other !== y) })

  // --- The answer

  const maturity = $derived(
    outlook ? (outlook.targets.find((t) => t.code === (isCorn ? MATURITY : 'target')) ?? null) : null,
  )
  const what = $derived(
    isCorn ? 'black layer' : $view.target !== null ? units.format('degF_day', $view.target, { digits: 0 }) : '',
  )
  const normalDate = $derived(
    maturity && normal && outlook ? dateReaching(outlook.dates, normal.mean, maturity.gdd) : null,
  )
  const chance = $derived(maturity?.p50 ? fallChance(chances, freezeF, maturity.p50) : null)
  const latest = $derived(outlook ? latestTotal(outlook) : null)
  const subject = $derived(
    crop ? subjectWords({ crop: crop.label, hybrid: isCorn ? hybrid : null, planting: planting.date }) : '',
  )
  const answer = $derived(
    maturity && crop ? outlookAnswer({ subject, what, maturity, latest, normalDate, freezeF, chance, units }) : null,
  )
  const openMeteoYears = $derived(yearCurves.filter((y) => y.openMeteo).map((y) => y.year))

  // --- The chart and the table

  const chartStages = $derived<Target[]>(
    outlook
      ? isCorn
        ? outlook.targets.filter((t) => (CHART_STAGES as readonly string[]).includes(t.code))
        : ownTarget
          ? [{ ...ownTarget, code: 'Target' }]
          : []
      : [],
  )
  const chanceLine = $derived(outlook ? fallChances(chances, freezeF, outlook.dates) : [])
  const rows = $derived(outlook ? stageRows({ outlook, normal, years: yearCurves }) : [])
  const periodShown = $derived(normalTable?.years ?? null)
  const loadingSeason = $derived(main.value.status === 'loading' && !outlook)
</script>

<svelte:head>
  <title>Crop GDD outlook · AgWeather</title>
</svelte:head>

<div class="space-y-8">
  <header class="space-y-3">
    <nav aria-label="Breadcrumb" class="text-sm">
      <ol class="flex flex-wrap items-center gap-1 text-ink-muted">
        <li><a href={routes.tools()} class="underline hover:text-ink">Tools</a></li>
        <li aria-hidden="true" class="px-0.5">/</li>
        <li aria-current="page" class="text-ink">Crop GDD outlook</li>
      </ol>
    </nav>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold sm:text-3xl">Crop GDD outlook</h1>
      {#if place}<ShareButton url={() => view.shareUrl()} />{/if}
    </div>
    <p class="max-w-prose">
      When will my crop reach maturity, and how likely is a fall freeze before then? Choose a location, a crop and a
      planting date to see growing degree days (GDD) since planting, when each stage is likely to come, and how this
      year compares with a normal year and with past years. Growing degree days measure the heat a crop has had to grow:
      each day adds how far its temperatures rose above the crop’s base temperature.
    </p>
  </header>

  <section aria-labelledby="gdd-place" class="space-y-3">
    <h2 id="gdd-place" class="sr-only">Location</h2>
    <PlacePicker {place} {location} onpick={(picked) => view.patch(placeView(picked))} />
  </section>

  {#if place}
    <!-- The answer -->
    <section aria-labelledby="gdd-answer" class="rounded-lg border border-line bg-surface-raised p-4">
      <h2 id="gdd-answer" class="sr-only">The answer</h2>
      <div aria-live="polite" class="space-y-2">
        {#if answer}
          <p class="text-lg font-semibold">{answer.headline}</p>
          {#each answer.details as detail (detail)}<p class="max-w-prose">{detail}</p>{/each}
        {:else if crop && !isCorn && $view.target === null}
          <p>Type the growing degree days your variety needs to reach maturity, below, to see when it’s likely.</p>
        {:else if loadingSeason || presets.value.status === 'loading'}
          <div class="h-8 animate-pulse rounded-md bg-surface" aria-hidden="true"></div>
        {/if}
      </div>
      {#if main.value.status === 'failed'}
        <Failed {...main.value} retry={retryMain} />
      {/if}
      {#if presets.value.status === 'failed'}
        <Failed {...presets.value} retry={loadPresets} />
      {/if}
      {#if outlook?.warnings.length}
        <ul class="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-muted" aria-label="Notes on these results">
          {#each outlook.warnings as warning (warning)}<li>{warning}</li>{/each}
        </ul>
      {/if}
      {#if inBox === false}
        <p class="mt-2 max-w-prose text-sm">
          This location is outside the area we cover, so its weather comes from Open-Meteo, and the normal and the
          freeze chance, which come from our own records, aren’t available.
        </p>
      {/if}
      <p class="mt-2 text-xs text-ink-muted">
        Dates after the forecast come from the weather of past years ({outlook?.projectionYears.length
          ? `${Math.min(...outlook.projectionYears)}–${Math.max(...outlook.projectionYears)}`
          : 'in our records'}): half of those years reach a stage by the middle date, and 8 in 10 within the range. They
        are guidance for planning, not a forecast.
      </p>
    </section>

    <!-- Settings -->
    <section aria-labelledby="gdd-settings" class="space-y-4">
      <h2 id="gdd-settings" class="text-lg font-semibold">Settings</h2>
      <div class="flex flex-wrap items-start gap-x-8 gap-y-4 text-sm">
        <label class="flex flex-col gap-1">
          <span class="font-medium">Crop</span>
          <select
            class="rounded-md border border-line bg-surface px-2 py-1"
            value={crop?.id ?? ''}
            onchange={(event) => view.patch({ crop: event.currentTarget.value, planting: null, freeze: null })}
          >
            {#each crops as c (c.id)}<option value={c.id}>{c.label}</option>{/each}
          </select>
        </label>

        {#if isCorn}
          <label class="flex flex-col gap-1">
            <span class="font-medium">Hybrid maturity</span>
            <select
              class="rounded-md border border-line bg-surface px-2 py-1"
              value={hybrid}
              onchange={(event) => view.patch({ hybrid: event.currentTarget.value })}
            >
              {#each hybrids as h (h.value)}<option value={h.value}>{h.label}</option>{/each}
            </select>
            <span class="max-w-xs text-xs text-ink-muted">
              GDD from planting to black layer, as seed companies rate it.
            </span>
          </label>
        {:else if crop}
          <div class="flex flex-col gap-1">
            <label for="gdd-target" class="font-medium">Maturity</label>
            <span class="flex items-center gap-1">
              <input
                id="gdd-target"
                type="text"
                inputmode="numeric"
                class="w-24 rounded-md border border-line bg-surface px-2 py-1"
                value={targetText}
                aria-invalid={targetError ? 'true' : undefined}
                aria-describedby="gdd-target-help{targetError ? ' gdd-target-error' : ''}"
                onchange={(event) => setTarget(event.currentTarget.value)}
              />
              <span class="text-ink-muted">{units.label('degF_day')}</span>
            </span>
            <span id="gdd-target-help" class="max-w-xs text-xs text-ink-muted">
              The GDD from planting your variety needs, from its seed company or extension.
            </span>
            {#if targetError}<span id="gdd-target-error" class="text-danger-ink">{targetError}</span>{/if}
          </div>
        {/if}

        <div class="flex flex-col gap-1">
          <label for="gdd-planting" class="font-medium">Planting date</label>
          <input
            id="gdd-planting"
            type="date"
            class="rounded-md border border-line bg-surface px-2 py-1"
            min={`${thisYear}-01-01`}
            max={end}
            value={planting.date}
            aria-describedby="gdd-planting-help"
            onchange={(event) => {
              const value = event.currentTarget.value
              if (value) view.patch({ planting: value })
            }}
          />
          <span id="gdd-planting-help" class="max-w-xs text-xs text-ink-muted">
            {planting.from === 'typical'
              ? `The typical date for ${crop?.label.toLowerCase() ?? 'this crop'} in this ${typical?.level === 'state' ? 'state' : typical?.level === 'county' ? 'county' : 'area'}; change it to your own.`
              : planting.from === 'fallback'
                ? 'We have no typical planting date for this crop here: enter your own.'
                : 'Your planting date.'}
          </span>
        </div>

        <div class="flex flex-col gap-1">
          <label for="gdd-freeze" class="font-medium">Fall freeze</label>
          <span class="flex items-center gap-1">
            <input
              id="gdd-freeze"
              type="text"
              inputmode="decimal"
              class="w-20 rounded-md border border-line bg-surface px-2 py-1"
              value={freezeText}
              aria-invalid={freezeError ? 'true' : undefined}
              aria-describedby="gdd-freeze-help{freezeError ? ' gdd-freeze-error' : ''}"
              onchange={(event) => setFreeze(event.currentTarget.value)}
            />
            <span class="text-ink-muted">{`${units.label('degF')} or colder`}</span>
          </span>
          <span id="gdd-freeze-help" class="max-w-xs text-xs text-ink-muted">
            {crop?.freezeF != null
              ? `${crop.label}’s killing freeze is ${temperatureText(crop.freezeF, units)}.${crop.freezeNote ? ` ${crop.freezeNote}` : ''}`
              : `We list no killing freeze for this crop; ${temperatureText(DEFAULT_FREEZE_F, units)}, a hard freeze, is shown.`}
          </span>
          {#if freezeError}<span id="gdd-freeze-error" class="text-danger-ink">{freezeError}</span>{/if}
        </div>

        <div class="space-y-1">
          <PeriodChoice value={period} {today} onchange={(p) => view.patch({ period: p })} name="gdd-period" />
          <p class="max-w-xs text-xs text-ink-muted">The years the normal and the freeze chance come from.</p>
        </div>
      </div>

      <fieldset class="space-y-2 text-sm">
        <legend class="font-medium">Compare with past years</legend>
        <div class="flex flex-wrap items-center gap-2">
          {#each chosenYears as y, k (y)}
            {@const loaded = slots[k].value}
            <span class="inline-flex items-center gap-1 rounded-full border border-line bg-surface px-3 py-1">
              {ownArchive(y) ? String(y) : `${y} (Open-Meteo)`}
              {#if loaded.status === 'loading'}<span class="text-ink-muted">{' (loading)'}</span>{/if}
              <button
                type="button"
                class="ml-1 rounded-full px-1 text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600"
                aria-label={`Remove ${y}`}
                onclick={() => removeYear(y)}
              >
                ×
              </button>
            </span>
          {/each}
          {#if chosenYears.length < MAX_YEARS}
            <label class="flex items-center gap-2">
              <span class="sr-only">Year to add</span>
              <select
                class="rounded-md border border-line bg-surface px-2 py-1"
                value={yearToAdd}
                onchange={(event) => (yearToAdd = event.currentTarget.value)}
              >
                <option value="">Choose a year</option>
                {#each yearChoices as y (y)}
                  <option value={String(y)}>{ownArchive(y) ? String(y) : `${y} (Open-Meteo)`}</option>
                {/each}
              </select>
            </label>
            <button
              type="button"
              class="rounded-md border border-line bg-surface px-3 py-1 hover:bg-surface-raised disabled:opacity-60"
              disabled={!yearToAdd}
              onclick={addYear}
            >
              Add
            </button>
          {/if}
        </div>
        {#each chosenYears as y, k (y)}
          {@const loaded = slots[k].value}
          {#if loaded.status === 'failed'}
            <Failed {...loaded} retry={() => loadYear(k)} />
          {/if}
        {/each}
        <p class="max-w-prose text-xs text-ink-muted">
          {`Up to ${MAX_YEARS} years, each planted on the same day of the year. Our own records begin in ${firstArchiveYear}; earlier years come from Open-Meteo’s historical weather, which is coarser than our 2.5 km grid and takes a few seconds to load.`}
        </p>
      </fieldset>
    </section>

    <!-- The chart -->
    <section aria-labelledby="gdd-chart" class="space-y-3">
      <h2 id="gdd-chart" class="text-lg font-semibold">{`Growing degree days since planting, ${thisYear}`}</h2>
      {#if outlook && outlook.dates.length}
        <div aria-busy={main.value.status === 'loading'}>
          <ChartCard
            title={`${crop?.label ?? 'Crop'} planted ${formatDate(planting.date)}`}
            info="Above: growing degree days since planting, observed (solid) and forecast (shaded), then, dashed, the middle of what past years’ weather would give, with the range 8 years in 10 fell within. The normal is dashed over its usual range; past years are thin lines; the stages are horizontal lines. Below: the chance that the first fall freeze at your temperature has come by each date."
            height="30rem"
            build={(palette) =>
              cropGddOption({
                outlook: outlook!,
                normal,
                normalYears: periodShown,
                years: yearCurves,
                stages: chartStages,
                chances: chanceLine,
                freezeF,
                units,
                palette,
                today,
              })}
            summary={cropGddSummary({ outlook, maturity, normalDate, freezeF, units })}
            table={() => cropGddRows({ outlook: outlook!, normal, years: yearCurves, chances: chanceLine, units })}
          />
        </div>
        {#if openMeteoYears.length}
          <p class="text-xs text-ink-muted">
            {`${openMeteoYears.join(' and ')} ${openMeteoYears.length === 1 ? 'comes' : 'come'} from Open-Meteo’s historical weather for this location.`}
          </p>
        {/if}
        {#if inBox && periodShown}
          <p class="text-xs text-ink-muted">
            {`The normal and the freeze chance are from ${periodWords(periodShown)}.`}
          </p>
        {/if}
        {#if compare.value.status === 'failed'}<Failed {...compare.value} retry={loadCompare} />{/if}
        {#if frost.value.status === 'failed'}<Failed {...frost.value} retry={loadFrost} />{/if}
      {:else if loadingSeason}
        <div class="h-96 animate-pulse rounded-lg bg-surface-raised" aria-hidden="true"></div>
      {/if}
    </section>

    <!-- The table -->
    {#if rows.length}
      <section aria-labelledby="gdd-stages" class="space-y-3">
        <h2 id="gdd-stages" class="text-lg font-semibold">{isCorn ? 'Growth stages' : 'Maturity'}</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="border-b border-line text-ink-muted">
              <tr>
                <th scope="col" class="py-2 pr-4 font-medium">Stage</th>
                <th scope="col" class="py-2 pr-4 font-medium">{`GDD (${units.label('degF_day')})`}</th>
                <th scope="col" class="py-2 pr-4 font-medium">{String(thisYear)}</th>
                {#if normal}<th scope="col" class="py-2 pr-4 font-medium">Normal year</th>{/if}
                {#each yearCurves as y (y.year)}<th scope="col" class="py-2 pr-4 font-medium">
                    {String(y.year)}
                  </th>{/each}
              </tr>
            </thead>
            <tbody>
              {#each rows as row (row.code)}
                <tr class="border-b border-line last:border-0">
                  <th scope="row" class="py-2 pr-4 font-medium">
                    {isCorn ? `${row.code} ${row.name}${row.estimated ? ' (estimated)' : ''}` : 'Maturity'}
                  </th>
                  <td class="py-2 pr-4 tabular-nums">
                    {units.format('degF_day', row.gdd, { digits: 0, unit: false })}
                  </td>
                  <td class="py-2 pr-4">{row.thisYear}</td>
                  {#if normal}<td class="py-2 pr-4">{row.normal ? formatDate(row.normal) : 'Not reached'}</td>{/if}
                  {#each row.years as date, k (k)}
                    <td class="py-2 pr-4">{date ? formatDate(date) : 'Not reached'}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="max-w-prose text-xs text-ink-muted">
          {`“Not reached” means the total didn’t get there by December 31.${isCorn ? ' Tasseling is estimated between the leaf stages and silking.' : ''}`}
        </p>
      </section>
    {/if}
  {/if}

  <section aria-labelledby="gdd-about" class="space-y-2">
    <h2 id="gdd-about" class="text-lg font-semibold">About this outlook</h2>
    <p class="max-w-prose">
      {`Each crop counts degree days its own way, from its planting date. ${crop ? `${crop.label}: ${crop.notes ?? ''}` : ''}`}
    </p>
    {#if isCorn}
      <p class="max-w-prose">
        Corn’s stages come from our corn growth stage model, which scales the stages to the hybrid’s rated GDD to black
        layer (physiological maturity).
        <a href={routes.model({ model_id: model.id })} class="text-brand-600 underline hover:text-brand-700">
          How the model works and its sources
        </a>
      </p>
    {/if}
    <p class="max-w-prose">
      The totals are from weather data for this location’s 2.5 km grid cell, which can differ from a field’s own. The
      freeze chance is the share of past years whose first fall freeze at the temperature you chose had come by each
      date. Alfalfa, counted from January 1 or the last cutting, has
      <a href={routes.toolAlfalfa()} class="text-brand-600 underline hover:text-brand-700">its own tool</a>.
    </p>
    <p class="text-sm">
      <a href={routes.toolDegreeDays()} class="text-brand-600 underline hover:text-brand-700">Degree-day calculator</a>
      {' · '}
      <a href={routes.toolFreeze()} class="text-brand-600 underline hover:text-brand-700">Freeze dates and odds</a>
      {' · '}
      <a href={routes.methods()} class="text-brand-600 underline hover:text-brand-700">How we make our weather data</a>
    </p>
  </section>
</div>
