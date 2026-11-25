<!-- Import sites from a CSV file (lib/sitesCsv): what was added and every row left out, in sentences -->
<script lang="ts">
  import Button from '@/lib/components/Button.svelte'
  import Dialog from '@/lib/components/Dialog.svelte'
  import { importSitesCsv, MAX_SITES, type ImportResult } from '@/lib/sites.svelte'

  let { open = $bindable(false) }: { open?: boolean } = $props()

  let result = $state<ImportResult | null>(null)
  let reading = $state(false)

  $effect(() => {
    if (open) result = null
  })

  async function chosen(event: Event) {
    const input = event.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    reading = true
    try {
      result = importSitesCsv(await file.text())
    } catch {
      result = {
        added: [],
        skipped: [],
        messages: ['We couldn’t read that file. Choose a CSV file saved from a spreadsheet.'],
        error: 'unreadable',
      }
    } finally {
      reading = false
      input.value = ''
    }
  }
</script>

<Dialog
  bind:open
  title="Import sites"
  description="Add sites from a CSV file, such as one exported from AgWeather or the Crop Risk Tool."
>
  <div class="space-y-4 text-sm">
    <p>
      The file’s first row names its columns: <code>name</code>, <code>lat</code> and <code>lng</code>, and optionally
      <code>groups</code> (group names separated by semicolons). Latitude and longitude are in decimal degrees, with
      west longitudes negative. You can save up to {MAX_SITES} sites.
    </p>
    <div>
      <label for="import-file" class="mb-1 block font-medium">CSV file</label>
      <input
        id="import-file"
        type="file"
        accept=".csv,text/csv"
        onchange={chosen}
        disabled={reading}
        class="block w-full text-sm file:mr-3 file:rounded-md file:border file:border-line file:bg-surface file:px-3 file:py-1.5 file:text-ink"
      />
    </div>
    {#if result}
      <div class="space-y-1 rounded-md border border-line bg-surface p-3" role="status">
        {#each result.messages as message, k (k)}
          <p class={k === 0 ? 'font-medium' : ''}>{message}</p>
        {/each}
      </div>
    {/if}
    <div class="flex justify-end border-t border-line pt-4">
      <Button variant="secondary" onclick={() => (open = false)}>{result ? 'Done' : 'Cancel'}</Button>
    </div>
  </div>
</Dialog>
