<!-- Ported from WISP 3 (adapted): app/frontend/lib/components/FlashMessages.svelte -->
<script lang="ts">
  import { page } from '@inertiajs/svelte'
  import { slide } from 'svelte/transition'

  // Django's messages (inertia-django sends them as flash.messages, {level, message}). Errors and
  // warnings are alerts; the rest are notices.
  //
  // How long a notice stays before it dismisses itself. Alerts stay until
  // dismissed: they report something that went wrong, so they shouldn't vanish.
  const NOTICE_MS = 6000

  // Dismissed messages stay hidden until the server sends a new flash. A new
  // flash reuses a message's box, changing its text; its generation restarts
  // the countdown, even for the same text
  let dismissed = $state<number[]>([])
  let pinned = $state<number[]>([])
  let generation = $state(0)
  let lastFlash: unknown = page.flash

  $effect(() => {
    if (page.flash !== lastFlash) {
      lastFlash = page.flash
      dismissed = []
      pinned = []
      generation += 1
    }
  })

  // The countdown is the bar's CSS animation, so pausing it (hover, focus, a
  // hidden tab) pauses the timer too, and its end dismisses the message
  let tabHidden = $state(typeof document !== 'undefined' && document.hidden)

  const messages = $derived(
    (page.flash?.messages ?? [])
      .map((message, index) => ({
        index,
        alert: message.level === 'error' || message.level === 'warning',
        text: message.message,
      }))
      .filter((message) => !dismissed.includes(message.index)),
  )

  const dismiss = (index: number) => (dismissed = [...dismissed, index])
  const pin = (index: number) => {
    if (!pinned.includes(index)) pinned = [...pinned, index]
  }
</script>

<svelte:document onvisibilitychange={() => (tabHidden = document.hidden)} />

{#each messages as message (message.index)}
  {@const timed = !message.alert && !pinned.includes(message.index)}
  <!-- It slides away only when dismissed (by its timer or button); a page whose
       flash has no message here just drops it -->
  <!-- Clicking the message keeps it (stops the timer); the keyboard equivalent
       is focusing its dismiss button, which pauses the timer while focused -->
  <div
    role={message.alert ? 'alert' : 'status'}
    out:slide={{ duration: dismissed.includes(message.index) ? 150 : 0 }}
    class="group relative flex items-start justify-between gap-4 overflow-hidden rounded-md border px-4 py-3 text-sm
      {message.alert ? 'border-danger/40 bg-danger/10' : 'border-success/40 bg-success/10'}"
    onclick={() => pin(message.index)}
  >
    <p>{message.text}</p>
    <button
      type="button"
      class="text-ink-muted hover:text-ink"
      aria-label="Dismiss message"
      onclick={(event) => {
        event.stopPropagation()
        dismiss(message.index)
      }}
    >
      ✕
    </button>
    {#key generation}
      {#if timed}
        <!-- The duration is !important to beat application.css's reduced-motion rule,
           which ends animations at once: this one is the timer, and a slow 2px bar
           isn't the motion that setting guards against -->
        <div
          aria-hidden="true"
          class="countdown absolute inset-x-0 bottom-0 h-0.5 origin-left bg-success group-focus-within:[animation-play-state:paused] group-hover:[animation-play-state:paused]"
          class:paused={tabHidden}
          style="animation-duration: {NOTICE_MS}ms !important"
          onanimationend={() => dismiss(message.index)}
        ></div>
      {/if}
    {/key}
  </div>
{/each}

<style>
  .countdown {
    animation-name: countdown;
    animation-timing-function: linear;
    animation-fill-mode: forwards;
  }

  .countdown.paused {
    animation-play-state: paused;
  }

  @keyframes countdown {
    from {
      transform: scaleX(1);
    }
    to {
      transform: scaleX(0);
    }
  }
</style>
