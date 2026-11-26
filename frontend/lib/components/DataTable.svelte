<!-- Ported from WISP 3: app/frontend/lib/components/DataTable.svelte -->
<script lang="ts" generics="T">
  import type { Snippet } from 'svelte'

  import { cellText, matchesQuery, sortRows, type Column, type SortDirection } from '../table'

  // A table that sorts by any column (click a heading; again to reverse) and filters rows by a
  // search box over the searchable columns. Cells show cellText unless a `cell` snippet renders them.
  // Too wide for its box, it scrolls sideways with its pinned columns (Column.pin) kept in view. A
  // heading's label can break onto two lines at a newline. With a maxHeight its box scrolls down too,
  // the headings kept in view; with a limit only that many of the matching rows are drawn (a file's
  // thousands of shapes), the status saying how many more a search would narrow.

  let {
    rows,
    columns,
    rowKey,
    label,
    searchPlaceholder = 'Search',
    sort = $bindable<{ key: string; direction: SortDirection } | null>(null),
    cell,
    rowClass,
    empty = 'Nothing to show yet.',
    nowrap = false,
    maxHeight,
    limit,
    actions,
    searchAlso,
    selected,
    showSelected = false,
    rowId,
  }: {
    rows: T[]
    columns: Column<T>[]
    rowKey: (row: T) => string | number
    /** The table's accessible name */
    label: string
    searchPlaceholder?: string
    sort?: { key: string; direction: SortDirection } | null
    cell?: Snippet<[T, Column<T>]>
    rowClass?: (row: T) => string
    empty?: string
    /** Cells keep to one line, so rows stay one line high and the table scrolls sideways instead */
    nowrap?: boolean
    /** A max height for the table's box (a CSS length), which then scrolls down with its headings in view */
    maxHeight?: string
    /** At most this many rows are drawn */
    limit?: number
    /** Beside the search (a button to expand the table) */
    actions?: Snippet
    /** More of a row's text for the search to find, beyond its searchable columns (ones not shown) */
    searchAlso?: (row: T) => string[]
    /** The row to highlight (the one chosen), across its pinned cells too */
    selected?: (row: T) => boolean
    /** The selected row is drawn first when the search or limit would leave it out (a shape picked on a map) */
    showSelected?: boolean
    /** An id for each row's element, to scroll to it */
    rowId?: (row: T) => string
  } = $props()

  let query = $state('')

  const searchable = $derived(columns.filter((column) => column.searchable))
  const filtered = $derived(
    query.trim()
      ? rows.filter((row) =>
          matchesQuery(query, [...searchable.map((column) => cellText(column, row)), ...(searchAlso?.(row) ?? [])]),
        )
      : rows,
  )
  const sortColumn = $derived(sort && columns.find((column) => column.key === sort!.key))
  const ordered = $derived(sortColumn && sort ? sortRows(filtered, sortColumn.value, sort.direction) : filtered)
  const limited = $derived(limit !== undefined && ordered.length > limit ? ordered.slice(0, limit) : ordered)
  const chosenRow = $derived(showSelected && selected ? rows.find(selected) : undefined)
  const shown = $derived(chosenRow && !limited.includes(chosenRow) ? [chosenRow, ...limited] : limited)
  const count = (n: number) => n.toLocaleString('en-US')
  const status = $derived(
    limited.length < ordered.length
      ? `Showing ${count(limited.length)} of ${count(ordered.length)}${query.trim() ? ` matching (${count(rows.length)} in all)` : ''}: search to narrow`
      : query.trim()
        ? `${count(limited.length)} of ${count(rows.length)} shown`
        : '',
  )

  function toggle(column: Column<T>) {
    const first = column.firstDirection ?? 'asc'
    sort =
      sort?.key === column.key
        ? { key: column.key, direction: sort.direction === 'asc' ? 'desc' : 'asc' }
        : { key: column.key, direction: first }
  }

  const alignClass = { left: 'text-left', right: 'text-right', center: 'text-center' }

  // Pinned columns: each left one's offset is the width of those pinned before it, measured from
  // the headings. The last left one and the right one draw a rule where the rest scroll under them.
  let widths = $state<Record<string, number>>({})
  const leftPinned = $derived(columns.filter((column) => column.pin === 'left'))
  const lastLeft = $derived(leftPinned.at(-1)?.key)
  function offset(column: Column<T>): number {
    let total = 0
    for (const other of leftPinned) {
      if (other.key === column.key) break
      total += widths[other.key] ?? 0
    }
    return total
  }
  // A pinned cell has its own background, to hide the cells scrolling under it: the row's, if chosen
  function pinClass(column: Column<T>, chosen = false): string {
    const bg = chosen ? 'bg-brand-50' : 'bg-surface-raised'
    if (column.pin === 'right') return `sticky right-0 z-10 ${bg} shadow-[inset_1px_0_0_var(--color-line)]`
    if (column.pin !== 'left') return ''
    return `sticky z-10 ${bg} ${column.key === lastLeft ? 'shadow-[inset_-1px_0_0_var(--color-line)]' : ''}`
  }
  // In a box that scrolls down, the headings stay at its top, over the pinned cells, with a rule below
  function headClass(column: Column<T>): string {
    if (!maxHeight) return pinClass(column)
    const rule =
      column.pin === 'right'
        ? 'right-0 shadow-[inset_1px_-1px_0_var(--color-line)]'
        : column.key === lastLeft
          ? 'shadow-[inset_-1px_-1px_0_var(--color-line)]'
          : 'shadow-[inset_0_-1px_0_var(--color-line)]'
    return `sticky top-0 bg-surface-raised ${column.pin ? 'z-30' : 'z-20'} ${rule}`
  }
  const pinStyle = (column: Column<T>) => (column.pin === 'left' ? `left: ${offset(column)}px` : undefined)
  const ariaSort = (column: Column<T>) =>
    sort?.key === column.key
      ? sort.direction === 'asc'
        ? 'ascending'
        : 'descending'
      : column.sortable === false
        ? undefined
        : 'none'
</script>

<div class="space-y-2">
  <div class="flex flex-wrap items-center justify-between gap-2">
    {#if searchable.length || searchAlso}
      <input
        type="search"
        bind:value={query}
        placeholder={searchPlaceholder}
        aria-label={searchPlaceholder}
        class="w-full max-w-xs rounded-md border-line bg-surface-raised shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm"
      />
    {/if}
    <span class="text-xs text-ink-muted" role="status">{status}</span>
    {#if actions}<div class="ml-auto">{@render actions()}</div>{/if}
  </div>

  <div
    class="rounded-lg border border-line bg-surface-raised {maxHeight ? 'overflow-auto' : 'overflow-x-auto'}"
    style={maxHeight ? `max-height: ${maxHeight}` : undefined}
  >
    <table class="w-full text-sm" aria-label={label}>
      <thead class="border-b border-line text-xs text-ink-muted">
        <tr>
          {#each columns as column (column.key)}
            {@const lines = column.label.split('\n')}
            <th
              scope="col"
              class="px-3 py-2 align-bottom font-medium whitespace-nowrap {alignClass[
                column.align ?? 'left'
              ]} {headClass(column)}"
              style={pinStyle(column)}
              aria-sort={ariaSort(column)}
              bind:offsetWidth={widths[column.key]}
            >
              {#if column.sortable === false}
                {column.label}
              {:else}
                <!-- The arrow hangs past the label, so the label lines up with the column's cells -->
                <button
                  type="button"
                  class="relative inline-block hover:text-ink {alignClass[column.align ?? 'left']}"
                  aria-label={lines.length > 1 ? lines.join(' ') : undefined}
                  onclick={() => toggle(column)}
                >
                  {#each lines as line, i (i)}{#if i}<br />{/if}{line}{/each}
                  <span
                    aria-hidden="true"
                    class="absolute bottom-0 left-full ml-0.5 {sort?.key === column.key ? 'text-ink' : 'opacity-0'}"
                  >
                    {sort?.key === column.key && sort.direction === 'desc' ? '▾' : '▴'}
                  </span>
                </button>
              {/if}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody class="divide-y divide-line">
        {#each shown as row (rowKey(row))}
          {@const chosen = selected?.(row) ?? false}
          <tr id={rowId?.(row)} class="{chosen ? 'bg-brand-50' : ''} {rowClass?.(row) ?? ''}">
            {#each columns as column (column.key)}
              <td
                class="px-3 py-2 {alignClass[column.align ?? 'left']} {nowrap && !column.wrap
                  ? 'whitespace-nowrap'
                  : ''} {pinClass(column, chosen)}"
                style={pinStyle(column)}
              >
                {#if cell}{@render cell(row, column)}{:else}{cellText(column, row)}{/if}
              </td>
            {/each}
          </tr>
        {:else}
          <tr>
            <td colspan={columns.length} class="px-3 py-6 text-center text-ink-muted">
              {query.trim() ? 'Nothing matches your search.' : empty}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
