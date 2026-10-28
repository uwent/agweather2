<script lang="ts">
  import { onMount } from 'svelte'

  import { currentTheme, onThemeChange, setTheme, type Theme } from '@/lib/theme'

  let { class: className = '' }: { class?: string } = $props()

  let theme = $state<Theme>('light')
  onMount(() => {
    theme = currentTheme()
    return onThemeChange(() => (theme = currentTheme()))
  })

  const next = $derived<Theme>(theme === 'dark' ? 'light' : 'dark')
</script>

<button
  type="button"
  class="inline-flex size-7 items-center justify-center rounded-full hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white {className}"
  aria-label="Switch to {next} mode"
  title="Switch to {next} mode"
  onclick={() => setTheme(next)}
>
  {#if theme === 'dark'}
    <!-- Sun: switch to light -->
    <svg
      viewBox="0 0 24 24"
      class="size-4"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
      />
    </svg>
  {:else}
    <!-- Moon: switch to dark -->
    <svg
      viewBox="0 0 24 24"
      class="size-4"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path
        d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"
      />
    </svg>
  {/if}
</button>
