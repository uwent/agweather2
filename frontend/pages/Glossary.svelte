<!-- The glossary (/glossary, track 7 step 7.4): every term in lib/glossary.ts A–Z, each at its own anchor (#id), which
     a term's popup in running text links to (Term.svelte), with a filter by words. -->
<script lang="ts">
  import SearchFilter from '@/lib/components/SearchFilter.svelte'
  import { filterGlossary, glossaryByLetter } from '@/lib/glossary'

  let query = $state('')

  const groups = $derived(glossaryByLetter(filterGlossary(query)))
  const count = $derived(groups.reduce((n, g) => n + g.entries.length, 0))
  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>Glossary · AgWeather</title>
  <meta
    name="description"
    content="The terms AgWeather uses for weather, crop growth, disease and insect models, explained in plain words."
  />
</svelte:head>

<div class="space-y-6">
  <header class="max-w-prose space-y-3">
    <h1 class="text-3xl font-semibold">Glossary</h1>
    <p class="text-lg">
      The terms AgWeather uses, explained in plain words. Where a term appears underlined with dots on another page, you
      can hover over or select it to read its definition there.
    </p>
  </header>

  <form
    class="max-w-prose rounded-lg border border-line bg-surface-raised p-4"
    role="search"
    aria-label="Filter the glossary"
    onsubmit={(event) => event.preventDefault()}
  >
    <span class="block text-sm font-medium" aria-hidden="true">Search</span>
    <div class="mt-1 [&_input]:w-full">
      <SearchFilter bind:value={query} placeholder="A term or a word in its definition" label="Search the glossary" />
    </div>
  </form>

  <p class="text-sm text-ink-muted" aria-live="polite">
    {count === 1 ? '1 term' : `${count} terms`}{query.trim() ? ' match.' : '.'}
    {#if query.trim()}
      <button type="button" class="ml-2 {link}" onclick={() => (query = '')}>Show all terms</button>
    {/if}
  </p>

  {#if groups.length === 0}
    <p>No terms match. Try fewer or other words.</p>
  {:else}
    <nav aria-label="Letters">
      <ul class="flex flex-wrap gap-x-3 gap-y-1 text-sm">
        {#each groups as group (group.letter)}
          <li><a href="#letter-{group.letter}" class={link}>{group.letter}</a></li>
        {/each}
      </ul>
    </nav>

    <div class="max-w-prose space-y-8">
      {#each groups as group (group.letter)}
        <section id="letter-{group.letter}" aria-labelledby="letter-{group.letter}-title" class="scroll-mt-24">
          <h2 id="letter-{group.letter}-title" class="border-b border-line pb-1 text-2xl font-semibold">
            {group.letter}
          </h2>
          <dl class="mt-3 space-y-4">
            {#each group.entries as entry (entry.id)}
              <div
                id={entry.id}
                class="-mx-2 scroll-mt-24 rounded-md p-2 target:bg-brand-50 target:outline-2 target:outline-brand-600"
              >
                <dt class="font-semibold">{entry.term}</dt>
                <dd class="mt-1">
                  {entry.definition}
                  {#if entry.more}
                    {' '}<a href={entry.more.href} class={link}>{entry.more.label}</a>.
                  {/if}
                </dd>
              </div>
            {/each}
          </dl>
        </section>
      {/each}
    </div>
  {/if}
</div>
