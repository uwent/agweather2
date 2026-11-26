<script lang="ts">
  import Dialog from '@/lib/components/Dialog.svelte'
  import InfoTip from '@/lib/components/InfoTip.svelte'
  import SegmentedChoice from '@/lib/components/SegmentedChoice.svelte'
  import { fieldInfo } from '@/lib/fieldInfo'
  import { currentUnits, type UnitSystem } from '@/lib/units'
  import { setUnitSystem, unitSystem } from '@/lib/unitSystem.svelte'

  // The header's settings (F10): the units every page shows, kept in this browser until accounts
  // hold them. A choice applies at once, so the page behind changes without a visit.
  let { open = $bindable(false) }: { open?: boolean } = $props()

  const tip = $derived(fieldInfo('settings.units', currentUnits()))
  const options: { value: UnitSystem; label: string }[] = [
    { value: 'imperial', label: 'US (°F, inches)' },
    { value: 'metric', label: 'Metric (°C, millimeters)' },
  ]
</script>

<Dialog bind:open title="Settings" description="Saved in this browser.">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <span class="flex items-center gap-1 text-sm font-medium">
      Units
      <InfoTip text={tip.text} label="About units" />
    </span>
    <SegmentedChoice
      legend="Units"
      name="unit_system"
      {options}
      value={unitSystem()}
      onchange={(system) => setUnitSystem(system)}
    />
  </div>
</Dialog>
