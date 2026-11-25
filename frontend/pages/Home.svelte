<!-- The home page (track 3 step 5): find a place, the month's headline maps, what's in season, your saved sites, links
     by task, and how current the data are. It makes no data requests of its own: the maps are the API's images, the
     rest props and this browser's saved sites. -->
<script lang="ts">
  import { Link, page, router } from '@inertiajs/svelte'

  import { dataThrough } from '@/lib/dataStatus'
  import { routes } from '@/lib/routes'
  import { siteKey, siteUrl, type PickedPlace } from '@/lib/siteKey'
  import { siteLabel, sites } from '@/lib/sites.svelte'
  import FindPlace from '@/lib/sites/FindPlace.svelte'
  import type { HomeProps } from '@/types'

  let { api_docs_url, maps, in_season }: HomeProps = $props()

  const through = $derived(dataThrough(page.props.status))

  function go(place: PickedPlace) {
    router.visit(siteUrl(siteKey(place.lat, place.lng), place.name || undefined))
  }

  const tasks = $derived([
    { href: '/map', title: 'Map', text: 'Weather, degree days and crop risk across the region, day by day.' },
    { href: routes.sites(), title: 'Your sites', text: 'Weather and risk at the fields and farms you follow.' },
    { href: '/models', title: 'Crop disease and insect models', text: 'What each model predicts and how it works.' },
    { href: '/tools/degree-days', title: 'Degree-day calculator', text: 'Growing degree days for a crop or pest.' },
    { href: '/data', title: 'Download data', text: 'Daily weather for a location or the whole region.' },
    { href: api_docs_url, title: 'API', text: 'The same data for your own programs and spreadsheets.' },
  ])

  const groupNames: Record<string, string> = {
    disease: 'disease',
    insect: 'insect',
    crop: 'growth stages',
    agronomic: 'field management',
  }
</script>

<svelte:head>
  <title>AgWeather</title>
</svelte:head>

<div class="space-y-10">
  <section class="space-y-4">
    <h1 class="text-3xl font-semibold">AgWeather</h1>
    <p class="max-w-prose text-lg">
      Weather, growing degree days, and crop disease and insect risk for farms and fields in the Upper Midwest, from
      University of Wisconsin–Madison Extension.
    </p>
    <FindPlace
      id="home-search"
      label="See the weather and crop risk for a place"
      placeholder="A town, address or coordinates, such as Hancock, WI"
      onpick={go}
    />
    {#if through}<p class="text-sm text-ink-muted">{through}.</p>{/if}
  </section>

  {#if sites.length}
    <section class="space-y-2" aria-labelledby="home-sites">
      <h2 id="home-sites" class="text-xl font-semibold">Your sites</h2>
      <ul class="flex flex-wrap gap-x-4 gap-y-1">
        {#each sites as site (site.key)}
          <li>
            <a href={siteUrl(site.key)} class="text-brand-600 underline hover:text-brand-700">{siteLabel(site)}</a>
          </li>
        {/each}
      </ul>
      <p class="text-sm">
        <Link href={routes.sites()} class="underline">See today’s weather and risk at all your sites</Link>
      </p>
    </section>
  {/if}

  <section class="space-y-3" aria-labelledby="home-maps">
    <h2 id="home-maps" class="text-xl font-semibold">Maps for this time of year</h2>
    <ul class="grid gap-4 md:grid-cols-3">
      {#each maps as map (map.layer)}
        <li>
          <a href={map.map_url} class="group block space-y-2">
            <img
              src={map.image_url}
              alt={map.alt}
              loading="lazy"
              width="640"
              class="h-auto w-full rounded-md border border-line bg-surface-raised"
            />
            <span class="block font-medium text-brand-600 underline group-hover:text-brand-700">{map.title}</span>
          </a>
        </li>
      {/each}
    </ul>
    <p class="text-sm text-ink-muted">Select a map to open it in the map explorer, where you can change the date.</p>
  </section>

  {#if in_season.length}
    <section class="space-y-3" aria-labelledby="home-season">
      <h2 id="home-season" class="text-xl font-semibold">Models in season now</h2>
      <p class="max-w-prose text-sm text-ink-muted">
        Crop disease, insect and growth models that apply at this time of year, by crop.
      </p>
      <div class="columns-1 gap-6 sm:columns-2 lg:columns-3">
        {#each in_season as crop (crop.crop)}
          <section class="mb-4 break-inside-avoid" aria-labelledby="season-{crop.crop}">
            <h3 id="season-{crop.crop}" class="font-medium">{crop.name}</h3>
            <ul class="text-sm">
              {#each crop.models as model (model.id)}
                <li>
                  <a href={model.url} class="underline hover:text-brand-700">{model.name}</a>
                  <span class="text-ink-muted">{` (${groupNames[model.group] ?? model.group})`}</span>
                </li>
              {/each}
            </ul>
          </section>
        {/each}
      </div>
    </section>
  {/if}

  <section class="space-y-3" aria-labelledby="home-tasks">
    <h2 id="home-tasks" class="text-xl font-semibold">What you can do here</h2>
    <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {#each tasks as task (task.href)}
        <li class="rounded-lg border border-line bg-surface-raised p-4">
          <a href={task.href} class="font-medium text-brand-600 underline hover:text-brand-700">{task.title}</a>
          <p class="text-sm text-ink-muted">{task.text}</p>
        </li>
      {/each}
    </ul>
  </section>

  <p class="text-xs text-ink-muted">Version {page.props.app.version} · {page.props.app.service_box}</p>
</div>
