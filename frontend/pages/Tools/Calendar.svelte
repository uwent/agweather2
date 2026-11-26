<!-- The day-of-year calendar (track 5; v1's weather#doycal): converters between a date and its day of the year,
     and a year's days as a 31 × 12 table (two six-month tables on a phone), today ringed and named, a heavier rule
     every five rows, and a print layout of the table alone. Years 1900–2100; no data requests. -->
<script lang="ts">
  import { onDestroy } from 'svelte'

  import { today as gridToday } from '@/lib/dates'
  import {
    FIRST_YEAR,
    LAST_YEAR,
    MONTHS,
    calendarRows,
    dateOfDay,
    dayOfYear,
    daysInYear,
    leapNote,
    longDate,
  } from '@/lib/tools/calendar'
  import { codecs, field, viewState } from '@/lib/viewState'

  const today = gridToday()
  const thisYear = Number(today.slice(0, 4))
  const todayDoy = dayOfYear(today)

  const view = viewState({
    year: field(codecs.integer({ min: FIRST_YEAR, max: LAST_YEAR }), thisYear),
  })
  onDestroy(() => view.destroy())

  const year = $derived($view.year)
  const rows = $derived(calendarRows(year))
  const years = Array.from({ length: LAST_YEAR - FIRST_YEAR + 1 }, (_, k) => LAST_YEAR - k)
  const isToday = (doy: number | null) => year === thisYear && doy === todayDoy

  // Date to day of year
  let date = $state(today)
  const dateAnswer = $derived(
    /^\d{4}-\d{2}-\d{2}$/.test(date) && Number(date.slice(0, 4)) >= FIRST_YEAR && Number(date.slice(0, 4)) <= LAST_YEAR
      ? `${longDate(date)} is day ${dayOfYear(date)} of ${date.slice(0, 4)}.`
      : `Enter a date from January 1, ${FIRST_YEAR}, to December 31, ${LAST_YEAR}.`,
  )

  // Day of year to date, in the year shown
  let day = $state<number | null>(todayDoy)
  const dayAnswer = $derived.by(() => {
    const found = day === null ? null : dateOfDay(year, day)
    return found
      ? `Day ${day} of ${year} is ${longDate(found)}.`
      : `Enter a day from 1 to ${daysInYear(year)}: ${year} has ${daysInYear(year)} days.`
  })

  const halves = [
    { label: 'January to June', months: [0, 1, 2, 3, 4, 5] },
    { label: 'July to December', months: [6, 7, 8, 9, 10, 11] },
  ]
  const ALL = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
  const short = (m: number) => MONTHS[m].slice(0, 3)
  const button =
    'cursor-pointer rounded-md border border-line bg-surface px-3 py-1 text-sm hover:border-frame disabled:cursor-default disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-brand-600'
  const input = 'rounded-md border border-line bg-surface px-2 py-1 text-sm'
</script>

<svelte:head>
  <title>Day-of-year calendar · AgWeather</title>
</svelte:head>

{#snippet table(months: number[], caption: string, classes: string)}
  <table class="doy-table w-full border-collapse text-center text-sm tabular-nums {classes}">
    <caption class="mb-2 text-left text-base font-semibold">{caption}</caption>
    <thead>
      <tr class="border-b-2 border-frame">
        <th scope="col" class="p-1 text-left text-xs font-medium text-ink-muted">
          <abbr title="Day of the month" class="no-underline">Day</abbr>
        </th>
        {#each months as m (m)}
          <th scope="col" class="p-1 font-semibold">
            <abbr title={MONTHS[m]} class="no-underline">{short(m)}</abbr>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as row, d (d)}
        <tr class={(d + 1) % 5 === 0 && d < 30 ? 'border-b-2 border-frame' : 'border-b border-line/60'}>
          <th scope="row" class="px-1 py-0.5 text-left font-semibold">{d + 1}</th>
          {#each months as m (m)}
            {@const doy = row[m]}
            {#if doy === null}
              <td class="px-1 py-0.5"></td>
            {:else if isToday(doy)}
              <td class="px-1 py-0.5">
                <span
                  class="doy-today inline-block min-w-8 rounded-full px-1 font-bold ring-2 ring-brand-600"
                  title="Today"
                >
                  {doy}<span class="sr-only">{' (today)'}</span>
                </span>
              </td>
            {:else}
              <td class="px-1 py-0.5">{doy}</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
{/snippet}

<div id="doy-page" class="mx-auto max-w-5xl space-y-6">
  <div class="space-y-2">
    <h1 class="text-2xl font-semibold sm:text-3xl">Day-of-year calendar</h1>
    <p class="max-w-prose print:hidden">
      The day of the year numbers each day from 1 on January 1 to 365 on December 31, or 366 in a leap year. Some call
      it the Julian date. Models, research papers and field records often use it in place of the month and day.
    </p>
  </div>

  <section class="grid gap-4 sm:grid-cols-2 print:hidden" aria-labelledby="convert-h">
    <h2 id="convert-h" class="sr-only">Convert a date</h2>
    <div class="space-y-2 rounded-lg border border-line bg-surface-raised p-4">
      <label for="doy-date" class="block text-sm font-medium">Date to day of year</label>
      <input
        id="doy-date"
        type="date"
        class={input}
        min="{FIRST_YEAR}-01-01"
        max="{LAST_YEAR}-12-31"
        value={date}
        oninput={(event) => (date = event.currentTarget.value)}
      />
      <p class="text-sm" aria-live="polite">{dateAnswer}</p>
    </div>
    <div class="space-y-2 rounded-lg border border-line bg-surface-raised p-4">
      <label for="doy-day" class="block text-sm font-medium">{`Day of year to date, in ${year}`}</label>
      <input
        id="doy-day"
        type="number"
        inputmode="numeric"
        class="{input} w-28"
        min="1"
        max={daysInYear(year)}
        step="1"
        value={day ?? ''}
        oninput={(event) => {
          const value = event.currentTarget.valueAsNumber
          day = Number.isFinite(value) ? value : null
        }}
      />
      <p class="text-sm" aria-live="polite">{dayAnswer}</p>
    </div>
  </section>

  <section class="space-y-3" aria-labelledby="year-h">
    <div class="flex flex-wrap items-center gap-3 print:hidden">
      <h2 id="year-h" class="text-xl font-semibold">{`The days of ${year}`}</h2>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class={button}
          disabled={year <= FIRST_YEAR}
          onclick={() => view.patch({ year: year - 1 })}
        >
          Previous year
        </button>
        <label class="flex items-center gap-2 text-sm">
          <span class="sr-only">Year</span>
          <select
            class={input}
            value={String(year)}
            onchange={(event) => view.patch({ year: Number(event.currentTarget.value) })}
          >
            {#each years as y (y)}<option value={String(y)}>{y}</option>{/each}
          </select>
        </label>
        <button
          type="button"
          class={button}
          disabled={year >= LAST_YEAR}
          onclick={() => view.patch({ year: year + 1 })}
        >
          Next year
        </button>
      </div>
      {#if year !== thisYear}
        <button
          type="button"
          class="text-sm text-brand-600 underline hover:text-brand-700"
          onclick={() => view.patch({ year: thisYear })}
        >
          {`Back to ${thisYear}`}
        </button>
      {/if}
    </div>
    <p class="max-w-prose text-sm text-ink-muted print:hidden">
      Find the day of the month down the left side, then follow its row to the month’s column.
      {year === thisYear ? `Today, ${longDate(today)}, is day ${todayDoy}, ringed in the table.` : ''}
    </p>

    <!-- The whole year on wider screens and in print; two halves on a phone -->
    {@render table(ALL, `Day of the year, ${year}`, 'doy-full hidden sm:table print:table')}
    <div class="doy-halves space-y-6 sm:hidden print:hidden">
      {#each halves as half (half.label)}
        {@render table(half.months, `Day of the year, ${half.label} ${year}`, '')}
      {/each}
    </div>

    <p class="max-w-prose text-sm">{leapNote(year)}</p>
    <p class="text-sm print:hidden">
      To print this calendar, use your browser’s Print command: only the table and the leap-year note are printed.
    </p>
  </section>
</div>

<style>
  /* Printing: the whole year's table and the leap-year note alone, without the site's header, banners and footer,
     in black on white */
  @media print {
    :global(div:has(> main #doy-page) > :not(main)) {
      display: none !important;
    }
    :global(body:has(#doy-page)) {
      background: white;
      color: black;
    }
    #doy-page :global(.doy-full) {
      display: table !important;
      font-size: 10pt;
      color: black;
    }
    #doy-page :global(.doy-halves) {
      display: none !important;
    }
    #doy-page :global(.doy-today) {
      box-shadow: none;
    }
  }
</style>
