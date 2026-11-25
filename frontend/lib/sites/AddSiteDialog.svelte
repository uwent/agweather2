<!-- Add a site: find a place by name or type its coordinates, name it, save. -->
<script lang="ts">
  import Button from '@/lib/components/Button.svelte'
  import Dialog from '@/lib/components/Dialog.svelte'
  import TextField from '@/lib/components/TextField.svelte'
  import { addSite, type Site } from '@/lib/sites.svelte'
  import { formatCoords, roundCoord, type PickedPlace } from '@/lib/siteKey'
  import { parseNumber } from '@/lib/units'

  import FindPlace from './FindPlace.svelte'

  let { open = $bindable(false), onadded }: { open?: boolean; onadded?: (site: Site) => void } = $props()

  let name = $state('')
  let lat = $state('')
  let lng = $state('')
  let error = $state<string | null>(null)
  let errors = $state<{ lat?: string; lng?: string }>({})

  $effect(() => {
    if (open) {
      name = ''
      lat = ''
      lng = ''
      error = null
      errors = {}
    }
  })

  function picked(place: PickedPlace) {
    lat = String(roundCoord(place.lat))
    lng = String(roundCoord(place.lng))
    if (place.name) name = place.name
    errors = {}
  }

  function submit(event: SubmitEvent) {
    event.preventDefault()
    error = null
    const a = parseNumber(lat)
    const b = parseNumber(lng)
    errors = {
      lat:
        !a.ok || a.value === null || Math.abs(a.value) > 90
          ? 'Enter a latitude from -90 to 90 in decimal degrees, such as 43.07.'
          : undefined,
      lng:
        !b.ok || b.value === null || Math.abs(b.value) > 180
          ? 'Enter a longitude from -180 to 180 in decimal degrees, such as -89.40 (west is negative).'
          : undefined,
    }
    if (errors.lat || errors.lng || !a.ok || !b.ok) return
    const result = addSite({ lat: a.value!, lng: b.value!, name })
    if (!result.ok) {
      error = result.message
      return
    }
    open = false
    onadded?.(result.value)
  }

  const where = $derived.by(() => {
    const a = parseNumber(lat)
    const b = parseNumber(lng)
    return a.ok && b.ok && a.value !== null && b.value !== null && Math.abs(a.value) <= 90 && Math.abs(b.value) <= 180
      ? formatCoords(a.value, b.value)
      : null
  })
</script>

<Dialog bind:open title="Add a site" description="Find a place by name, or enter its latitude and longitude.">
  <div class="space-y-4">
    <FindPlace id="add-site-search" label="Find a place" onpick={picked} />
    <form class="space-y-4 border-t border-line pt-4" onsubmit={submit} novalidate>
      <TextField label="Name" name="name" bind:value={name} optional hint="Such as Home farm or North field." />
      <div class="grid grid-cols-2 gap-3">
        <TextField label="Latitude" name="lat" bind:value={lat} inputmode="decimal" error={errors.lat} required />
        <TextField label="Longitude" name="lng" bind:value={lng} inputmode="decimal" error={errors.lng} required />
      </div>
      {#if where}<p class="text-sm text-ink-muted">{where}</p>{/if}
      {#if error}<p class="text-sm text-danger-ink" role="alert">{error}</p>{/if}
      <div class="flex justify-end gap-3 border-t border-line pt-4">
        <Button variant="secondary" onclick={() => (open = false)}>Cancel</Button>
        <Button type="submit">Save site</Button>
      </div>
    </form>
  </div>
</Dialog>
