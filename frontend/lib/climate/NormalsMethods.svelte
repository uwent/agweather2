<!-- How normals are made (/methods#normals, Phase 7 track 6 step 6.5): generated from the code (`normals` of the
     methods page's props, the same as /api/v2/methods serves: agdata.climatology, normals, climatestore, springfreeze
     and seasonopens), so every number here is the code's. The climate pages' "How normals are made" links come here
     (`normalsHref`). -->
<script lang="ts">
  import Term from '@/lib/components/Term.svelte'
  import {
    countText,
    dailyWords,
    degreeDaysText,
    kmText,
    settingText,
    totalText,
    yearCount,
    yearsText,
  } from '@/lib/methods'
  import { andList, longDate, monthDay } from '@/lib/models/format'
  import { routes } from '@/lib/routes'
  import { currentUnits } from '@/lib/units'
  import type { MethodsVariable, NormalsInfo, NormalsSeasonOpeningInfo } from '@/types'

  import { ordinal, shareOfYears, thresholdLabel, thresholdsInWords } from './words'

  let {
    normals,
    variables,
    cellKm,
  }: {
    normals: NormalsInfo
    /** The catalog, for the names of variables the words don't know */
    variables: MethodsVariable[]
    /** A grid cell's width, km */
    cellKm: number
  } = $props()

  const units = $derived(currentUnits())
  const n = $derived(normals)
  const longNames = $derived(new Map(variables.map((v) => [`${v.kind}:${v.name}`, v.long_name])))
  const daily = (name: string) => dailyWords(name, longNames.get(`daily:${name}`))
  const total = (name: string) => totalText(name, units, longNames.get(`cumulative:${name}`))
  const periodLength = (period: string) => Number(period.replace(/\D/g, ''))

  const longest = $derived(n.periods[0])
  const shortest = $derived(n.periods[n.periods.length - 1])
  const atLocationsOnly = $derived(n.periods.filter((p) => !p.maps))
  const shorter = $derived(n.periods.slice(1).filter((p) => p.maps))
  const firstArchive = $derived(Math.min(...n.periods.flatMap((p) => p.archive_years)))
  const withGridmet = $derived(n.periods.find((p) => p.gridmet_years.length))

  const g = $derived(n.gridmet)
  const added = $derived(g.adjust.filter((a) => a.kind === 'add').map((a) => daily(a.variable)))
  const ratios = $derived(g.adjust.filter((a) => a.kind === 'ratio').map((a) => daily(a.variable)))
  // gridMET's values left out, grouped by their years: "daily high and daily reference evapotranspiration for 2011–2013"
  const leftOut = $derived.by(() => {
    const byYears: Record<string, string[]> = {}
    for (const l of g.left_out) {
      const years = yearsText(l.years)
      byYears[years] = [...(byYears[years] ?? []), daily(l.variable).replace(/^the /, '')]
    }
    return andList(Object.entries(byYears).map(([years, names]) => `${andList(names)} for ${years}`))
  })
  const decilePeriods = $derived(n.decile_periods.map(periodLength).sort((a, b) => b - a))
  const orList = (items: string[]) => andList(items).replace(/ and ([^ ]+)$/, ' or $1')
  const capitalized = (text: string) => text.replace(/^1 /, 'One ').replace(/^./, (c) => c.toUpperCase())

  const [low, high] = $derived([n.daily_percentiles[0], n.daily_percentiles[n.daily_percentiles.length - 1]])
  const f = $derived(n.freeze)
  const [early, late] = $derived([f.percentiles[0], f.percentiles[f.percentiles.length - 1]])

  const leads = $derived([...new Set(n.season_opens.filter((o) => o.rule === 'degree_days').map((o) => o.lead_days))])
  const leadText = $derived(leads.length === 1 ? `${leads[0] === 7 ? 'A week' : `${leads[0]} days`}` : 'A few days')

  function offsetText(days: number): string {
    if (days === 0) return 'on the day of it'
    const k = Math.abs(days)
    return `${k} day${k === 1 ? '' : 's'} ${days < 0 ? 'before' : 'after'} it`
  }

  function opensText(o: NormalsSeasonOpeningInfo): string {
    if (o.rule === 'degree_days')
      return `${o.lead_days} day${o.lead_days === 1 ? '' : 's'} before ${o.event ?? 'its first activity'}`
    if (o.rule === 'crop_stage') return `When ${o.event}`
    return `On ${monthDay(o.first_day)}`
  }

  function countedText(o: NormalsSeasonOpeningInfo): string {
    if (o.degree_days === null || o.method === null || o.base === null) return 'A fixed date'
    const setting = settingText(o.method, o.base, o.upper, units)
    if (o.rule === 'crop_stage') {
      const from = o.planting ? `the ${o.planting} planting date` : 'January 1'
      return `${degreeDaysText(o.degree_days, units)} (${o.crop_model_name}: ${setting}) from ${from}`
    }
    const main = `${degreeDaysText(o.degree_days, units)} (${setting}) from ${monthDay(o.start ?? '01-01')}`
    if (o.form_degree_days === null || o.form_below === null || o.form_through === null) return main
    return `${main}; ${degreeDaysText(o.form_degree_days, units)} where the normal from January 1 through ${monthDay(o.form_through)} is below ${degreeDaysText(o.form_below, units)}`
  }

  const link = 'text-brand-600 underline hover:text-brand-700'
  const cell = 'px-3 py-2 align-top'
</script>

<section id="normals" aria-labelledby="normals-title" class="scroll-mt-24 space-y-6">
  <h2 id="normals-title" class="text-2xl font-semibold">How normals are made</h2>
  <p>
    {'A '}<Term id="normal">
      normal
    </Term>{` is the usual weather for a place and time of year. We compute every normal from each location’s own past years on our grid, so a normal describes the same grid cell as the weather it is compared with. Maps, a location’s Climate tab and the freeze tool all use the normals described here.`}
  </p>

  <section id="normals-periods" aria-labelledby="normals-periods-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-periods-title" class="text-xl font-semibold">The periods</h3>
    <p>
      {`A period is the whole years before this one, so it moves on a year each January. Normals cover the last ${periodLength(longest.period)} years unless you choose ${shorter.length ? `the last ${orList(shorter.map((p) => String(periodLength(p.period))))}` : 'fewer'}, which follow recent change more closely, though one unusual year then counts for more.`}
      {#if atLocationsOnly.length}
        {` The ${andList(atLocationsOnly.map((p) => `${periodLength(p.period)}-year`))} period${atLocationsOnly.length > 1 ? 's are' : ' is'} available only for a location, through the API, not as maps.`}
      {/if}
    </p>
    <div class="overflow-x-auto">
      <table class="w-full min-w-120 text-left text-sm">
        <caption class="sr-only">The periods normals cover and where their years come from</caption>
        <thead class="border-b border-line">
          <tr>
            <th scope="col" class="sticky left-0 bg-surface {cell}">Period</th>
            <th scope="col" class={cell}>Years</th>
            <th scope="col" class={cell}>From our archive</th>
            <th scope="col" class={cell}>From gridMET</th>
            <th scope="col" class={cell}>Maps</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          {#each n.periods as p (p.period)}
            <tr>
              <th scope="row" class="sticky left-0 bg-surface font-medium {cell}">
                {`Last ${periodLength(p.period)} years`}
              </th>
              <td class={cell}>{`${p.first_year}–${p.last_year}`}</td>
              <td class={cell}>{p.archive_years.length ? yearsText(p.archive_years) : 'None'}</td>
              <td class={cell}>{p.gridmet_years.length ? yearsText(p.gridmet_years) : 'None'}</td>
              <td class={cell}>{p.maps ? 'Yes' : 'No'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#each n.periods.filter((p) => p.missing_years.length) as p (p.period)}
      <p class="text-sm text-ink-muted">
        {`We don’t yet have ${yearCount(p.missing_years.length)} of the last ${periodLength(p.period)} (${yearsText(p.missing_years)}), so that period’s normals come from the other ${p.archive_years.length + p.gridmet_years.length}.`}
      </p>
    {/each}
  </section>

  <section id="normals-gridmet" aria-labelledby="normals-gridmet-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-gridmet-title" class="text-xl font-semibold">The earlier years, from gridMET</h3>
    <p>
      {withGridmet && Number.isFinite(firstArchive)
        ? `Our archive begins in ${firstArchive}, so the last ${periodLength(withGridmet.period)} years take ${yearsText(withGridmet.gridmet_years)} from gridMET, a gridded daily weather dataset, and the years since from our archive.`
        : 'Where a period reaches back before our archive, it takes those years from gridMET, a gridded daily weather dataset.'}
      {` The two sources differ, so we adjust gridMET to our archive for each grid cell and day of the year, fitted on the years both have${g.fit_years.length ? ` (${yearsText(g.fit_years)})` : ''}${g.fitted ? `, most recently on ${longDate(g.fitted)}` : ''}:`}
    </p>
    <ul class="list-disc space-y-1 pl-6">
      {#if added.length}
        <li>
          {`For ${andList(added)}, we add the average difference between the two sources over the ${g.pool_days} days centered on each date.`}
        </li>
      {/if}
      {#if ratios.length}
        <li>
          {`For ${andList(ratios)}, we multiply by the ratio of the two sources’ totals over the same days, kept between ${g.ratio_limits[0]} and ${g.ratio_limits[1]}.`}
        </li>
      {/if}
      <li>
        {`Each adjustment is then averaged over the ${g.smooth_cells} × ${g.smooth_cells} cells around it, a square ${kmText(g.smooth_cells * cellKm)} on a side, so it reflects the area rather than one cell’s chance differences.`}
      </li>
      {#if g.left_out.length}
        <li>
          {`We leave out gridMET’s ${leftOut}, which we found wrong against weather stations; normals of those take the period’s other years.`}
        </li>
      {/if}
    </ul>
    <p>
      {'Our corrections describe '}<a href="#correction-{g.correction}" class={link}>
        this adjustment
      </a>{', with the technical reports on what we found.'}
    </p>
  </section>

  <section id="normals-daily" aria-labelledby="normals-daily-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-daily-title" class="text-xl font-semibold">Daily normals</h3>
    <p>
      {`A day’s normal, such as the normal high on June 15, pools every year’s values for the ${n.pool_days} days centered on it, wrapping from December 31 to January 1: ${(n.pool_days * periodLength(longest.period)).toLocaleString('en-US')} values over ${periodLength(longest.period)} years, ${n.pool_days * periodLength(shortest.period)} over ${periodLength(shortest.period)}. One date’s values alone would make a normal that jumps from day to day; pooling keeps it steady. A day’s normal needs ${Math.round(n.coverage * 100)}% of the values it could have, or it is missing.`}
    </p>
    <p>
      {`For ${andList(n.daily_percentile_variables.map(daily))}, we also keep the ${ordinal(low)} and ${ordinal(high)} `}<Term
        id="percentile"
      >
        percentiles
      </Term>{` of the pooled values, the usual range: ${shareOfYears(high - low)
        .replace('years', 'days')
        .replace('year', 'day')} fall within it.`}
    </p>
  </section>

  <section id="normals-totals" aria-labelledby="normals-totals-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-totals-title" class="text-xl font-semibold">Totals, percentiles and departures</h3>
    <p>
      {`A normal total, such as `}<Term id="growing_degree_days">
        degree days
      </Term>{` or precipitation since January 1, is each year’s own total to the date, averaged over the years. It is never a total of normal days: thirty real springs give other degree days than one average spring does. A year’s total counts while it has missed no more than ${n.running_max_missing} days, and a normal needs ${Math.round(n.coverage * 100)}% of the period’s years.`}
    </p>
    <p>
      {`A `}<Term id="percentile">
        percentile
      </Term>{` ranks this year’s total among the years’ own totals to the same date. Maps keep every 10th percentile of ${andList(n.decile_variables.map(total))}, over the last ${andList(decilePeriods.map(String))} years, and a percentile map reads between them. At a location, any percentile is computed from the years themselves.`}
    </p>
    <p>
      {`A `}<Term id="departure">
        departure from normal
      </Term>{` is a value less its normal for the same days: a map of the last week’s rain against normal subtracts the normal total for that week.`}
    </p>
  </section>

  <section id="normals-counts" aria-labelledby="normals-counts-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-counts-title" class="text-xl font-semibold">Counts of days</h3>
    <p>
      {`A normal count of days, such as hot days or dry days, is counted in each year and then averaged, as a total is. Maps keep the counts below as running counts from January 1, so the normal count for any span of days is a subtraction. At a location, the API counts days within any bounds you choose.`}
    </p>
    <ul class="list-disc space-y-1 pl-6">
      {#each n.counts as c, k (k)}
        <li>{countText(c, units)}</li>
      {/each}
    </ul>
  </section>

  <section id="normals-freeze" aria-labelledby="normals-freeze-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-freeze-title" class="text-xl font-semibold">Freeze dates and their chances</h3>
    <p>
      {`For each year we find the last spring freeze, the last day from ${monthDay(f.spring[0])} through ${monthDay(f.spring[1])} with a low at or below the temperature, and the first fall freeze, the first such day from ${monthDay(f.fall[0])} through ${monthDay(f.fall[1])}. Then we compare those dates across the years. The typical date is the median: half the years had their freeze earlier. ${capitalized(shareOfYears(early))} had it before the ${ordinal(early)} percentile’s date, and ${shareOfYears(100 - late)} after the ${ordinal(late)} percentile’s.`}
    </p>
    <p>
      {`The chance of a freeze after a spring date is the share of years whose last spring freeze came after it; the chance by a fall date is the share whose first fall freeze came by it. Both count each year’s own dates rather than adding up each night’s chance of a freeze, which would treat cold nights as if they were unrelated. A year with no freeze in a season counts as having none, and a season missing more than ${Math.round(f.max_missing_share * 100)}% of its days is left out. The `}<Term
        id="frost_free_season"
      >
        frost-free season
      </Term>{`’s length is each year’s own, from its last spring freeze to its first fall freeze, and its typical length is the median of those.`}
    </p>
    <p>
      {`Maps keep ${thresholdsInWords(f.thresholds, units)}. At a location, the `}<a
        href={routes.toolFreeze()}
        class={link}
      >
        freeze tool
      </a>{' and the API take any temperature.'}
    </p>
  </section>

  <section id="normals-area" aria-labelledby="normals-area-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-area-title" class="text-xl font-semibold">Averages over an area</h3>
    <p>
      {`Some dates should describe an area rather than one cell: a cell in low ground or by a bog can freeze two or three weeks later than the farms a few miles away. For typical planting dates and insect seasons, we average each cell’s ${periodLength(n.area.period)}-year normal over the cells within ${kmText(n.area.radius_km)}, weighted along a bell curve with a standard deviation of ${n.area.sigma_km} km, so the nearest cells count most. Open water and cells without a value are left out.`}
    </p>
    <p>
      {`Our `}<Term id="planting_tiers">
        typical potato planting dates
      </Term>{` follow the area’s median last spring ${thresholdLabel(n.area.planting_freeze, units).replace(/^./, (c) => c.toLowerCase())}: early planting ${offsetText(n.area.planting_offsets.early ?? 0)}, mid ${offsetText(n.area.planting_offsets.mid ?? 0)} and late ${offsetText(n.area.planting_offsets.late ?? 0)}.`}
    </p>
  </section>

  <section id="normals-insects" aria-labelledby="normals-insects-title" class="scroll-mt-24 space-y-3">
    <h3 id="normals-insects-title" class="text-xl font-semibold">When insect seasons open</h3>
    <p>
      An insect’s models show its activity and risk only in its season, which opens at each location by one of three
      rules:
    </p>
    <ul class="list-disc space-y-1 pl-6">
      <li>
        {`On degree days: ${leadText.toLowerCase()} before the day the area’s ${periodLength(n.area.period)}-year normal degree days, counted with the insect’s own method and thresholds, reach its first activity.`}
      </li>
      <li>
        On its crop: the day its crop typically reaches a stage, from the crop model’s degree days on the same normal.
      </li>
      <li>On a fixed date, for insects that arrive on the wind from the south each year.</li>
    </ul>
    <p>
      {`Where we don’t have the normal for a location, every season opens on its fixed date. For the region as a whole, as in the home page’s list and a map’s notes, a season opens on the day it has opened on ${n.region_percentile}% of the area’s cropland.`}
    </p>
    <div class="overflow-x-auto">
      <table class="w-full min-w-xl text-left text-sm">
        <caption class="sr-only">When each insect’s season opens</caption>
        <thead class="border-b border-line">
          <tr>
            <th scope="col" class="sticky left-0 bg-surface {cell}">Insect</th>
            <th scope="col" class={cell}>Season opens</th>
            <th scope="col" class={cell}>Counted as</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          {#each n.season_opens as o (o.model)}
            <tr>
              <th scope="row" class="sticky left-0 bg-surface font-medium {cell}">
                <a href={routes.model({ model_id: o.model })} class={link}>{o.name}</a>
              </th>
              <td class={cell}>{opensText(o)}</td>
              <td class={cell}>{countedText(o)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  {#if n.evidence.length}
    <p class="text-sm text-ink-muted">
      {'Our technical reports on the normals, with the checks against weather stations: '}{#each n.evidence as url, i (url)}{i
          ? ' · '
          : ''}<a href={url} class={link}>
          {n.evidence.length > 1 ? `Technical report ${i + 1}` : 'Technical report'}
        </a>{/each}.
    </p>
  {/if}
</section>
