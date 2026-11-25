<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/Sparkline.svelte -->
<script lang="ts">
  // A small line of recent values (a site card's last days), with optional reference lines (a
  // threshold, a zero); forecast values continue it dashed. Missing values (null) break the line
  // rather than drop to zero. WISP 3's drew allowable depletion with its irrigate line and field
  // capacity: here the lines are given.
  let {
    values,
    projected = [],
    max,
    min,
    label,
    lines = [],
    class: className = '',
  }: {
    values: (number | null)[]
    projected?: (number | null)[]
    max: number
    min: number
    label: string
    /** Reference lines: `danger` solid in the danger color, `muted` dashed in the rule color */
    lines?: { value: number; kind: 'danger' | 'muted' }[]
    class?: string
  } = $props()

  const width = 120
  const height = 32
  const count = $derived(values.length + projected.length)
  const y = (value: number) => height - 2 - ((value - min) / (max - min || 1)) * (height - 4)
  const x = (i: number) => (count < 2 ? width : (i / (count - 1)) * width)
  // A path through the points, lifting the pen over missing values
  const line = (points: [number, number | null][]) => {
    let path = ''
    let pen = false
    for (const [i, value] of points) {
      if (value === null || Number.isNaN(value)) {
        pen = false
        continue
      }
      path += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(value).toFixed(1)}`
      pen = true
    }
    return path
  }
  const path = $derived(line(values.map((value, i) => [i, value])))
  // From the last observed value on
  const ahead = $derived(
    projected.length && values.length
      ? line([
          [values.length - 1, values[values.length - 1]],
          ...projected.map((value, i): [number, number | null] => [values.length + i, value]),
        ])
      : '',
  )
</script>

<svg
  viewBox="0 0 {width} {height}"
  class="h-8 w-full {className}"
  role="img"
  aria-label={label}
  preserveAspectRatio="none"
>
  {#each lines as reference, index (index)}
    <line
      x1="0"
      x2={width}
      y1={y(reference.value)}
      y2={y(reference.value)}
      class={reference.kind === 'danger' ? 'stroke-danger' : 'stroke-line'}
      stroke-width="1"
      stroke-dasharray={reference.kind === 'muted' ? '3 3' : undefined}
      vector-effect="non-scaling-stroke"
    />
  {/each}
  {#if path}
    <path d={path} fill="none" class="stroke-brand-600" stroke-width="2" vector-effect="non-scaling-stroke" />
  {/if}
  {#if ahead}
    <path
      d={ahead}
      fill="none"
      class="stroke-brand-600"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      vector-effect="non-scaling-stroke"
    />
  {/if}
</svg>
