<!-- "Open at a site" on a model's page: find a place (or pick one of your saved sites) and go to the model there -->
<script lang="ts">
  import { router } from '@inertiajs/svelte'

  import { routes } from '@/lib/routes'
  import { siteKey, siteModelUrl, type PickedPlace } from '@/lib/siteKey'
  import { siteLabel, sites } from '@/lib/sites.svelte'
  import FindPlace from '@/lib/sites/FindPlace.svelte'

  // feed: the model has risk levels, so "all your sites" (its feed) has something to compare
  let { modelId, feed = false }: { modelId: string; feed?: boolean } = $props()

  function go(place: PickedPlace) {
    const url = siteModelUrl(siteKey(place.lat, place.lng), modelId)
    router.visit(place.name ? `${url}?${new URLSearchParams({ name: place.name })}` : url)
  }
</script>

<div class="space-y-3">
  <FindPlace id="model-site-search" label="Find a place" placeholder="A town, address or coordinates" onpick={go} />
  {#if sites.length}
    <div class="text-sm">
      <p class="text-ink-muted">Or choose one of your sites:</p>
      <ul class="mt-1 flex flex-wrap gap-x-4 gap-y-1">
        {#each sites as site (site.key)}
          <li>
            <a href={siteModelUrl(site.key, modelId)} class="text-brand-600 underline hover:text-brand-700">
              {siteLabel(site)}
            </a>
          </li>
        {/each}
      </ul>
      {#if feed && sites.length > 1}
        <p class="mt-2">
          <a href={routes.sitesModelFeed({ model_id: modelId })} class="text-brand-600 underline hover:text-brand-700">
            {`See it at all ${sites.length} of your sites`}
          </a>
        </p>
      {/if}
    </div>
  {/if}
</div>
