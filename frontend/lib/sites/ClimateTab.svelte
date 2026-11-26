<script lang="ts">
  import type { LocateData } from '@/types/api'

  import FreezeOdds from '../climate/FreezeOdds.svelte'
  import LazySection from '../climate/LazySection.svelte'
  import MonthCounts from '../climate/MonthCounts.svelte'
  import Normals, { type NormalVariable } from '../climate/Normals.svelte'
  import PeriodChoice from '../climate/PeriodChoice.svelte'
  import type { Period } from '../climate/periods'
  import { climateSlots } from '../climate/slots'
  import TemperatureNormal from '../climate/TemperatureNormal.svelte'
  import ThisSeason from '../climate/ThisSeason.svelte'
  import WaterNote from '../climate/WaterNote.svelte'
  import GlossaryText from '../components/GlossaryText.svelte'

  export type ClimateView = {
    period: Period
    /** This season's degree days: a preset's id or a setting; empty for modified 50/86 °F */
    dd: string
    /** This season's start, null for January 1 */
    start: string | null
    /** The season, null for this year */
    year: number | null
    /** The month counted, 1–12 of this year; null for this month */
    month: number | null
    /** The variable the normals draw through the year */
    variable: NormalVariable
  }

  // A site's Climate tab (track 6.2): the place against its normals, a section at a time as it scrolls in, two
  // requests at a time (lib/climate/slots), each section one of lib/climate's, which `/climate` reuses with only a
  // location. The period applies to every section; each section's own settings are the page's view (`cperiod`,
  // `cdd`, `cstart`, `cyear`, `cmonth`, `cvar`).
  let {
    lat,
    lng,
    today,
    location,
    view,
    onchange,
  }: {
    lat: number
    lng: number
    /** The grid's today, ISO */
    today: string
    /** `/locate`'s answer: whether the point is inside the area normals cover, and its cell's open water */
    location: LocateData | null
    view: ClimateView
    onchange: (changes: Partial<ClimateView>) => void
  } = $props()

  const outside = $derived(location?.in_box === false)
  const common = $derived({ lat, lng, today, period: view.period, queue: climateSlots })
</script>

<div class="space-y-8">
  <div class="space-y-3">
    <GlossaryText
      class="max-w-prose text-sm text-ink-muted"
      paragraphs={[
        'A normal is what’s typical for a date at this location: each year’s value averaged over a period of past years, with a usual range between the 10th and 90th percentiles, which holds 8 years in 10. Compare this year with it, and see the odds of a freeze.',
      ]}
    />
    {#if !outside}
      <PeriodChoice value={view.period} {today} onchange={(period) => onchange({ period })} />
    {/if}
    <WaterNote percent={location?.water_percent} />
  </div>

  {#if outside}
    <p class="max-w-prose text-sm" role="status">
      Normals are available only inside the area we cover, and this location is outside it, so we can’t show its climate
      here.
    </p>
  {:else}
    <LazySection title="This season so far" id="climate-season">
      <ThisSeason
        {...common}
        dd={view.dd}
        start={view.start}
        year={view.year}
        onchange={(changes) => onchange(changes)}
      />
    </LazySection>
    <LazySection title="Temperature against normal" id="climate-temperature">
      <TemperatureNormal {...common} />
    </LazySection>
    <LazySection title="Frost and freeze" id="climate-freeze">
      <FreezeOdds {...common} thisYear={view.year ?? undefined} />
    </LazySection>
    <LazySection title="This month against normal" id="climate-month">
      <MonthCounts {...common} month={view.month} onchange={({ month }) => onchange({ month })} />
    </LazySection>
    <LazySection title="Normals" id="climate-normals">
      <Normals {...common} variable={view.variable} onchange={({ variable }) => onchange({ variable })} />
    </LazySection>
  {/if}
</div>
