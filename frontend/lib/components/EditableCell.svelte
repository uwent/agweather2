<!-- Ported from WISP 3: app/frontend/lib/components/EditableCell.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte'
  import { tick } from 'svelte'

  // A spreadsheet-style cell. Click, Enter or start typing to edit; Enter saves and moves down,
  // Tab saves and moves along the row, Escape cancels; arrow keys move between cells of the same
  // grid. A grid is one tab stop (the cell last focused, else its first), so Tab moves past it.
  // onsave gets the typed text and resolves with an error message, or null once saved. readOnly
  // shows the content as plain text, out of the grid and the tab order (time travel).
  let {
    text,
    label,
    grid,
    row,
    col,
    onsave,
    children,
    align = 'right',
    readOnly = false,
    class: className = '',
  }: {
    text: string
    label: string
    grid: string
    row: number
    col: number
    onsave: (text: string) => Promise<string | null>
    children: Snippet
    align?: 'left' | 'right'
    readOnly?: boolean
    class?: string
  } = $props()

  let editing = $state(false)
  let draft = $state('')
  let error = $state<string | null>(null)
  let saving = $state(false)
  let input: HTMLInputElement | undefined = $state()

  const cellAt = (r: number, c: number) =>
    document.querySelector<HTMLButtonElement>(`[data-grid="${grid}"][data-row="${r}"][data-col="${c}"]`)

  async function start(initial?: string) {
    draft = initial ?? text
    error = null
    editing = true
    await tick()
    input?.focus()
    if (initial === undefined) input?.select()
  }

  /** Where to go once an edit ends: the cell below opens for editing, the one beside is focused */
  type Move = { row: number; col: number; open: boolean }

  function go(move: Move) {
    const cell = cellAt(move.row, move.col)
    if (move.open) cell?.click()
    else cell?.focus()
  }

  async function commit(move?: Move) {
    // Chromium blurs an input as it's removed, so a cancelled or finished edit can arrive here too
    if (saving || !editing) return
    if (draft.trim() === text.trim()) {
      editing = false
      if (move) {
        await tick()
        go(move)
      }
      return
    }
    saving = true
    error = await onsave(draft)
    saving = false
    if (error) {
      input?.focus()
      return
    }
    editing = false
    if (move) {
      await tick()
      go(move)
    }
  }

  function onInputKey(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault()
      commit({ row: row + 1, col, open: true })
    } else if (event.key === 'Tab') {
      // Past the row's end, Tab leaves the grid as usual (and the blur saves)
      const next = col + (event.shiftKey ? -1 : 1)
      if (!cellAt(row, next)) return
      event.preventDefault()
      commit({ row, col: next, open: false })
    } else if (event.key === 'Escape') {
      event.preventDefault()
      editing = false
      error = null
      cellAt(row, col)?.focus()
    }
  }

  // Roving tab stop: a cell joins the tab order when it's focused, and the first cell mounted takes
  // it when no other cell of the grid has it (also after the cell holding it goes)
  const stopOf = () => document.querySelector(`button[data-grid="${grid}"][tabindex="0"]`)

  function rove(cell: HTMLButtonElement) {
    cell.tabIndex = stopOf() ? -1 : 0
    const take = () => {
      for (const other of document.querySelectorAll<HTMLButtonElement>(`button[data-grid="${grid}"]`))
        other.tabIndex = other === cell ? 0 : -1
    }
    cell.addEventListener('focus', take)
    return () => {
      cell.removeEventListener('focus', take)
      queueMicrotask(() => {
        const first = document.querySelector<HTMLButtonElement>(`button[data-grid="${grid}"]`)
        if (first && !stopOf()) first.tabIndex = 0
      })
    }
  }

  function onCellKey(event: KeyboardEvent) {
    const moves: Record<string, [number, number]> = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
    }
    const move = moves[event.key]
    if (move) {
      event.preventDefault()
      cellAt(row + move[0], col + move[1])?.focus()
    } else if (event.key === 'Enter' || event.key === 'F2') {
      event.preventDefault()
      start()
    } else if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault()
      start('')
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault()
      start(event.key)
    }
  }
</script>

{#if readOnly}
  <div class="block min-w-16 px-1.5 py-1 tabular-nums {align === 'right' ? 'text-right' : 'text-left'} {className}">
    {@render children()}
  </div>
{:else if editing}
  <!-- The cell's content stays in place, unseen, so the column keeps its width while the input
       covers it; otherwise the table shifts as an edit opens and closes, and a click meant for the
       next cell lands somewhere else -->
  <div class="relative">
    <span aria-hidden="true" class="invisible block min-w-16 px-1.5 py-1 tabular-nums">{@render children()}</span>
    <input
      bind:this={input}
      bind:value={draft}
      onkeydown={onInputKey}
      onblur={() => commit()}
      aria-label={label}
      aria-invalid={error ? 'true' : undefined}
      disabled={saving}
      class="absolute inset-0 size-full min-w-0 rounded-sm border-brand-500 px-1.5 py-0 text-sm tabular-nums focus:ring-brand-500
        {align === 'right' ? 'text-right' : 'text-left'}
        {error ? 'border-danger' : ''}"
    />
    {#if error}
      <p
        role="alert"
        class="absolute top-full right-0 z-10 mt-1 w-max max-w-56 rounded-sm bg-danger px-2 py-1 text-xs text-white shadow-sm"
      >
        {error}
      </p>
    {/if}
  </div>
{:else}
  <button
    type="button"
    data-grid={grid}
    data-row={row}
    data-col={col}
    {@attach rove}
    onclick={() => start()}
    onkeydown={onCellKey}
    class="relative block w-full min-w-16 rounded-sm px-1.5 py-1 tabular-nums hover:bg-brand-50
      {align === 'right' ? 'text-right' : 'text-left'}
      focus-visible:outline-2 focus-visible:outline-brand-500 {className}"
  >
    <!-- The label leads the button's name, which also carries what the cell shows (WCAG 2.5.3) -->
    <span class="sr-only">{label}:</span>
    {@render children()}
  </button>
{/if}
