<!-- WISP 3: app/frontend/lib/charts/DataDialog.svelte (copied) -->
<script lang="ts">
  import Dialog from '../components/Dialog.svelte'
  import { formatDate } from '../dates'
  import type { ChartTable } from './ChartCard.svelte'
  import { tableTsv } from './weatherCharts'

  // A chart's (or every chart's) numbers in a dialog (Ben, 2026-11-17): its summary in words, a way
  // to download them (a button building the CSV, or a link to the server's), Copy to paste them into
  // a spreadsheet, and the table, newest first, scrolling both ways with its dates kept in view.
  // The table is built only while open.
  let {
    open = $bindable(false),
    title,
    name,
    label,
    summary,
    table,
    download,
    downloadHref,
    widest = false,
  }: {
    open?: boolean
    title: string
    /** What the data is, for labels: "the Precipitation data" */
    name: string
    /** The table's name, before "by day": "Precipitation" */
    label: string
    summary?: string
    table: () => ChartTable
    download?: () => void
    downloadHref?: string
    widest?: boolean
  } = $props()

  const rows = $derived(open ? table() : null)

  let copied = $state<'yes' | 'failed' | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  async function copy() {
    if (!rows) return
    try {
      await navigator.clipboard.writeText(tableTsv(rows))
      copied = 'yes'
    } catch {
      copied = 'failed'
    }
    clearTimeout(timer)
    timer = setTimeout(() => (copied = null), 3000)
  }
  const action = 'cursor-pointer text-brand-600 hover:underline'
</script>

<Dialog bind:open {title} wide {widest}>
  <div class="space-y-3 text-sm">
    {#if summary}<p class="text-ink-muted">{summary}</p>{/if}
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
      {#if downloadHref}
        <a href={downloadHref} class={action} aria-label="Download CSV of {name}" download>Download CSV</a>
      {:else if download}
        <button type="button" class={action} aria-label="Download CSV of {name}" onclick={download}>
          Download CSV
        </button>
      {/if}
      <button type="button" class={action} aria-label="Copy to clipboard: {name}" onclick={copy}>
        Copy to clipboard
      </button>
      <span class="text-xs text-ink-muted" role="status">
        {copied === 'yes'
          ? 'Copied: paste it into a spreadsheet.'
          : copied === 'failed'
            ? "This browser didn't allow copying."
            : ''}
      </span>
    </div>
    {#if rows}
      <!-- Focusable so keyboard users can scroll it (WCAG 2.1.1) -->
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div
        class="max-h-[60dvh] overflow-auto rounded-sm border border-line text-xs"
        tabindex="0"
        role="region"
        aria-label="{label} by day"
      >
        <table class="w-full tabular-nums">
          <caption class="sr-only">{label} by day, newest first</caption>
          <thead class="sticky top-0 z-10 bg-surface-raised text-ink-muted">
            <tr class="text-right">
              <th scope="col" class="sticky left-0 bg-surface-raised px-2 py-1 text-left font-medium">Date</th>
              {#each rows.columns as column (column)}
                <th scope="col" class="px-2 py-1 font-medium">{column}</th>
              {/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            {#each rows.rows as row (row.date)}
              <tr class="text-right {row.forecast ? 'bg-surface text-ink-muted' : ''}">
                <th
                  scope="row"
                  class="sticky left-0 px-2 py-0.5 text-left font-normal whitespace-nowrap {row.forecast
                    ? 'bg-surface'
                    : 'bg-surface-raised'}"
                >
                  {formatDate(row.date, { weekday: true })}{row.forecast ? ' (forecast)' : ''}
                </th>
                {#each row.values as value, i (i)}
                  <td class="px-2 py-0.5">{value ?? '–'}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</Dialog>
