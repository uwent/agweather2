<script lang="ts">
  import { page, useForm } from '@inertiajs/svelte'

  import type { ApiUseProps } from '@/types'

  // A minimal page (D112); Phase 7 designs it
  let { areas, frequencies, form_token }: ApiUseProps = $props()

  const form = useForm({
    name: '',
    organization: '',
    email: '',
    uses: '',
    areas: [] as string[],
    endpoints: '',
    frequency: '',
    notify: false,
    website: '', // left empty by people: the field is hidden from them (updates/forms.py)
  })

  const errors = $derived(page.props.errors as Record<string, string[] | undefined>)
  const described = (field: string) => (errors[field] ? `${field}-error` : undefined)

  function submit(event: SubmitEvent) {
    event.preventDefault()
    form
      .transform((data) => ({ ...data, form_token }))
      .post('/api-use', { preserveState: true, preserveScroll: true, onSuccess: () => form.reset() })
  }

  const input =
    'border-line bg-surface text-ink focus:border-brand-500 focus:ring-brand-500 mt-1 block w-full rounded-md text-sm'
</script>

<svelte:head>
  <title>Tell us how you use the API · AgWeather</title>
</svelte:head>

<section class="max-w-prose space-y-6">
  <header class="space-y-2">
    <h1 class="text-3xl font-semibold">Tell us how you use the API</h1>
    <p>
      We would like to know who uses the AgWeather API, what for, and what you would like it to do. Your answers help us
      decide what to add and how to make changes without disrupting your work.
    </p>
    <p class="text-sm text-ink-muted">
      We use your email address only to reply to you or, if you ask, to tell you before changes that affect the API. We
      don't share it. Past changes are on the
      <a href="/changelog" class="underline hover:text-ink">changelog page</a>.
    </p>
  </header>

  {#if errors.form}
    <p role="alert" class="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm">{errors.form[0]}</p>
  {/if}

  <form onsubmit={submit} class="space-y-5" novalidate>
    {#snippet error(field: string)}
      {#if errors[field]}
        <p id={`${field}-error`} class="mt-1 text-sm text-danger">{errors[field]?.join(' ')}</p>
      {/if}
    {/snippet}

    <div>
      <label for="name" class="text-sm font-medium">Your name</label>
      <input
        id="name"
        name="name"
        type="text"
        autocomplete="name"
        maxlength="200"
        required
        class={input}
        bind:value={form.name}
        aria-invalid={errors.name ? 'true' : undefined}
        aria-describedby={described('name')}
      />
      {@render error('name')}
    </div>

    <div>
      <label for="organization" class="text-sm font-medium">
        Organization <span class="text-ink-muted">(optional)</span>
      </label>
      <input
        id="organization"
        name="organization"
        type="text"
        autocomplete="organization"
        maxlength="200"
        class={input}
        bind:value={form.organization}
        aria-invalid={errors.organization ? 'true' : undefined}
        aria-describedby={described('organization')}
      />
      {@render error('organization')}
    </div>

    <div>
      <label for="email" class="text-sm font-medium">
        Email address <span class="text-ink-muted">(optional)</span>
      </label>
      <input
        id="email"
        name="email"
        type="email"
        autocomplete="email"
        maxlength="254"
        class={input}
        bind:value={form.email}
        aria-invalid={errors.email ? 'true' : undefined}
        aria-describedby={described('email')}
      />
      {@render error('email')}
    </div>

    <div>
      <label for="uses" class="text-sm font-medium">What do you use the API for?</label>
      <textarea
        id="uses"
        name="uses"
        rows="5"
        maxlength="5000"
        required
        class={input}
        bind:value={form.uses}
        aria-invalid={errors.uses ? 'true' : undefined}
        aria-describedby={described('uses')}></textarea>
      {@render error('uses')}
    </div>

    <fieldset aria-describedby={described('areas')}>
      <legend class="text-sm font-medium">
        Which parts of the API do you use? <span class="text-ink-muted">(optional)</span>
      </legend>
      <div class="mt-2 space-y-1">
        {#each areas as area (area)}
          <label class="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              name="areas"
              value={area}
              class="rounded-sm text-brand-600"
              bind:group={form.areas}
            />
            {area}
          </label>
        {/each}
      </div>
      {@render error('areas')}
    </fieldset>

    <div>
      <label for="endpoints" class="text-sm font-medium">
        Which endpoints do you use, and what would you like added? <span class="text-ink-muted">(optional)</span>
      </label>
      <textarea
        id="endpoints"
        name="endpoints"
        rows="3"
        maxlength="2000"
        class={input}
        bind:value={form.endpoints}
        aria-invalid={errors.endpoints ? 'true' : undefined}
        aria-describedby={described('endpoints')}></textarea>
      {@render error('endpoints')}
    </div>

    <div>
      <label for="frequency" class="text-sm font-medium">
        How often do you send requests? <span class="text-ink-muted">(optional)</span>
      </label>
      <select
        id="frequency"
        name="frequency"
        class={input}
        bind:value={form.frequency}
        aria-invalid={errors.frequency ? 'true' : undefined}
        aria-describedby={described('frequency')}
      >
        <option value="">Choose one</option>
        {#each frequencies as choice (choice.value)}
          <option value={choice.value}>{choice.label}</option>
        {/each}
      </select>
      {@render error('frequency')}
    </div>

    <label class="flex items-start gap-2 text-sm">
      <input type="checkbox" name="notify" class="mt-0.5 rounded-sm text-brand-600" bind:checked={form.notify} />
      Email me before changes that affect the API. This needs your email address above.
    </label>

    <!-- The honeypot: people never see or reach it, so anything typed here came from a program -->
    <div class="absolute left-[-10000px] size-px overflow-hidden" aria-hidden="true">
      <label for="website">Leave this field empty</label>
      <input id="website" name="website" type="text" tabindex="-1" autocomplete="off" bind:value={form.website} />
    </div>

    <button
      type="submit"
      disabled={form.processing}
      class="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-surface hover:bg-brand-700 disabled:opacity-60"
    >
      Send
    </button>
  </form>
</section>
