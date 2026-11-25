<script lang="ts">
  import { forecastIndex, type RiskDay } from '../riskSpan'
  import { riskColor } from '../riskLevels'

  // A model's risk as a small strip of days, each colored by its level (lib/riskLevels), from two weeks back through
  // the forecast: a day without a level is left blank, a day out of season faded, the forecast shaded and today
  // marked with a tick. Its text alternative is `label` (the trend in words, lib/riskSpan's trendWords).
  let {
    days,
    levels,
    today,
    label,
    class: className = '',
  }: { days: RiskDay[]; levels: number; today: string; label: string; class?: string } = $props()

  const width = 120
  const height = 10
  const step = $derived(days.length ? width / days.length : width)
  const ahead = $derived(forecastIndex(days))
  const todayAt = $derived(days.findIndex((d) => d.date === today))
</script>

<svg
  viewBox="0 0 {width} {height + 2}"
  class="h-3 {className || 'w-full'}"
  role="img"
  aria-label={label}
  preserveAspectRatio="none"
>
  {#each days as day, i (day.date)}
    {#if day.level !== null}
      <rect
        x={i * step}
        y="1"
        width={step + 0.05}
        {height}
        style:fill={riskColor(day.level, levels)}
        opacity={day.inSeason === false ? 0.3 : 1}
      />
    {/if}
  {/each}
  {#if ahead >= 0}
    <rect x={ahead * step} y="0" width={width - ahead * step} height={height + 2} class="fill-ink" opacity="0.14" />
  {/if}
  {#if todayAt >= 0}
    <line
      x1={todayAt * step}
      x2={todayAt * step}
      y1="0"
      y2={height + 2}
      class="stroke-ink"
      stroke-width="1.5"
      vector-effect="non-scaling-stroke"
    />
  {/if}
</svg>
