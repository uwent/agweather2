<script lang="ts">
  // The normals' period as a quick switch (30, 10 or 5 years, each labelled with its years): see ./periods.ts
  import SegmentedChoice from '../components/SegmentedChoice.svelte'
  import { NORMAL_PERIODS, periodOptions, type Period } from './periods'

  let {
    value,
    today,
    onchange,
    name = 'climate-period',
    periods = NORMAL_PERIODS,
  }: {
    value: Period
    /** ISO date: the years are the whole years before it */
    today: string
    onchange: (period: Period) => void
    /** The radios' name, unique on the page */
    name?: string
    periods?: readonly Period[]
  } = $props()
</script>

<SegmentedChoice legend="Normal from" {name} showLegend options={periodOptions(today, periods)} {value} {onchange} />
