<script lang="ts" module>
  /** The share of open water from which a cell's normals get the note (Ben, 2026-11-26, track 6 Q8: a note on
   * lakeshore cells rather than defaulting to an area) */
  export const WATER_NOTE_PERCENT = 10
</script>

<script lang="ts">
  // The note on a grid cell that's partly open water (track 6.2): its weather, and so its normals, are partly the
  // lake's. Nothing for a cell under the share above, or where the share isn't known.
  let { percent }: { percent: number | null | undefined } = $props()
</script>

{#if percent !== null && percent !== undefined && percent >= WATER_NOTE_PERCENT}
  <p class="max-w-prose rounded-md border border-line bg-surface-raised px-3 py-2 text-sm" role="note">
    {percent >= 100
      ? 'This location’s 2.5 km grid cell is open water, so its normals are the water’s. Land nearby is likely to have warmer days, colder nights and earlier fall frosts.'
      : `About ${percent}% of this location’s 2.5 km grid cell is open water. Water warms and cools more slowly than land, so these normals can be milder than on the land nearby: cooler days, warmer nights and later fall frosts.`}
  </p>
{/if}
