<!-- "Tell us how you use the API" (/api-use, D112; designed in Phase 7 step 7.3): a short form for the API's users,
     who have no accounts. On success the form gives way to a thank-you with what happens next. -->
<script lang="ts">
  import { Link, page, useForm } from '@inertiajs/svelte'

  import Button from '@/lib/components/Button.svelte'
  import { routes } from '@/lib/routes'
  import type { ApiUseProps } from '@/types'

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
  // A field's error replaces its hint, so only the one shown is referenced
  const described = (field: string, hint = false) =>
    errors[field] ? `${field}-error` : hint ? `${field}-hint` : undefined

  let sent = $state<{ notify: boolean; email: string } | null>(null)
  let heading = $state<HTMLElement | null>(null)

  function submit(event: SubmitEvent) {
    event.preventDefault()
    const asked = { notify: form.notify, email: form.email }
    form
      .transform((data) => ({ ...data, form_token }))
      .post(routes.apiUse(), {
        preserveState: true,
        preserveScroll: true,
        onSuccess: () => {
          // A refusal comes back as errors on the same page; only a clean answer is a success
          if (Object.keys(page.props.errors ?? {}).length) return
          sent = asked
          form.reset()
          queueMicrotask(() => heading?.focus())
        },
      })
  }

  function again() {
    sent = null
  }

  const input =
    'mt-1 block w-full rounded-md border-line bg-surface text-sm text-ink focus:border-brand-500 focus:ring-brand-500'
  const hint = 'mt-1 text-sm text-ink-muted'
  const link = 'text-brand-600 underline hover:text-brand-700'
</script>

<svelte:head>
  <title>Tell us how you use the API · AgWeather</title>
  <meta
    name="description"
    content="Tell the AgWeather team how you use the public API and what you would like it to do."
  />
</svelte:head>

<section class="max-w-prose space-y-6">
  <header class="space-y-3">
    <h1 class="text-3xl font-semibold">Tell us how you use the API</h1>
    <p>
      The AgWeather API is free to use without an account, so we don’t know who relies on it. Telling us how you use it
      helps us decide what to add, and lets us warn you before a change that could affect your work.
    </p>
    <p class="text-sm text-ink-muted">
      The form takes a few minutes. Only your name and what you use the API for are required. The
      <a href="/api/v2/docs" class={link}>API documentation</a> lists every endpoint, and the
      <Link href={routes.changelog()} class={link}>changelog</Link> lists past changes.
    </p>
  </header>

  {#if sent}
    <div class="space-y-3 rounded-lg border-l-4 border-success bg-surface-raised p-4" role="status">
      <h2 bind:this={heading} tabindex="-1" class="text-xl font-semibold outline-none">Thank you</h2>
      <p>
        We’ve received your answers. Someone on the AgWeather team reads every response.
        {sent.email ? ' If you asked a question, we’ll reply by email.' : ''}
        {sent.notify ? ' We’ll email you before changes that affect the API.' : ''}
      </p>
      <p>
        To follow changes yourself, add the <a href={routes.changelogFeed()} class={link}>changelog’s Atom feed</a> to a
        feed reader. The <Link href={routes.status()} class={link}>data status</Link> page shows how current the data are.
      </p>
      <Button variant="secondary" onclick={again}>Send another response</Button>
    </div>
  {:else}
    {#if errors.form}
      <p role="alert" class="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm">{errors.form[0]}</p>
    {/if}

    <form onsubmit={submit} class="space-y-6" novalidate>
      {#snippet error(field: string)}
        {#if errors[field]}
          <p id={`${field}-error`} class="mt-1 text-sm text-danger-ink">{errors[field]?.join(' ')}</p>
        {/if}
      {/snippet}

      <fieldset class="space-y-4">
        <legend class="text-lg font-semibold">About you</legend>
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
            Organization <span class="font-normal text-ink-muted">(optional)</span>
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
            aria-describedby={described('organization', true)}
          />
          {#if errors.organization}
            {@render error('organization')}
          {:else}
            <p id="organization-hint" class={hint}>A farm, business, university, agency or other group.</p>
          {/if}
        </div>

        <div>
          <label for="email" class="text-sm font-medium">
            Email address <span class="font-normal text-ink-muted">(optional)</span>
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
            aria-describedby={described('email', true)}
          />
          {#if errors.email}
            {@render error('email')}
          {:else}
            <p id="email-hint" class={hint}>
              We use it only to reply to you or, if you ask below, to tell you before changes that affect the API. We
              don’t share it.
            </p>
          {/if}
        </div>
      </fieldset>

      <fieldset class="space-y-4">
        <legend class="text-lg font-semibold">How you use the API</legend>
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
            aria-describedby={described('uses', true)}></textarea>
          {#if errors.uses}
            {@render error('uses')}
          {:else}
            <p id="uses-hint" class={hint}>
              For example: “We pull daily degree days for 40 fields each morning to schedule scouting,” or “A class
              project mapping frost dates.”
            </p>
          {/if}
        </div>

        <fieldset aria-describedby={described('areas')}>
          <legend class="text-sm font-medium">
            Which parts of the API do you use? <span class="font-normal text-ink-muted">(optional)</span>
          </legend>
          <div class="mt-2 grid gap-1 sm:grid-cols-2">
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
            Which endpoints do you use, and what would you like added? <span class="font-normal text-ink-muted">
              (optional)
            </span>
          </label>
          <textarea
            id="endpoints"
            name="endpoints"
            rows="3"
            maxlength="2000"
            class={input}
            bind:value={form.endpoints}
            aria-invalid={errors.endpoints ? 'true' : undefined}
            aria-describedby={described('endpoints', true)}></textarea>
          {#if errors.endpoints}
            {@render error('endpoints')}
          {:else}
            <p id="endpoints-hint" class={hint}>
              Paths as the documentation gives them, such as /weather/daily, and any data or models you’d like to see.
            </p>
          {/if}
        </div>

        <div>
          <label for="frequency" class="text-sm font-medium">
            How often do you send requests? <span class="font-normal text-ink-muted">(optional)</span>
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
      </fieldset>

      <div>
        <label class="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            name="notify"
            class="mt-0.5 rounded-sm text-brand-600"
            bind:checked={form.notify}
            aria-describedby="notify-hint"
          />
          Email me before changes that affect the API.
        </label>
        <p id="notify-hint" class="{hint} ml-6">This needs your email address above.</p>
      </div>

      <!-- The honeypot: people never see or reach it, so anything typed here came from a program -->
      <div class="absolute left-[-10000px] size-px overflow-hidden" aria-hidden="true">
        <label for="website">Leave this field empty</label>
        <input id="website" name="website" type="text" tabindex="-1" autocomplete="off" bind:value={form.website} />
      </div>

      <Button type="submit" disabled={form.processing}>{form.processing ? 'Sending…' : 'Send'}</Button>
    </form>
  {/if}
</section>
