<script lang="ts">
  import ChartCard from '../charts/ChartCard.svelte'
  import { compareOption, compareRows, compareSummary, type CompareTable } from '../charts/climateCharts'
  import { downloadCsv, toCsv } from '../csv'
  import { currentUnits } from '../units'
  import { periodWords } from './periods'

  // This year's running total of one measure against the normal (track 6.1): the answer's sentence first, then the
  // chart (this year through the forecast, the normal dashed over its usual range, last year). The caller asks
  // `/climate/compare` once for every measure it shows (`compareTable`) and gives each chart its column, so a
  // section with degree days and precipitation makes one request.
  let {
    table,
    column,
    label,
    today,
    title,
    lastYear = true,
    filename,
  }: {
    table: CompareTable
    /** The total's column stem: `precipitation_sum`, `dd_modified_50_86`, `air_temperature_max_days_above_90` */
    column: string
    /** What's totalled, at the start of a sentence: "Precipitation", "Degree days (modified, 50–86 °F)" */
    label: string
    /** The grid's today, ISO */
    today: string
    title: string
    lastYear?: boolean
    /** A CSV download's name, without the extension; no download without it */
    filename?: string
  } = $props()

  const units = $derived(currentUnits())
  const summary = $derived(compareSummary({ table, column, units, label }))
  const normal = $derived(table.years ? `the normal over ${periodWords(table.years)}` : 'the normal')
  const info = $derived(
    `The solid line is this year’s total from the first day shown, observed and then forecast (shaded). The dashed line is ${normal}: each year’s own total to the date, averaged. The shaded band is its usual range, between the 10th and 90th percentiles of those years, which holds 8 years in 10. ${lastYear ? 'The thin line is last year’s total.' : ''}`.trim(),
  )

  function download() {
    const rows = compareRows(table, column, units)
    downloadCsv(
      `${filename}.csv`,
      toCsv([['date', ...rows.columns], ...rows.rows.toReversed().map((r) => [r.date, ...r.values])]),
    )
  }
</script>

<div class="space-y-2">
  <p class="max-w-prose text-sm">{summary}</p>
  <ChartCard
    {title}
    {info}
    height="20rem"
    build={(palette) => compareOption({ table, column, units, palette, today, label, lastYear })}
    {summary}
    table={() => compareRows(table, column, units)}
    download={filename ? download : undefined}
  />
</div>
